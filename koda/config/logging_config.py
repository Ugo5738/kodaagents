import logging


def configure_logger(name):
    # Create or get a logger
    logger = logging.getLogger(name)

    # Set the log level
    logger.setLevel(logging.INFO)

    # Create handler (console handler in this case)
    handler = logging.StreamHandler()

    # Create formatter and set it for the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to the logger
    if not logger.handlers:  # Avoid adding multiple handlers if already present
        logger.addHandler(handler)

    return logger
