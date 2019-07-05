"""
CLI Utilities
"""

# logging
import logging as log
from logging.handlers import RotatingFileHandler
logger = log.getLogger('postprocess')


def set_logger(log_level, log_file):
    # log level
    if log_level == 0:
        level = log.WARN
    elif log_level == 2:
        level = log.DEBUG
    else:
        level = log.INFO

    # log file
    if log_file:
        handler = RotatingFileHandler(
            log_file, maxBytes=5000000, backupCount=9)
        formatter = log.Formatter(
            '%(asctime)s - %(name)s %(levelname)s: %(message)s')
    else:
        handler = log.StreamHandler()
        formatter = log.Formatter('%(name)s %(levelname)s: %(message)s')

    # apply settings
    handler.setLevel(level)
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
