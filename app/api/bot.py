from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
import json
from app.utils.logger import logger
from app.db.database import get_db_pool, close_db_pool
from fastapi.encoders import jsonable_encoder
from fastapi_csrf_protect import CsrfProtect
import os
from PIL import Image

app = FastAPI()

# Инициализация CSRF
csrf_protect = CsrfProtect()

class AIConfig(BaseModel):
    provider: str
    api_key: str
    token: str
    custom_ai_name: str | None = None
    custom_ai_url: str | None = None

class BotCreate(BaseModel):
    name: str
    token: str

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

# Добавляем маршрут для получения CSRF-токена
@app.get("/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends(CsrfProtect)):
    token = csrf_protect.generate_csrf()
    return {"csrf_token": token}

# Проверка CSRF-токена через зависимость
async def get_csrf_token(request: Request, csrf_protect: CsrfProtect = Depends(CsrfProtect)):
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise HTTPException(status_code=400, detail="CSRF token missing")
    # Проверяем токен с помощью CsrfProtect
    await csrf_protect.validate_csrf(request, csrf_token)
    return csrf_token

def generate_2d_image(description: str) -> str:
    """Генерирует простую 2D-картинку."""
    try:
        img = Image.new("RGB", (200, 200), color="green")
        img_path = os.path.join("app/static", f"{description.replace(' ', '_')}_2d.png")
        img.save(img_path)
        logger.info(f"Generated 2D image: {img_path}")
        return img_path
    except Exception as e:
        logger.error(f"2D image generation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate 2D image")

@app.post("/create-bot")
async def create_bot(bot_data: BotCreate, csrf_token: str = Depends(get_csrf_token)):
    pool = None
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                query = "INSERT INTO bots (name, token) VALUES (%s, %s)"
                await cursor.execute(query, (bot_data.name, bot_data.token))
                await connection.commit()
                logger.info({"action": "create_bot", "name": bot_data.name, "token": bot_data.token, "status": "success"})
                return {"message": "Bot created", "name": bot_data.name, "token": bot_data.token}
    except Exception as e:
        logger.error({"action": "create_bot", "error": str(e), "status": "failed", "data": jsonable_encoder(bot_data)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка создания бота")
    finally:
        if pool:
            await close_db_pool(pool)

@app.post("/save-nodes")
async def save_nodes(data: BotNodes, csrf_token: str = Depends(get_csrf_token)):
    pool = None
    try:
        pool = await get_db_pool()
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
            await close_db_pool(pool)

@app.post("/configure-ai")
async def configure_ai(config: AIConfig, csrf_token: str = Depends(get_csrf_token)):
    pool = None
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("DELETE FROM ai_configs WHERE bot_token = %s", (config.token,))
                query = "INSERT INTO ai_configs (bot_token, provider, api_key, custom_ai_name, custom_ai_url) VALUES (%s, %s, %s, %s, %s)"
                await cursor.execute(query, (config.token, config.provider, config.api_key, config.custom_ai_name, config.custom_ai_url))
                await connection.commit()
                logger.info({"action": "configure_ai", "provider": config.provider, "token": config.token, "status": "success"})
                if config.provider == "custom" and (not config.custom_ai_name or not config.custom_ai_url):
                    raise HTTPException(status_code=400, detail="Custom AI name and URL are required for custom provider")
                logger.info({"action": "configure_ai_custom", "name": config.custom_ai_name, "url": config.custom_ai_url})
                return {
                    "message": "AI configured",
                    "provider": config.provider,
                    "custom_ai_name": config.custom_ai_name,
                    "custom_ai_url": config.custom_ai_url
                }
    except Exception as e:
        logger.error({"action": "configure_ai", "error": str(e), "status": "failed", "data": jsonable_encoder(config)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка настройки ИИ")
    finally:
        if pool:
            await close_db_pool(pool)

@app.post("/generate-3d")
async def generate_3d(request: Generate3DRequest):
    if not request.description:
        raise HTTPException(status_code=400, detail="Description is required")
    img_path = generate_2d_image(request.description)
    return {
        "model": {"type": "image", "data": f"/static/{os.path.basename(img_path)}"},
        "description": request.description,
        "quality": "low"
    }
