import aiomysql
from app.utils.logger import logger

async def get_db_pool():
    try:
        pool = await aiomysql.create_pool(
            host="109.71.242.77",
            user="huppyk",
            password="Domofon32Dom321",
            db="gen_user",
            connect_timeout=10,
            minsize=1,
            maxsize=10
        )
        logger.info({"action": "db_pool_create", "status": "success", "host": "localhost"})
        return pool
    except Exception as e:
        logger.error({"action": "db_pool_create", "error": str(e), "status": "failed"})
        raise Exception("Не удалось создать пул подключений к базе данных")

async def close_db_pool(pool):
    try:
        pool.close()
        await pool.wait_closed()
        logger.info({"action": "db_pool_close", "status": "success"})
    except Exception as e:
        logger.error({"action": "db_pool_close", "error": str(e), "status": "failed"})

async def check_user(pool, username: str, password: str) -> bool:
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT * FROM users WHERE username = %s AND password = %s AND is_verified = %s"
                await cursor.execute(query, (username, password, True))
                user = await cursor.fetchone()
                logger.info({
                    "action": "check_user",
                    "status": "success",
                    "username": username,
                    "found": user is not None
                })
                return user is not None
    except Exception as e:
        logger.error({
            "action": "check_user",
            "error": str(e),
            "status": "failed",
            "username": username
        })
        return False
