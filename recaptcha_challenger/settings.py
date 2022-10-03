# -*- coding: utf-8 -*-
# Time       : 2022/2/15 17:42
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import os
from dataclasses import dataclass

from .utils import init_log


@dataclass
class Config:
    PROJECT_PAYLOAD: str = "datas"
    DIR_MODEL = os.path.join(PROJECT_PAYLOAD, "models")
    DIR_CHALLENGE_CACHE = os.path.join(PROJECT_PAYLOAD, "temp_cache")
    DIR_LOG = os.path.join(PROJECT_PAYLOAD, "logs")

    def __post_init__(self):
        for ttf in [self.DIR_MODEL, self.DIR_CHALLENGE_CACHE]:
            os.makedirs(ttf, exist_ok=True)

    def register_logger(self):
        log_path_error = os.path.join(self.DIR_LOG, "error.log")
        log_path_runtime = os.path.join(self.DIR_LOG, "runtime.log")
        return init_log(error=log_path_error, runtime=log_path_runtime)


config = Config()
logger = config.register_logger()
