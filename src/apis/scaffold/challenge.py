# -*- coding: utf-8 -*-
# Time       : 2022/2/24 22:31
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import time
import typing

from loguru import logger

from services.recaptcha_challenger import new_challenger, AudioChallenger, VisualChallenger
from services.settings import DIR_CHALLENGE_CACHE, DIR_MODEL
from services.utils import get_challenge_ctx


def _motion(ctx, challenger: typing.Union[AudioChallenger, VisualChallenger], style: str):
    # 访问测试站点
    ctx.get("https://www.google.com/recaptcha/api2/demo")

    # 必要的容错时间
    time.sleep(3)

    # 检测到当前页面存弹出的 reCAPTCHA checkbox
    if not challenger.utils.face_the_checkbox(ctx):
        return

    # 启动人机挑战
    start = time.time()
    response = challenger.anti_recaptcha(ctx)
    challenger.log(f"演示结束，挑战总耗时: {round(time.time() - start, 2)}s - {style=} {response=}")


@logger.catch()
def solution(style: str, silence: typing.Optional[bool] = False):
    """

    :param style:
    :param silence:
    :return:
    """
    with get_challenge_ctx(silence, language="en") as ctx:
        challenger = new_challenger(
            style=style, dir_challenge_cache=DIR_CHALLENGE_CACHE, dir_model=DIR_MODEL
        )
        _motion(ctx=ctx, challenger=challenger, style=style)
