
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "3386"))
    DB_HOST = os.getenv("DB_HOST")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
