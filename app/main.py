from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.bot import app as bot_app
from app.utils.logger import logger
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel
import os

app = FastAPI()

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение маршрутов API
app.mount("/api", bot_app)

csrf_protect = CsrfProtect()

class DocsRequest(BaseModel):
    name: str
    token: str
    commands: list
    examples: list

@app.get("/")
async def serve_index():
    return FileResponse("app/static/index.html")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("app/static/favicon.ico")

@app.post("/api/generate-docs")
async def generate_docs(data: DocsRequest, request: Request, csrf_protect: CsrfProtect = Depends()):
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
