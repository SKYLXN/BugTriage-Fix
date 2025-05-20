import logging

def get_logger(name="bugtriage"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logging.basicConfig(level=logging.INFO)
    return logger
