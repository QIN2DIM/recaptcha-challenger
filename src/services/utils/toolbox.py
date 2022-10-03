# -*- coding: utf-8 -*-
# Time       : 2022/1/16 0:27
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import sys

from loguru import logger


def init_log(**sink_path):
    """Initialize loguru log information"""
    event_logger_format = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | "
        "<lvl>{level}</lvl> - "
        # "<c><u>{name}</u></c> | "
        "{message}"
    )
    logger.remove()
    logger.add(
        sink=sys.stdout, colorize=True, level="DEBUG", format=event_logger_format, diagnose=False
    )
    if sink_path.get("error"):
        logger.add(
            sink=sink_path.get("error"),
            level="ERROR",
            rotation="1 week",
            encoding="utf8",
            diagnose=False,
        )
    if sink_path.get("runtime"):
        logger.add(
            sink=sink_path.get("runtime"),
            level="DEBUG",
            rotation="20 MB",
            retention="20 days",
            encoding="utf8",
            diagnose=False,
        )
    return logger
