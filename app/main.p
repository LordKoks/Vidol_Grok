import random
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect
from app.db.database import get_db_pool, close_db_pool, check_user
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Конфигурация CSRF в виде списка кортежей для версии 1.0.2
csrf_settings = [
    ("secret_key", os.getenv("CSRF_SECRET_KEY", "your-secret-key-here")),
    ("cookie_samesite", "lax"),
    ("cookie_secure", False),  # Булево значение
    ("max_age", 3600)  # Целое число
]

csrf_protect = CsrfProtect()

@csrf_protect.load_config
def get_csrf_config():
    return csrf_settings

@app.on_event("startup")
async def startup_event():
    app.state.db_pool = await get_db_pool()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_pool(app.state.db_pool)

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
        print(f"Verification email sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise

@app.get("/api/csrf-token")
async def get_csrf_token(response: Response):
    try:
        csrf_token = csrf_protect.get_csrf_token()
        response.set_cookie(
            key="csrftoken",
            value=csrf_token,
            httponly=True,
            secure=False,  # Установите True в продакшене
            samesite="lax",
            max_age=3600
        )
        print(f"CSRF token generated: {csrf_token}")
        return {"csrf_token": csrf_token}
    except Exception as e:
        print(f"CSRF Token Error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {str(e)}"})

@app.post("/api/register")
async def register(request: Request, data: RegisterData):
    try:
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise HTTPException(status_code=403, detail="CSRF token missing")
        await csrf_protect.validate_csrf(csrf_token)

        pool = app.state.db_pool
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT * FROM users WHERE username = %s", (data.username,))
                if await cursor.fetchone():
                    return JSONResponse(status_code=400, content={"detail": "Логин уже занят"})
                
                await cursor.execute("SELECT * FROM users WHERE email = %s", (data.email,))
                if await cursor.fetchone():
                    return JSONResponse(status_code=400, content={"detail": "Email уже используется"})

                verification_code = str(random.randint(100000, 999999))
                await cursor.execute(
                    "INSERT INTO users (username, password, email, verification_code, is_verified, role) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (data.username, data.password, data.email, verification_code, False, 'user')
                )
                await connection.commit()
                print(f"User registered: {data.username}, email: {data.email}")

        send_verification_email(data.email, verification_code)
        return {"message": "Registration successful, check your email"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Registration Error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {str(e)}"})

@app.post("/api/verify-email")
async def verify_email(request: Request, data: VerifyData):
    try:
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise HTTPException(status_code=403, detail="CSRF token missing")
        await csrf_protect.validate_csrf(csrf_token)

        pool = app.state.db_pool
        async with pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT verification_code FROM users WHERE username = %s AND is_verified = %s",
                    (data.username, False)
                )
                result = await cursor.fetchone()
                if not result or result[0] != data.code:
                    return JSONResponse(status_code=400, content={"detail": "Неверный код подтверждения"})

                await cursor.execute(
                    "UPDATE users SET is_verified = %s, verification_code = NULL WHERE username = %s",
                    (True, data.username)
                )
                await connection.commit()
                print(f"Email verified for user: {data.username}")
                return {"message
