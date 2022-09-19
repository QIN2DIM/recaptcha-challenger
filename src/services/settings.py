# -*- coding: utf-8 -*-
# Time       : 2022/2/15 17:42
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import os
from os.path import join, dirname

from services.utils import ToolBox

# ---------------------------------------------------
# [√]Lock the project directory
# ---------------------------------------------------
# hcaptcha-challenger
#  ├── database
#  │   ├── logs
#  │   └── temp_cache
#  │       ├── audio
#  │       ├── visual
#  │       └── captcha_screenshot
#  ├── model
#  │   ├── _assets
#  │   ├── _memory
#  │   └── rainbow.yaml
#  └── src
#      └── objects.yaml
# ---------------------------------------------------
PROJECT_SRC = dirname(dirname(__file__))
DIR_DATABASE = join(dirname(PROJECT_SRC), "database")
DIR_MODEL = join(dirname(PROJECT_SRC), "model")
DIR_CHALLENGE_CACHE = join(DIR_DATABASE, "temp_cache")
DIR_LOG = join(DIR_DATABASE, "logs")
# ---------------------------------------------------
# [√]Server log configuration
# ---------------------------------------------------
logger = ToolBox.init_log(error=join(DIR_LOG, "error.log"), runtime=join(DIR_LOG, "runtime.log"))
# ---------------------------------------------------
# [√]Path completion
# ---------------------------------------------------
for ttf in [DIR_MODEL, DIR_CHALLENGE_CACHE]:
    os.makedirs(ttf, exist_ok=True)
