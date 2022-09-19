# -*- coding: utf-8 -*-
# Time       : 2022/1/4 13:15
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from typing import Optional, Sequence


class ChallengeException(Exception):
    def __init__(
        self, msg: Optional[str] = None, stacktrace: Optional[Sequence[str]] = None
    ) -> None:
        self.msg = msg
        self.stacktrace = stacktrace
        super().__init__()

    def __str__(self) -> str:
        exception_msg = "Message: {}\n".format(self.msg)
        if self.stacktrace:
            stacktrace = "\n".join(self.stacktrace)
            exception_msg += "Stacktrace:\n{}".format(stacktrace)
        return exception_msg


class ChallengeTimeoutException(ChallengeException):
    """挑战执行中的某一个步骤超时"""


class RiskControlSystemArmor(ChallengeException):
    """出现不可抗力的风控拦截"""


class AntiBreakOffWarning(ChallengeException):
    """切换到声纹验证异常时抛出，此时在激活checkbox时就已经通过了验证，无需进行声纹识别"""


class ElementLocationException(ChallengeException):
    """多语种问题导致的强定位方法失效"""


class ChallengeReset(ChallengeException):
    """人机挑战意外通过"""


class LabelNotFoundException(ChallengeException):
    """获取到异常的挑战标签"""
