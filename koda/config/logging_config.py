import logging


class CustomFormatter(logging.Formatter):
    def __init__(self, fmt="%(levelname)s: %(message)s"):
        super().__init__(fmt)

    def format(self, record):
        # Change format for ERROR level and above (ERROR, CRITICAL)
        if record.levelno >= logging.ERROR:
            self._style._fmt = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        else:
            self._style._fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        return super().format(record)


def configure_logger(name):
    # Create or get a logger
    logger = logging.getLogger(name)

    # Set the log level
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to catch all levels

    # Create handler (console handler in this case)
    handler = logging.StreamHandler()

    # Set the custom formatter
    handler.setFormatter(CustomFormatter())

    # Add handler to the logger
    if not logger.handlers:  # Avoid adding multiple handlers if already present
        logger.addHandler(handler)

    return logger
