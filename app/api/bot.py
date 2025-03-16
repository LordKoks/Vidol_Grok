from fastapi import FastAPI, HTTPException, Depends, Request, Query, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import json
from app.utils.logger import logger
from app.db.database import get_db_pool, close_db_pool
from fastapi.encoders import jsonable_encoder
from fastapi_csrf_protect import CsrfProtect
import os
from PIL import Image
import jwt
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse
import csv
import io
from app.bot.handlers import start_bot, configure_ai, shutdown_bots, running_bots, ai_configs, call_ai_api, update_stats

app = FastAPI()

# CSRF конфигурация
@CsrfProtect.load_config
def get_csrf_config():
    return [
        ('secret_key', 'my-super-secret-key-12345'),  # Уникальный ключ
        ('cookie_key', 'csrftoken'),
        ('cookie_samesite', 'lax'),
        ('header_name', 'X-CSRF-Token')
    ]

csrf_protect = CsrfProtect()

# JWT настройки
SECRET_KEY = "my-super-secret-key-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Глобальный пул базы данных
db_pool = None

# Модели данных
class AIConfig(BaseModel):
    provider: str
    api_key: str
    token: str
    custom_ai_name: str | None = None
    custom_ai_url: str | None = None

class BotCreate(BaseModel):
    name: str
    token: str
    platform: str = "telegram"

class Node(BaseModel):
    id: int
    text: str
    next: int | None = None

class BotNodes(BaseModel):
    token: str
    nodes: dict

class Generate3DRequest(BaseModel):
    description: str
    device_info: str = "unknown"

class UserRegister(BaseModel):
    username: str
    password: str
    email: str

class UserLogin(BaseModel):
    username: str
    password: str

class StatsResponse(BaseModel):
    platform: str
    messages_sent: int
    messages_received: int
    active_users: int
    last_updated: str

class BotStatus(BaseModel):
    name: str
    token: str
    platform: str
    is_running: bool

# Инициализация базы данных
async def get_db_pool_local():
    global db_pool
    if db_pool is None:
        logger.info("Инициализация подключения к базе данных...")
        db_pool = await get_db_pool()
    return db_pool

async def close_db_pool_local(pool):
    if pool:
        logger.info("Закрытие пула базы данных...")
        await close_db_pool(pool)

# Создание JWT токена
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Создан JWT токен для {data['sub']}")
    return encoded_jwt

# Проверка текущего пользователя
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            logger.warning("Токен не содержит user_id")
            raise HTTPException(status_code=401, detail="Неверный токен: отсутствует user_id")
        logger.debug(f"Аутентифицирован пользователь с ID {user_id}")
        return user_id
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка декодирования токена: {str(e)}")
        raise HTTPException(status_code=401, detail="Неверный токен")

# Проверка CSRF-токена
async def get_csrf_token(request: Request, csrf_protect: CsrfProtect = Depends()):
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        logger.warning("Отсутствует CSRF токен в заголовке")
        raise HTTPException(status_code=400, detail="CSRF token missing in header")
    try:
        await csrf_protect.validate_csrf(request, csrf_token)
        logger.debug(f"CSRF токен проверен: {csrf_token}")
        return csrf_token
    except Exception as e:
        logger.error(f"Ошибка валидации CSRF: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid CSRF token")

# Генерация 2D изображения
def generate_2d_image(description: str) -> str:
    try:
        img = Image.new("RGB", (200, 200), color="green")
        img_path = os.path.join("app/static", f"{description.replace(' ', '_')}_2d.png")
        img.save(img_path)
        logger.info(f"Generated 2D image: {img_path}")
        return img_path
    except Exception as e:
        logger.error(f"2D image generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate 2D image")

# Получение CSRF-токена
@app.get("/csrf-token")
async def get_csrf_token_endpoint(csrf_protect: CsrfProtect = Depends()):
    csrf_token = csrf_protect.generate_csrf_token()
    response = JSONResponse(content={"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(csrf_token, response)
    logger.info(f"Сгенерирован CSRF токен: {csrf_token}")
    return response

# Регистрация пользователя
@app.post("/register")
async def register_user(user: UserRegister, csrf_token: str = Depends(get_csrf_token)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (user.username, user.email))
                if await cursor.fetchone():
                    logger.warning(f"Попытка регистрации с существующим username или email: {user.username}, {user.email}")
                    raise HTTPException(status_code=400, detail="Пользователь или email уже существует")
                await cursor.execute(
                    "INSERT INTO users (username, password, email) VALUES (%s, %s, %s) RETURNING id",
                    (user.username, user.password, user.email)
                )
                user_id = (await cursor.fetchone())[0]
                await connection.commit()
        logger.info(f"Успешно зарегистрирован пользователь: {user.username}, ID: {user_id}")
        return {"message": "Пользователь успешно зарегистрирован 🌟", "user_id": user_id}
    except Exception as e:
        logger.error({"action": "register_user", "error": str(e), "status": "failed", "data": jsonable_encoder(user)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка регистрации пользователя")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Вход пользователя
@app.post("/login")
async def login_user(user: UserLogin, csrf_token: str = Depends(get_csrf_token)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT id FROM users WHERE username = %s AND password = %s", (user.username, user.password))
                result = await cursor.fetchone()
                if not result:
                    logger.warning(f"Неудачная попытка входа для {user.username}")
                    raise HTTPException(status_code=401, detail="Неверные учетные данные")
                user_id = result[0]
        token = create_access_token(data={"sub": user_id})
        logger.info(f"Пользователь {user.username} успешно вошел в систему")
        return {"message": "Успешный вход 🌈", "user_id": user_id, "token": token}
    except Exception as e:
        logger.error({"action": "login_user", "error": str(e), "status": "failed", "data": jsonable_encoder(user)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка входа")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Создание и запуск бота
@app.post("/create-bot")
async def create_bot(bot_data: BotCreate, csrf_token: str = Depends(get_csrf_token), user_id: int = Depends(get_current_user)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT id FROM bots WHERE token = %s", (bot_data.token,))
                if await cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Бот с таким токеном уже существует")
                query = "INSERT INTO bots (name, token, platform, user_id) VALUES (%s, %s, %s, %s) RETURNING id"
                await cursor.execute(query, (bot_data.name, bot_data.token, bot_data.platform, user_id))
                bot_id = (await cursor.fetchone())[0]
                await connection.commit()
                await start_bot(bot_data.token, bot_data.name, bot_data.platform)
                logger.info({"action": "create_bot", "name": bot_data.name, "token": bot_data.token, "platform": bot_data.platform, "status": "success"})
                return {
                    "message": "Bot created and started 🌟",
                    "bot_id": bot_id,
                    "name": bot_data.name,
                    "token": bot_data.token,
                    "platform": bot_data.platform
                }
    except Exception as e:
        logger.error({"action": "create_bot", "error": str(e), "status": "failed", "data": jsonable_encoder(bot_data)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка создания или запуска бота")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Сохранение узлов
@app.post("/save-nodes")
async def save_nodes(data: BotNodes, csrf_token: str = Depends(get_csrf_token), user_id: int = Depends(get_current_user)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("DELETE FROM nodes WHERE bot_token = %s", (data.token,))
                for node_id, node_data in data.nodes.items():
                    query = "INSERT INTO nodes (bot_token, node_id, text, next_node) VALUES (%s, %s, %s, %s)"
                    await cursor.execute(query, (data.token, node_id, node_data['text'], node_data.get('next')))
                await connection.commit()
                logger.info({"action": "save_nodes", "token": data.token, "node_count": len(data.nodes), "status": "success"})
                return {"message": "Nodes saved"}
    except Exception as e:
        logger.error({"action": "save_nodes", "error": str(e), "status": "failed", "data": jsonable_encoder(data)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка сохранения узлов")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Настройка AI
@app.post("/configure-ai")
async def configure_ai(config: AIConfig, csrf_token: str = Depends(get_csrf_token), user_id: int = Depends(get_current_user)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("DELETE FROM ai_configs WHERE bot_token = %s", (config.token,))
                query = "INSERT INTO ai_configs (bot_token, provider, api_key, custom_ai_name, custom_ai_url) VALUES (%s, %s, %s, %s, %s)"
                await cursor.execute(query, (config.token, config.provider, config.api_key, config.custom_ai_name, config.custom_ai_url))
                await connection.commit()
                logger.info({"action": "configure_ai", "provider": config.provider, "token": config.token, "status": "success"})
                if config.provider == "custom" and (not config.custom_ai_name or not config.custom_ai_url):
                    raise HTTPException(status_code=400, detail="Custom AI name and URL are required for custom provider")
                await configure_ai(config.token, config.dict())
                return {
                    "message": "AI configured 🤖",
                    "provider": config.provider,
                    "custom_ai_name": config.custom_ai_name,
                    "custom_ai_url": config.custom_ai_url
                }
    except Exception as e:
        logger.error({"action": "configure_ai", "error": str(e), "status": "failed", "data": jsonable_encoder(config)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка настройки ИИ")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Генерация 3D (оставлено из вашего кода)
@app.post("/generate-3d")
async def generate_3d(request: Generate3DRequest, csrf_token: str = Depends(get_csrf_token)):
    if not request.description:
        logger.warning("Отсутствует описание для генерации 3D")
        raise HTTPException(status_code=400, detail="Description is required")
    img_path = generate_2d_image(request.description)
    logger.info(f"Сгенерировано изображение для 3D: {img_path}")
    return {
        "model": {"type": "image", "data": f"/static/{os.path.basename(img_path)}"},
        "description": request.description,
        "quality": "low"
    }

# Проверка статуса бота
@app.get("/bot-status/{bot_id}", response_model=BotStatus)
async def get_bot_status(bot_id: int, user_id: int = Depends(get_current_user)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT name, token, platform FROM bots WHERE id = %s AND user_id = %s", (bot_id, user_id))
                bot = await cursor.fetchone()
                if not bot:
                    raise HTTPException(status_code=404, detail="Бот не найден")
                name, token, platform = bot
                is_running = token in running_bots
                return BotStatus(name=name, token=token, platform=platform, is_running=is_running)
    except Exception as e:
        logger.error({"action": "get_bot_status", "error": str(e), "status": "failed"}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка проверки статуса бота")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Экспорт APK (заглушка)
@app.get("/export-apk/{bot_id}")
async def export_apk(bot_id: int, user_id: int = Depends(get_current_user)):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT name, token FROM bots WHERE id = %s AND user_id = %s", (bot_id, user_id))
                bot = await cursor.fetchone()
                if not bot:
                    raise HTTPException(status_code=404, detail="Бот не найден")
                name, token = bot
        
        apk_path = f"app/static/{name}.apk"
        with open(apk_path, "w") as f:
            f.write(f"Placeholder APK for bot {name} with token {token}")
        logger.info(f"Экспортирован APK для бота {name}")
        return FileResponse(apk_path, filename=f"{name}.apk")
    except Exception as e:
        logger.error({"action": "export_apk", "error": str(e), "status": "failed"}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка экспорта APK")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Получение статистики
@app.get("/stats/{user_id}", response_model=list[StatsResponse])
async def get_stats(
    user_id: int = Depends(get_current_user),
    start_date: str = Query(None, description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(None, description="Конечная дата в формате YYYY-MM-DD"),
    platform: str = Query(None, description="Платформа: telegram, vk, discord, whatsapp")
):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                query = """
                    SELECT platform, messages_sent, messages_received, active_users, last_updated
                    FROM statistics
                    WHERE user_id = %s
                """
                params = [user_id]
                if start_date:
                    query += " AND last_updated >= %s"
                    params.append(datetime.strptime(start_date, "%Y-%m-%d"))
                if end_date:
                    query += " AND last_updated <= %s"
                    params.append(datetime.strptime(end_date, "%Y-%m-%d"))
                if platform:
                    query += " AND platform = %s"
                    params.append(platform)
                
                await cursor.execute(query, params)
                stats = await cursor.fetchall()
        if not stats:
            logger.warning(f"Статистика для пользователя {user_id} не найдена")
            raise HTTPException(status_code=404, detail="Статистика не найдена 😞")
        logger.info(f"Получена статистика для пользователя {user_id}")
        return [StatsResponse(platform=s[0], messages_sent=s[1], messages_received=s[2], 
                             active_users=s[3], last_updated=str(s[4])) for s in stats]
    except Exception as e:
        logger.error({"action": "get_stats", "error": str(e), "status": "failed"}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Экспорт статистики в CSV
@app.get("/stats/{user_id}/export")
async def export_stats(
    user_id: int = Depends(get_current_user),
    start_date: str = Query(None, description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(None, description="Конечная дата в формате YYYY-MM-DD"),
    platform: str = Query(None, description="Платформа: telegram, vk, discord, whatsapp")
):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                query = """
                    SELECT platform, messages_sent, messages_received, active_users, last_updated
                    FROM statistics
                    WHERE user_id = %s
                """
                params = [user_id]
                if start_date:
                    query += " AND last_updated >= %s"
                    params.append(datetime.strptime(start_date, "%Y-%m-%d"))
                if end_date:
                    query += " AND last_updated <= %s"
                    params.append(datetime.strptime(end_date, "%Y-%m-%d"))
                if platform:
                    query += " AND platform = %s"
                    params.append(platform)
                
                await cursor.execute(query, params)
                stats = await cursor.fetchall()
        
        if not stats:
            logger.warning(f"Статистика для экспорта пользователем {user_id} не найдена")
            raise HTTPException(status_code=404, detail="Статистика не найдена для экспорта 😞")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Platform", "Messages Sent", "Messages Received", "Active Users", "Last Updated"])
        for stat in stats:
            writer.writerow([stat[0], stat[1], stat[2], stat[3], str(stat[4])])
        
        logger.info(f"Статистика для пользователя {user_id} экспортирована в CSV")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=stats_{user_id}.csv"}
        )
    except Exception as e:
        logger.error({"action": "export_stats", "error": str(e), "status": "failed"}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка экспорта статистики")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Webhook для WhatsApp
@app.post("/whatsapp/webhook/{bot_token}")
async def whatsapp_webhook(bot_token: str, request: Request):
    form_data = await request.form()
    from_number = form_data.get("From")
    body = form_data.get("Body")
    media_url = form_data.get("MediaUrl0")
    
    if bot_token not in running_bots:
        logger.warning(f"Бот с токеном {bot_token} не найден для WhatsApp webhook")
        return {"message": "Бот не найден 😞"}

    bot = running_bots[bot_token]["bot"]
    name = running_bots[bot_token]["name"]
    user_id = from_number.replace("whatsapp:", "")

    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT * FROM nodes WHERE bot_token = %s AND node_id = %s", (bot_token, body.strip().lower()))
                node = await cursor.fetchone()
                if not node and body.lower() == "/start":
                    node = ("start", "text", f"🌟 Привет! Я {name}. Выбери действие:", None, "Меню,Помощь")
    
        response = MessagingResponse()
        if node:
            formatted_text = f"🌈 {node[0]}\n\n{node[2]}"
            if node[1] == "text":
                response.message(formatted_text)
            elif node[1] in ["photo", "video"]:
                response.message(media_url=node[2])
            
            if node[3]:
                async with pool.acquire() as connection:
                    async with connection.cursor() as cursor:
                        await cursor.execute("SELECT * FROM nodes WHERE bot_token = %s AND node_id = %s", (bot_token, node[3]))
                        next_node = await cursor.fetchone()
                if next_node:
                    formatted_text = f"🌈 {next_node[0]}\n\n{next_node[2]}"
                    if next_node[1] == "text":
                        response.message(formatted_text)
                    elif next_node[1] in ["photo", "video"]:
                        response.message(media_url=next_node[2])
        else:
            if bot_token in ai_configs:
                ai_response = await call_ai_api(bot_token, body)
                response.message(f"🤖 AI: {ai_response}")
            else:
                response.message("❌ Узел не найден.")

        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT id FROM users WHERE bot_token = %s", (bot_token,))
                user_id_db = await cursor.fetchone()
                if user_id_db:
                    user_id_db = user_id_db[0]
                else:
                    user_id_db = 1  # Заглушка, если user_id не найден
        await update_stats(user_id_db, bot_token, "whatsapp", 1, 1, 1)
        logger.info(f"WhatsApp сообщение обработано для бота {bot_token}")
        return response.to_xml()
    except Exception as e:
        logger.error({"action": "whatsapp_webhook", "error": str(e), "status": "failed"}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка обработки WhatsApp webhook")
    finally:
        if pool:
            await close_db_pool_local(pool)

# Завершение работы приложения
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Остановка всех ботов и закрытие базы данных...")
    await shutdown_bots()
    await close_db_pool_local(db_pool)

# Получение узлов бота
async def get_bot_nodes(token: str):
    pool = None
    try:
        pool = await get_db_pool_local()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT node_id, text, next_node FROM nodes WHERE bot_token = %s", (token,))
                nodes = await cursor.fetchall()
        logger.debug(f"Получены узлы для бота с токеном {token}")
        return [{"id": n[0], "text": n[1], "next": n[2]} for n in nodes]
    except Exception as e:
        logger.error(f"Ошибка получения узлов для бота {token}: {str(e)}")
        return []
    finally:
        if pool:
            await close_db_pool_local(pool)
