
import aiomysql
import logging
import os
from dotenv import load_dotenv

load_dotenv()

async def get_db_pool():
    try:
        pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "telegram_bot_db"),
            minsize=1,
            maxsize=10
        )
        logging.info({"event": {"action": "db_pool_create", "status": "success", "host": os.getenv("DB_HOST", "localhost")}})
        return pool
    except Exception as e:
        logging.error(f"Error creating database pool: {str(e)}")
        raise

async def close_db_pool(pool):
    try:
        pool.close()
        await pool.wait_closed()
        logging.info("Database pool closed")
    except Exception as e:
        logging.error(f"Error closing database pool: {str(e)}")
        raise

async def check_user(username, password):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            result = await cur.fetchone()
            return result
