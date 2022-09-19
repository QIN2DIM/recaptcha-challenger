# -*- coding: utf-8 -*-
# Time       : 2022/1/16 0:27
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import logging
import os
import sys
from typing import Optional

import undetected_chromedriver as uc
from loguru import logger
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import get_browser_version_from_os, ChromeType


class ToolBox:
    """Portable Toolbox"""

    @staticmethod
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
            sink=sys.stdout,
            colorize=True,
            level="DEBUG",
            format=event_logger_format,
            diagnose=False,
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


def _set_options(language: Optional[str] = None) -> ChromeOptions:
    """统一挑战上下文参数"""

    # - Restrict browser startup parameters
    options = ChromeOptions()
    options.add_argument("--log-level=3")
    options.add_argument("--disable-dev-shm-usage")

    # - Restrict the language of hCaptcha label
    # - Environment variables are valid only in the current process
    # and do not affect other processes in the operating system
    os.environ["LANGUAGE"] = "en" if language is None else language
    options.add_argument(f"--lang={os.getenv('LANGUAGE')}")

    logger.debug("🎮 Activate challenger context")
    return options


def get_ctx(silence: Optional[bool] = None, language: Optional[str] = None) -> Chrome:
    """标准的 Selenium 上下文"""
    # Control headless browser
    silence = True if silence is None or "linux" in sys.platform else silence
    options = _set_options(language=language)
    if silence:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    return Chrome(options=options, service=service)


def get_challenge_ctx(silence: Optional[bool] = None, language: Optional[str] = None) -> uc.Chrome:
    """
    Challenger drive for handling human-machine challenges

    :param silence: Control headless browser
    :param language: Restrict the language of hCatpcha label.
        In the current version, `language` parameter must be `zh`.
        See https://github.com/QIN2DIM/hcaptcha-challenger/issues/2
    :return:
    """
    silence = True if silence is None or "linux" in sys.platform else silence
    options = _set_options(language=language)

    # - Use chromedriver cache to improve application startup speed
    # - Requirement: undetected-chromedriver >= 3.1.5.post2
    logging.getLogger("WDM").setLevel(logging.NOTSET)
    driver_executable_path = ChromeDriverManager().install()
    version_main = get_browser_version_from_os(ChromeType.GOOGLE).split(".")[0]

    try:
        ctx = uc.Chrome(
            options=options,
            headless=silence,
            driver_executable_path=driver_executable_path,
            use_subprocess=True,
        )
    except Exception as e:
        logger.exception(e)
        ctx = uc.Chrome(
            options=options,
            headless=silence,
            version_main=int(version_main) if version_main.isdigit() else None,
        )
    return ctx
