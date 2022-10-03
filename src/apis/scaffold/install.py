# -*- coding: utf-8 -*-
# Time       : 2022/1/20 16:16
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from typing import Optional

from services.recaptcha_challenger import YOLO
from services.settings import DIR_MODEL, logger


def _download_model(onnx_prefix: Optional[str] = None):
    """下载 YOLOv4 目标检测模型"""
    logger.debug("Downloading YOLOv5 object detection model...")

    YOLO(dir_model=DIR_MODEL, onnx_prefix=onnx_prefix).pull_model()
