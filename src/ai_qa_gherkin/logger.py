import sys
from loguru import logger
from ai_qa_gherkin.config import settings

def setup_logger():
    logger.remove()  # Remove the default logger

    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level} | "
            "{extra[service]} | "
            "{extra[operation]} | "
            "{message}"
        ),
    )

def get_logger(operation: str = "general"):
    return logger.bind(service=settings.app_name, operation=operation)