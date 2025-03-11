
import structlog
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Настройка стандартного логирования
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    handlers=[
        RotatingFileHandler("bot_builder.log", maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

# Настройка structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
