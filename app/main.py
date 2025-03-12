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

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Конфигурация CSRF (оставлена для совместимости, но не используется для генерации токена)
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
        csrf_token = secrets.token_hex(16)  # Ручная генерация токена
        response.set_cookie(
            key="csrftoken",
            value=csrf_token,
            httponly=True,
            secure=False,  # Установите True в продакшене с HTTPS
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

    hashed_password = pwd_context.hash(data.password)  # Хеширование пароля
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
            if result and pwd_context.verify(password, result[0]):  # Проверка хешированного пароля
                logger.info(f"Login successful for user: {username}")
                return {"message": "Login successful", "role": result[1]}
            raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/create-bot")
async def create_bot(request: Request):
    data = await request.json()
    bot_name = data.get("name")
    bot_token = data.get("token")

    if not bot_name or not bot_token:
        raise HTTPException(status_code=400, detail="Bot name and token are required")

    csrf_token = request.headers.get("X-CSRF-Token")
    cookie_csrf = request.cookies.get("csrftoken")
    logger.info(f"Create Bot CSRF token received: {csrf_token}, Cookie CSRF: {cookie_csrf}")
    if not csrf_token or csrf_token != cookie_csrf:
        logger.warning("CSRF validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    logger.info(f"Bot created: {bot_name}")
    return {"message": f"Bot {bot_name} created successfully"}

@app.get("/")
async def serve_index():
    return FileResponse("app/static/index.html")
