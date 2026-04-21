"""
Logger Setup
"""
import sys
from loguru import logger
from pathlib import Path


def setup_logger(
    log_level: str = "INFO",
    log_file: str = None,
    rotation: str = "00:00",
    retention: str = "7 days",
) -> None:
    """
    Setup logger dengan loguru.
    
    Args:
        log_level: DEBUG, INFO, WARNING, ERROR
        log_file: Path ke log file (optional)
        rotation: Rotation time
        retention: Retention period
    """
    # Remove default handler
    logger.remove()
    
    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # File output
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            level="DEBUG",
            compression="zip",
        )
    
    # Configure
    logger.level("DEBUG", color="<blue>")
    logger.level("INFO", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
