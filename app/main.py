import random
import smtplib
import logging
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect
from app.db.database import get_db_pool, close_db_pool
from pydantic import BaseModel
from dotenv import load_dotenv
from passlib.context import CryptContext
import os
import secrets
import aiohttp
import zipfile
import shutil

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

csrf_settings = [
    ("secret_key", os.getenv("CSRF_SECRET_KEY", "your-secret-key-here")),
    ("cookie_samesite", "lax"),
    ("cookie_secure", False),
    ("max_age", 3600)
]

csrf_protect = CsrfProtect()

@csrf_protect.load_config
def get_csrf_config():
    return csrf_settings

@app.on_event("startup")
async def startup_event():
    app.state.db_pool = await get_db_pool()
    logger.info("Database pool created")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_pool(app.state.db_pool)
    logger.info("Database pool closed")

class RegisterData(BaseModel):
    username: str
    password: str
    email: str

class VerifyData(BaseModel):
    username: str
    code: str

class BotData(BaseModel):
    name: str
    token: str
    type: str  # "telegram", "discord", "multiplatform"

class ExportAPKData(BaseModel):
    name: str
    token: str
    ui_config: dict  # Настройки интерфейса APK

class BotStructureData(BaseModel):
    name: str
    token: str
    structure: dict  # Обновленная структура

class GenerateDocsData(BaseModel):
    name: str
    token: str
    commands: list
    examples: list

def send_verification_email(email: str, code: str):
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    if not sender or not password:
        raise ValueError("SMTP_EMAIL or SMTP_PASSWORD not set in .env")
    msg = MIMEText(f"Ваш код подтверждения: {code}")
    msg['Subject'] = 'Подтверждение регистрации'
    msg['From'] = sender
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.mail.ru', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        logger.info(f"Verification email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise

@app.get("/api/csrf-token")
async def get_csrf_token(response: Response):
    try:
        logger.info("Received request to /api/csrf-token")
        csrf_token = secrets.token_hex(16)
        response.set_cookie(
            key="csrftoken",
            value=csrf_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=3600
        )
        logger.info(f"CSRF token generated: {csrf_token}")
        return {"csrf_token": csrf_token}
    except Exception as e:
        logger.error(f"CSRF Token Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/api/register")
async def register(request: Request, data: RegisterData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Register CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    hashed_password = pwd_context.hash(data.password)
    async with app.state.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users WHERE username = %s", (data.username,))
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Логин уже занят")
            
            await cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
            if await cursor.fetchone():
                raise HTTPException(status_code=400, detail="Email уже используется")

            verification_code = str(random.randint(100000, 999999))
            await cursor.execute(
                "INSERT INTO users (username, password, email, verification_code, is_verified, role) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (data.username, hashed_password, data.email, verification_code, False, 'user')
            )
            await connection.commit()
            logger.info(f"User registered: {data.username}, email: {data.email}")

    send_verification_email(data.email, verification_code)
    return {"message": "Registration successful, check your email"}

@app.post("/api/verify-email")
async def verify_email(request: Request, data: VerifyData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Verify CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    async with app.state.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT verification_code FROM users WHERE username = %s AND is_verified = %s",
                (data.username, False)
            )
            result = await cursor.fetchone()
            if not result or result[0] != data.code:
                raise HTTPException(status_code=400, detail="Неверный код подтверждения")

            await cursor.execute(
                "UPDATE users SET is_verified = %s, verification_code = NULL WHERE username = %s",
                (True, data.username)
            )
            await connection.commit()
            logger.info(f"Email verified for user: {data.username}")
            return {"message": "Email verified"}

@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Login CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    async with app.state.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT password, role FROM users WHERE username = %s AND is_verified = %s",
                (username, True)
            )
            result = await cursor.fetchone()
            if result and pwd_context.verify(password, result[0]):
                logger.info(f"Login successful for user: {username}")
                return {"message": "Login successful", "role": result[1]}
            raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/create-bot")
async def create_bot(request: Request, data: BotData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Create Bot CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if data.type == "telegram":
        code = f"""import asyncio
from aiogram import Bot, Dispatcher, types

bot = Bot(token='{data.token}')
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply('Привет от Telegram бота!')

async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
"""
    elif data.type == "discord":
        code = f"""import discord

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    print(f'Discord bot {{client.user}} is ready')

@client.event
async def on_message(message):
    if message.author != client.user:
        await message.channel.send('Привет от Discord бота!')

client.run('{data.token}')
"""
    elif data.type == "multiplatform":
        code = f"""import asyncio
from aiogram import Bot as TelegramBot, Dispatcher as TelegramDispatcher, types
import discord

telegram_bot = TelegramBot(token='{data.token.split('|')[0]}')
telegram_dp = TelegramDispatcher(telegram_bot)
discord_client = discord.Client(intents=discord.Intents.default())

@telegram_dp.message_handler(commands=['start'])
async def telegram_start(message: types.Message):
    await message.reply('Привет из Telegram!')

@discord_client.event
async def on_ready():
    print(f'Discord bot {{discord_client.user}} is ready')

@discord_client.event
async def on_message(message):
    if message.author != discord_client.user:
        await message.channel.send('Привет из Discord!')

async def main():
    await asyncio.gather(telegram_dp.start_polling(), discord_client.start('{data.token.split('|')[1]}'))

if __name__ == '__main__':
    asyncio.run(main())
"""
    else:
        raise HTTPException(status_code=400, detail="Invalid bot type")

    with open(f"{data.name}_bot.py", "w") as f:
        f.write(code)
    logger.info(f"Bot created: {data.name}, type: {data.type}")
    return FileResponse(f"{data.name}_bot.py", filename=f"{data.name}_bot.py")

@app.post("/api/check-bot-status")
async def check_bot_status(request: Request, data: BotData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Check Bot Status CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if data.type == "telegram":
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{data.token}/getMe"
            async with session.get(url) as response:
                result = await response.json()
                if response.status == 200 and result.get("ok"):
                    logger.info(f"Bot {data.name} is online")
                    stats = await session.get(f"https://api.telegram.org/bot{data.token}/getUpdates")
                    stats_data = await stats.json()
                    return {"status": "online", "bot_info": result["result"], "stats": stats_data.get("result", [])}
                logger.info(f"Bot {data.name} is offline")
                return {"status": "offline", "error": result.get("description", "Unknown error")}
    elif data.type == "discord":
        return {"status": "unknown", "message": "Discord status check not implemented yet"}
    else:
        return {"status": "unknown", "message": "Multiplatform status check requires separate tokens"}

@app.post("/api/export-apk")
async def export_apk(request: Request, data: ExportAPKData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Export APK CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    ui_config = data.ui_config or {"title": "Bot Control", "color": "#007bff"}
    bot_code = f"""import requests
import tkinter as tk

TOKEN = '{data.token}'
API_URL = 'https://api.telegram.org/bot' + TOKEN

def send_message():
    chat_id = chat_id_entry.get()
    text = message_entry.get()
    requests.post(f'{{API_URL}}/sendMessage', json={{'chat_id': chat_id, 'text': text}})
    message_entry.delete(0, tk.END)

root = tk.Tk()
root.title("{ui_config['title']}")
root.configure(bg="{ui_config['color']}")

tk.Label(root, text="Chat ID:").pack()
chat_id_entry = tk.Entry(root)
chat_id_entry.pack()

tk.Label(root, text="Message:").pack()
message_entry = tk.Entry(root)
message_entry.pack()

tk.Button(root, text="Send", command=send_message).pack()

root.mainloop()
"""
    apk_dir = f"apk_{data.name}"
    os.makedirs(apk_dir, exist_ok=True)
    with open(f"{apk_dir}/bot.py", "w") as f:
        f.write(bot_code)
    with open(f"{apk_dir}/AndroidManifest.xml", "w") as f:
        f.write("<manifest><!-- Заглушка для APK --></manifest>")
    apk_file = f"{data.name}_bot.apk"
    with zipfile.ZipFile(apk_file, 'w') as zf:
        zf.write(f"{apk_dir}/bot.py", "bot.py")
        zf.write(f"{apk_dir}/AndroidManifest.xml", "AndroidGITManifest.xml")
    shutil.rmtree(apk_dir)

    logger.info(f"APK exported for bot: {data.name}")
    return FileResponse(apk_file, filename=apk_file)

@app.post("/api/bot-structure")
async def bot_structure(request: Request, data: BotStructureData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Bot Structure CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    structure = data.structure or {
        "nodes": [
            {"id": "start", "command": "/start", "x": 0, "y": 0, "z": 0},
            {"id": "help", "command": "/help", "x": 5, "y": 0, "z": 0}
        ],
        "edges": [
            {"from": "start", "to": "help"}
        ]
    }
    logger.info(f"Bot structure updated for: {data.name}")
    return {"structure": structure}

@app.post("/api/generate-docs")
async def generate_docs(request: Request, data: GenerateDocsData):
    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Generate Docs CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    docs = f"# {data.name} Bot\n\n"
    docs += "## Описание\nЭто Telegram-бот, созданный с помощью Telegram Bot Builder.\n\n"
    docs += "## Команды\n"
    for i, cmd in enumerate(data.commands):
        example = data.examples[i] if i < len(data.examples) else "Нет примера"
        docs += f"- `{cmd}`: Описание команды.\n  *Пример:* `{example}`\n"
    docs += "\n## Установка\n1. Установите зависимости: `pip install aiogram`\n2. Запустите бота: `python bot.py`\n"

    doc_file = f"{data.name}_README.md"
    with open(doc_file, "w") as f:
        f.write(docs)
    logger.info(f"Docs generated for bot: {data.name}")
    return FileResponse(doc_file, filename=doc_file)

@app.get("/")
async def serve_index():
    return FileResponse("app/static/index.html")
