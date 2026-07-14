from ai_qa_gherkin.logger import setup_logger, get_logger
from ai_qa_gherkin.config import settings

setup_logger()
log = get_logger("smoke")

log.info(f"Environment loaded: {settings.app_env}")
log.info("Config + logger OK")