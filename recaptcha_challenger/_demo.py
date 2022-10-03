# -*- coding: utf-8 -*-
# Time       : 2022/10/3 23:46
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import time
import typing

from loguru import logger
from playwright.sync_api import BrowserContext, sync_playwright

from recaptcha_challenger import AudioChallenger, VisualChallenger
from recaptcha_challenger.core import new_challenger
from recaptcha_challenger.settings import config


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
    challenger.log(f"total: {round(time.time() - start, 2)}s - " f"{style=} {is_success=}")
    logger.success(f"{challenger.response=}")


@logger.catch()
def solution(style: str, silence: typing.Optional[bool] = False):
    """

    :param style:
    :param silence:
    :return:
    """
    challenger = new_challenger(
        style=style, dir_challenge_cache=config.DIR_CHALLENGE_CACHE, dir_model=config.DIR_MODEL
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=silence)
        ctx = browser.new_context(locale="en-US")
        _motion(ctx=ctx, challenger=challenger, style=style)
        browser.close()


if __name__ == "__main__":
    from recaptcha_challenger import ChallengeStyle

    solution(style=ChallengeStyle.AUDIO, silence=False)
