# -*- coding: utf-8 -*-
# Time       : 2022/1/16 0:25
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import typing

from apis.scaffold import challenge as challenge_handler
from apis.scaffold import install


class Scaffold:
    """System scaffolding Top-level interface commands"""

    CHALLENGE_STYLE = "audio"

    @staticmethod
    def _install(model: typing.Optional[str] = None):
        """Download Project Dependencies"""
        install.run(model=model)

    @staticmethod
    def challenge(silence: typing.Optional[bool] = False, style: typing.Optional[str] = None):
        """Dueling with hCaptcha challenge"""
        style = style or Scaffold.CHALLENGE_STYLE
        challenge_handler.solution(style=style, silence=silence)
