
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.utils.logger import logger
import asyncio
import aiogram.exceptions
import requests
import os

running_bots = {}
polling_tasks = {}
ai_configs = {}  # Хранилище настроек AI для ботов

async def send_animated_text(message: types.Message, text: str, delay: float = 0.5):
    """Отправка текста с анимацией."""
    for i in range(0, len(text), 2):
        await message.answer(text[:i+2], parse_mode="HTML")
        await asyncio.sleep(delay)
    await message.answer(text, parse_mode="HTML")

async def call_ai_api(token: str, message_text: str) -> str:
    """Вызов внешнего API AI (например, OpenAI)."""
    config = ai_configs.get(token)
    if not config:
        return "AI не настроен. Настройте ключ API в интерфейсе."
    
    ai_provider = config.get('aiProvider')
    ai_api_key = config.get('aiApiKey')
    if not ai_api_key or not ai_provider:
        return "Ошибка: Отсутствует ключ API или провайдер."

    if ai_provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {ai_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": message_text}]
        }
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Ошибка вызова OpenAI API: {str(e)}")
            return "Ошибка при обработке запроса AI."
    elif ai_provider == "anthropic":
        # Пример для Anthropic (нужно адаптировать под их API)
        url = "https://api.anthropic.com/v1/complete"
        headers = {
            "x-api-key": ai_api_key,
            "Content-Type": "application/json"
        }
        data = {
            "prompt": message_text,
            "model": "claude-2",
            "max_tokens": 100
        }
        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()["completion"]
        except Exception as e:
            logger.error(f"Ошибка вызова Anthropic API: {str(e)}")
            return "Ошибка при обработке запроса AI."
    return "Провайдер AI не поддерживается."

async def start_bot(token: str, name: str):
    if token in running_bots:
        logger.warning(f"Бот с токеном {token} уже запущен, перезапуск")
        if token in polling_tasks:
            polling_tasks[token].cancel()
            try:
                await asyncio.wait_for(polling_tasks[token], timeout=2.0)
            except asyncio.CancelledError:
                logger.info(f"Polling для бота {token} остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки polling: {str(e)}")
            del polling_tasks[token]

    bot = Bot(token=token)
    dp = Dispatcher()
    running_bots[token] = {"bot": bot, "dp": dp, "name": name}

    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        from app.api.bot import get_bot_nodes
        nodes = await get_bot_nodes(token)
        start_node = next((n for n in nodes if n["id"].lower() == "start"), None)
        if not start_node:
            start_node = {"id": "start", "text": "🌟 <b>Привет!</b> 🌟\nЯ твой бот.\nВыбери действие:", "options": ["Меню", "Помощь"]}
        formatted_text = f"🌈 <b>{start_node['id']}</b> 🌈\n\n{start_node['text']}"
        keyboard = None
        if start_node.get("options"):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📌 {opt}", callback_data=opt.lower()) for opt in start_node["options"]]
            ])
        try:
            await send_animated_text(message, formatted_text, delay=0.2)
            if keyboard:
                await message.answer("Выберите опцию:", reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"Бот {name} обработал /start для {message.from_user.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {str(e)}")

    @dp.callback_query()
    async def process_callback(callback_query: types.Message):
        from app.api.bot import get_bot_nodes
        nodes = await get_bot_nodes(token)
        callback_data = callback_query.data
        node = next((n for n in nodes if n.get("options") and callback_data in [opt.lower() for opt in n["options"]]), None)
        if node:
            next_id = node.get("next")
            next_node = next((n for n in nodes if n["id"] == next_id), None) if next_id else None
            target_node = next_node if next_node else node
            formatted_text = f"🌈 <b>{target_node['id']}</b> 🌈\n\n{target_node['text']}"
            keyboard = None
            if target_node.get("options"):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📌 {opt}", callback_data=opt.lower()) for opt in target_node["options"]]
                ])
            try:
                await send_animated_text(callback_query.message, formatted_text, delay=0.2)
                if keyboard:
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                await callback_query.answer()
            except Exception as e:
                logger.error(f"Ошибка обработки callback: {str(e)}")
        else:
            await callback_query.message.answer("❌ Действие не найдено.", parse_mode="HTML")
            await callback_query.answer()

    @dp.message()
    async def handle_message(message: types.Message):
        from app.api.bot import get_bot_nodes
        nodes = await get_bot_nodes(token)
        node_id = message.text.strip()
        node = next((n for n in nodes if n["id"].lower() == node_id.lower()), None)
        if node:
            formatted_text = f"🌈 <b>{node['id']}</b> 🌈\n\n{node['text']}"
            keyboard = None
            if node.get("options"):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"📌 {opt}", callback_data=opt.lower()) for opt in node["options"]]
                ])
            try:
                await send_animated_text(message, formatted_text, delay=0.2)
                if keyboard:
                    await message.answer("Выберите опцию:", reply_markup=keyboard, parse_mode="HTML")
                if node["next"]:
                    next_node = next((n for n in nodes if n["id"] == node["next"]), None)
                    if next_node:
                        formatted_text = f"🌈 <b>{next_node['id']}</b> 🌈\n\n{next_node['text']}"
                        keyboard = None
                        if next_node.get("options"):
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text=f"📌 {opt}", callback_data=opt.lower()) for opt in next_node["options"]]
                            ])
                        await send_animated_text(message, formatted_text, delay=0.2)
                        if keyboard:
                            await message.answer("Выберите опцию:", reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения: {str(e)}")
        else:
            # Проверка на включённый AI
            if token in ai_configs:
                ai_response = await call_ai_api(token, message.text)
                await send_animated_text(message, f"🤖 AI: {ai_response}", delay=0.2)
            else:
                await message.answer("❌ Узел не найден. Попробуйте другой ID или используйте кнопки.", parse_mode="HTML")

    try:
        logger.info(f"Запуск бота {name} в режиме polling")
        task = asyncio.create_task(dp.start_polling(bot))
        polling_tasks[token] = task
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Ошибка запуска бота {name}: {str(e)}")
        if token in running_bots and token not in polling_tasks:
            del running_bots[token]
        if token in polling_tasks:
            del polling_tasks[token]
        raise

async def add_node(token: str, node: dict):
    if token in running_bots:
        logger.info(f"Обновление узлов для бота с токеном {token}")
    else:
        logger.warning(f"Бот с токеном {token} не найден для обновления узлов")

async def configure_ai(token: str, ai_config: dict):
    ai_configs[token] = ai_config
    logger.info(f"Настройка AI для бота с токеном {token}: {ai_config}")

async def shutdown_bots():
    for token in list(running_bots.keys()):
        if token in polling_tasks:
            polling_tasks[token].cancel()
            try:
                await asyncio.wait_for(polling_tasks[token], timeout=2.0)
            except asyncio.CancelledError:
                logger.info(f"Polling для бота {token} остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки polling: {str(e)}")
            del polling_tasks[token]
        if token in running_bots:
            bot = running_bots[token]["bot"]
            for attempt in range(3):
                try:
                    await bot.close()
                    logger.info(f"Бот с токеном {token} успешно закрыт")
                    break
                except aiogram.exceptions.TelegramRetryError as e:
                    logger.warning(f"Превышен лимит Telegram, повтор через {e.retry_after} секунд")
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    logger.error(f"Ошибка закрытия бота: {str(e)}")
                    break
            del running_bots[token]
