# -*- coding: utf-8 -*-
# Time       : 2022/2/24 22:31
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import time
import typing

from loguru import logger
from playwright.sync_api import sync_playwright, BrowserContext

from services.recaptcha_challenger import new_challenger, AudioChallenger, VisualChallenger
from services.settings import DIR_CHALLENGE_CACHE, DIR_MODEL


def _motion(
    ctx: BrowserContext, challenger: typing.Union[AudioChallenger, VisualChallenger], style: str
):
    page = ctx.new_page()
    # Visit the test site
    page.goto("https://www.google.com/recaptcha/api2/demo")
    # A pop-up reCAPTCHA checkbox is detected on the current page
    if not challenger.utils.face_the_checkbox(page):
        return
    # Start man-machine challenge
    start = time.time()
    is_success = challenger.anti_recaptcha(page)
    challenger.log(f"演示结束，挑战总耗时: {round(time.time() - start, 2)}s - " f"{style=} {is_success=}")
    logger.success(f"{challenger.response=}")


@logger.catch()
def solution(style: str, silence: typing.Optional[bool] = False):
    """

    :param style:
    :param silence:
    :return:
    """
    challenger = new_challenger(
        style=style, dir_challenge_cache=DIR_CHALLENGE_CACHE, dir_model=DIR_MODEL
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=silence)
        ctx = browser.new_context(locale="en-US")
        _motion(ctx=ctx, challenger=challenger, style=style)
        browser.close()
