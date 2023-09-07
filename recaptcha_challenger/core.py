# -*- coding: utf-8 -*-
# Time       : 2022/2/24 22:29
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import os
import time
import typing
from contextlib import suppress
from urllib.parse import quote
from urllib.request import getproxies

import pydub
import requests
from loguru import logger
from playwright.sync_api import Page, Locator, expect, FrameLocator
from playwright.sync_api import TimeoutError
from speech_recognition import Recognizer, AudioFile

from .exceptions import (
    AntiBreakOffWarning,
    RiskControlSystemArmor,
    ChallengeTimeoutException,
    LabelNotFoundException,
)
from .solutions import yolo


class ChallengeStyle:
    AUDIO = "audio"
    VISUAL = "visual"


class ArmorUtils:
    """判断遇见 reCAPTCHA 的各种断言方法"""

    @staticmethod
    def fall_in_captcha_login(page: Page) -> typing.Optional[bool]:
        """检测在登录时遇到的 reCAPTCHA challenge"""

    @staticmethod
    def fall_in_captcha_runtime(page: Page) -> typing.Optional[bool]:
        """检测在运行时遇到的 reCAPTCHA challenge"""

    @staticmethod
    def face_the_checkbox(page: Page) -> typing.Optional[bool]:
        """遇见 reCAPTCHA checkbox"""
        with suppress(TimeoutError):
            page.frame_locator("//iframe[@title='reCAPTCHA']")
            return True
        return False


class ArmorKernel:
    """人机挑战的共用基础方法"""

    # <success> Challenge Passed by following the expected
    CHALLENGE_SUCCESS = "success"
    # <continue> Continue the challenge
    CHALLENGE_CONTINUE = "continue"
    # <crash> Failure of the challenge as expected
    CHALLENGE_CRASH = "crash"
    # <retry> Your proxy IP may have been flagged
    CHALLENGE_RETRY = "retry"
    # <refresh> Skip the specified label as expected
    CHALLENGE_REFRESH = "refresh"
    # <backcall> (New Challenge) Types of challenges not yet scheduled
    CHALLENGE_BACKCALL = "backcall"

    def __init__(self, dir_challenge_cache: str, style: str, debug=True, **kwargs):
        self.dir_challenge_cache = dir_challenge_cache
        self.style = style
        self.debug = debug
        self.action_name = f"{self.style.title()}Challenge"

        self.bframe = "//iframe[contains(@src,'bframe')]"
        self._response = ""

    @property
    def utils(self):
        return ArmorUtils

    @property
    def response(self):
        return self._response

    def captcha_screenshot(self, page: typing.Union[Page, Locator], name_screenshot: str = None):
        """
        保存挑战截图，需要在 get_label 之后执行

        :param page:
        :param name_screenshot: filename of the Challenge image
        :return:
        """
        if hasattr(self, "label_alias") and hasattr(self, "label"):
            _suffix = self.label_alias.get(self.label, self.label)
        else:
            _suffix = self.action_name
        _filename = (
            f"{int(time.time())}.{_suffix}.png" if name_screenshot is None else name_screenshot
        )
        _out_dir = os.path.join(os.path.dirname(self.dir_challenge_cache), "captcha_screenshot")
        _out_path = os.path.join(_out_dir, _filename)
        os.makedirs(_out_dir, exist_ok=True)

        # FullWindow screenshot or FocusElement screenshot
        page.screenshot(path=_out_path)
        return _out_path

    def log(self, message: str, **params) -> None:
        """格式化日志信息"""
        if not self.debug:
            return
        flag_ = message
        if params:
            flag_ += " - "
            flag_ += " ".join([f"{i[0]}={i[1]}" for i in params.items()])
        logger.debug(flag_)

    def _activate_recaptcha(self, page: Page):
        """处理 checkbox 激活 reCAPTCHA"""
        # --> reCAPTCHA iframe
        activator = page.frame_locator("//iframe[@title='reCAPTCHA']").locator(
            ".recaptcha-checkbox-border"
        )
        activator.click()
        self.log("Active reCAPTCHA")

        # Check reCAPTCHA accessible status for the checkbox-result
        with suppress(TimeoutError):
            if status := page.locator("#recaptcha-accessible-status").text_content(timeout=2000):
                raise AntiBreakOffWarning(status)

    def _switch_to_style(self, page: Page) -> typing.Optional[bool]:
        """
        切换验证模式 在 anti_checkbox() 执行前使用
        :param page:
        :raise AntiBreakOffWarning: 无法切换至 <声纹验证模式>
        :return:
        """
        frame_locator = page.frame_locator(self.bframe)
        # 切换至<声纹验证模式>或停留在<视觉验证模式>
        if self.style == ChallengeStyle.AUDIO:
            switcher = frame_locator.locator("#recaptcha-audio-button")
            expect(switcher).to_be_visible()
            switcher.click()
        self.log("Accept the challenge", style=self.style)
        return True

    def anti_recaptcha(self, page: Page):
        """人机挑战的执行流"""
        # [⚔] 激活 reCAPTCHA 并切换至<声纹验证模式>或<视觉验证模式>
        try:
            self._activate_recaptcha(page)
        except AntiBreakOffWarning as err:
            logger.info(err)
            return
        return self._switch_to_style(page)


class AudioChallenger(ArmorKernel):
    def __init__(self, dir_challenge_cache: str, debug: typing.Optional[bool] = True, **kwargs):
        super().__init__(
            dir_challenge_cache=dir_challenge_cache,
            style=ChallengeStyle.AUDIO,
            debug=debug,
            kwargs=kwargs,
        )

    def get_audio_download_link(self, fl: FrameLocator) -> typing.Optional[str]:
        """Returns the download address of the sound source file."""
        for _ in range(5):
            with suppress(TimeoutError):
                self.log("Play challenge audio")
                fl.locator("//button[@aria-labelledby]").click(timeout=1000)
                break
            with suppress(TimeoutError):
                header_text = fl.locator(".rc-doscaptcha-header-text").text_content(timeout=1000)
                if "Try again later" in header_text:
                    raise ConnectionError(
                        "Your computer or network may be sending automated queries."
                    )

        # Locate the sound source file url
        try:
            audio_url = fl.locator("#audio-source").get_attribute("src")
        except TimeoutError:
            raise RiskControlSystemArmor("Trapped in an inescapable risk control context")
        return audio_url

    def handle_audio(self, audio_url: str) -> str:
        """
        Location, download and transcoding of audio files

        :param audio_url: reCAPTCHA Audio Link address
        :return:
        """
        # Splice audio cache file path
        timestamp_ = int(time.time())
        path_audio_mp3 = os.path.join(self.dir_challenge_cache, f"audio_{timestamp_}.mp3")
        path_audio_wav = os.path.join(self.dir_challenge_cache, f"audio_{timestamp_}.wav")

        # Download the sound source file to the local
        self.log("Downloading challenge audio")
        _request_asset(audio_url, path_audio_mp3)

        # Convert audio format mp3 --> wav
        self.log("Audio transcoding MP3 --> WAV")
        pydub.AudioSegment.from_mp3(path_audio_mp3).export(path_audio_wav, format="wav")
        self.log("Transcoding complete", path_audio_wav=path_audio_wav)

        # Returns audio files in wav format to increase recognition accuracy
        return path_audio_wav

    def parse_audio_to_text(self, path_audio_wav: str) -> str:
        """
        Speech recognition, audio to text

        :param path_audio_wav: reCAPTCHA Audio The local path of the audio file（.wav）
        :exception speech_recognition.RequestError: Need to suspend proxy
        :exception http.client.IncompleteRead: Poor Internet Speed，
        :return:
        """
        # Internationalized language format of audio files, default en-US American pronunciation.
        language = "en-US"

        # Read audio into and cut into a frame matrix
        recognizer = Recognizer()
        audio_file = AudioFile(path_audio_wav)
        with audio_file as stream:
            audio = recognizer.record(stream)

        # Returns the text corresponding to the short audio(str)，
        # en-US Several words that are not sentence patterns
        self.log("Parsing audio file ... ")
        audio_answer = recognizer.recognize_google(audio, language=language)
        self.log("Analysis completed", audio_answer=audio_answer)

        return audio_answer

    def submit_text(self, fl: FrameLocator, text: str) -> typing.Optional[bool]:
        """
        Submit reCAPTCHA man-machine verification

        The answer text information needs to be passed in,
        and the action needs to stay in the submittable frame-page.

        :param fl:
        :param text:
        :return:
        """
        with suppress(NameError, TimeoutError):
            input_field = fl.locator("#audio-response")
            input_field.fill("")
            input_field.fill(text.lower())
            self.log("Submit the challenge")
            input_field.press("Enter")
            return True
        return False

    def is_correct(self, page: Page) -> typing.Optional[str]:
        """Check if the challenge passes"""
        with suppress(TimeoutError):
            err_resp = page.locator(".rc-audiochallenge-error-message")
            if msg := err_resp.text_content(timeout=2000):
                self.log("Challenge failed", err_message=msg)
            return self.CHALLENGE_RETRY
        self.log("Challenge success")
        self._response = page.evaluate("grecaptcha.getResponse()")
        return self.CHALLENGE_SUCCESS

    def anti_recaptcha(self, page: Page):
        if super().anti_recaptcha(page) is not True:
            return

        # [⚔] Register Challenge Framework
        frame_locator = page.frame_locator(self.bframe)
        # [⚔] Get the audio file download link
        audio_url: str = self.get_audio_download_link(frame_locator)
        # [⚔] Audio transcoding（MP3 --> WAV）increase recognition accuracy
        path_audio_wav: str = self.handle_audio(audio_url=audio_url)
        # [⚔] Speech to text
        audio_answer: str = self.parse_audio_to_text(path_audio_wav)
        # [⚔] Locate the input box and fill in the text
        if self.submit_text(frame_locator, text=audio_answer) is not True:
            self.log("reCAPTCHA Challenge submission failed")
            raise ChallengeTimeoutException
        # Judging whether the challenge is successful or not
        # Get response of the reCAPTCHA
        return self.is_correct(page)


class VisualChallenger(ArmorKernel):
    TASK_OBJECT_DETECTION = "ObjectDetection"
    TASK_BINARY_CLASSIFICATION = "BinaryClassification"

    FEATURE_DYNAMIC = "rc-imageselect-dynamic-selected"
    FEATURE_SELECTED = "rc-imageselect-tileselected"

    # TODO
    # crosswalks
    # stairs
    # vehicles
    # tractors
    # taxis
    # chimneys
    # mountains or hills
    # bridge
    # cars
    # stairs
    # 红绿灯
    # 小轿车 机动车
    # 人行横道 过街人行道
    # 公交车
    # 楼梯
    # 棕榈树
    # 拖拉机
    label_alias = {
        "zh": {
            "消防栓": "fire hydrant",
            "交通灯": "traffic light",
            "汽车": "car",
            "自行车": "bicycle",
            "摩托车": "motorcycle",
            "公交车": "bus",
            "船": "boat",
        },
        "en": {
            "a fire hydrant": "fire hydrant",
            "bicycles": "bicycle",
            "buses": "bus",
            "bus": "bus",
            "boats": "boat",
            # "bridges": "bridge",
            "car": "car",
            "cars": "car",
            # "chimneys": "chimney",
            # "crosswalks": "crosswalk",
            "motorcycles": "motorcycle",
            # "mountains or hills": "mountains",
            "traffic lights": "traffic light",
            # "taxis": "taxi",
            # "tractors": "tractor",
            # "stairs": "stair",
            # "palm trees": "tree",
            # "vehicles",
        },
    }

    def __init__(
        self,
        dir_challenge_cache: str,
        dir_model: str,
        onnx_prefix: typing.Optional[str] = None,
        screenshot: typing.Optional[bool] = False,
        debug: typing.Optional[bool] = True,
        **kwargs,
    ):
        super().__init__(
            dir_challenge_cache=dir_challenge_cache,
            style=ChallengeStyle.VISUAL,
            debug=debug,
            kwargs=kwargs,
        )
        self.dir_model = dir_model
        self.onnx_prefix = onnx_prefix
        self.screenshot = screenshot
        self.prompt: str = ""
        self.label: str = ""
        self.lang: str = "en"
        self.label_alias = VisualChallenger.label_alias[self.lang]

        # _oncall_task "object-detection" | "binary-classification"
        self._oncall_task = None

        self.yolo_model = yolo.YOLO(self.dir_model, self.onnx_prefix)

    def reload(self, page: Page):
        """Overload Visual Challenge :: In the BFrame"""
        self.log("reload challenge")
        page.frame_locator(self.bframe).locator("#recaptcha-reload-button").click()
        page.wait_for_timeout(1000)

    def check_oncall_task(self, page: Page) -> typing.Optional[str]:
        """Identify the type of task：Detection task or classification task"""
        # Usually, when the number of clickable pictures is 16, it is an object detection task,
        # and when the number of clickable pictures is 9, it is a classification task.
        image_objs = page.frame_locator(self.bframe).locator("//td[@aria-label]")
        self._oncall_task = (
            self.TASK_OBJECT_DETECTION
            if image_objs.count() > 9
            else self.TASK_BINARY_CLASSIFICATION
        )
        return self._oncall_task

    def get_label(self, page: Page):
        def split_prompt_message(prompt_message: str) -> str:
            prompt_message = prompt_message.strip()
            return prompt_message

        # Captcha prompts
        label_obj = page.frame_locator(self.bframe).locator("//strong")
        self.prompt = label_obj.text_content()
        # Parse prompts to model label
        try:
            _label = split_prompt_message(prompt_message=self.prompt)
        except (AttributeError, IndexError):
            raise LabelNotFoundException("Get the exception label object")
        else:
            self.label = _label
            self.log(
                message="Get label", label=f"「{self.label}」", task=f"{self.check_oncall_task(page)}"
            )

    def select_model(self):
        """Optimizing solutions based on different challenge labels"""
        # label_alias = self.label_alias.get(self.label)
        return self.yolo_model

    def check_positive_element(
        self, sample: Locator, model, screenshot: typing.Optional[bool] = False
    ) -> typing.Optional[bool]:
        """Review positive samples"""
        result = model.solution(img_stream=sample.screenshot(), label=self.label_alias[self.label])

        # Pass: Hit at least one object
        if result:
            sample.click()

        # Check result of the challenge.
        if screenshot or self.screenshot:
            _filename = f"{int(time.time())}.{model.flag}.{self.label_alias[self.label]}.png"
            self.captcha_screenshot(sample, name_screenshot=_filename)

        return result

    def challenge(self, page: Page, model):
        """Image classification, element clicks, answer submissions"""

        def hit_dynamic_samples(target: list):
            if not target:
                return
            for i in target:
                locator_ = f'//td[@tabindex="{i + 4}"]'
                # Gradient control
                # Ensure that the pictures fed into the model are correctly exposed.
                with suppress(TimeoutError, AssertionError):
                    expect(page.frame_locator(self.bframe).locator(locator_)).to_have_attribute(
                        "class", self.FEATURE_DYNAMIC
                    )
                dynamic_element = page.frame_locator(self.bframe).locator(locator_)
                result_ = self.check_positive_element(sample=dynamic_element, model=model)
                if not result_:
                    target.remove(i)
            return hit_dynamic_samples(target)

        is_dynamic = None
        dynamic_index = []
        samples = page.frame_locator(self.bframe).locator("//td[@aria-label]")
        for index in range(samples.count()):
            result = self.check_positive_element(sample=samples.nth(index), model=model)
            if is_dynamic is None:
                motion_status = (
                    page.frame_locator(self.bframe)
                    .locator(f'//td[@tabindex="{index + 4}"]')
                    .get_attribute("class")
                )
                if self.FEATURE_SELECTED in motion_status:
                    is_dynamic = False
                elif self.FEATURE_DYNAMIC in motion_status:
                    is_dynamic = True
            if result:
                dynamic_index.append(index)

        # Winter is coming
        if is_dynamic:
            hit_dynamic_samples(target=dynamic_index)
        # Submit challenge
        page.frame_locator(self.bframe).locator("//button[@id='recaptcha-verify-button']").click()

    def check_accessible_status(self, page: Page) -> typing.Optional[str]:
        """Judging whether the challenge was successful"""
        try:
            prompt_obj = page.frame_locator(self.bframe).locator(
                "//div[@class='rc-imageselect-error-select-more']"
            )
            prompt_obj.wait_for(timeout=1000)
        except TimeoutError:
            try:
                prompt_obj = page.frame_locator(self.bframe).locator(
                    "rc-imageselect-incorrect-response"
                )
                prompt_obj.wait_for(timeout=1000)
            except TimeoutError:
                self.log("挑战成功")
                return self.CHALLENGE_SUCCESS

        prompts = prompt_obj.text_content()
        return prompts

    def tactical_retreat(self, page: Page) -> typing.Optional[str]:
        """
        「blacklist mode」 skip unchoreographed challenges
        :param page:
        :return: the screenshot storage path
        """
        if self.label_alias.get(self.label):
            return self.CHALLENGE_CONTINUE

        # Save a screenshot of the challenge
        with suppress(TimeoutError):
            challenge_container = page.frame_locator(self.bframe).locator(
                "//body[@class='no-selection']"
            )
            path_screenshot = self.captcha_screenshot(challenge_container)
            q = quote(self.label, "utf8")
            issues = f"https://github.com/QIN2DIM/hcaptcha-challenger/issues?q={q}"
            logger.warning(
                "Types of challenges not yet scheduled - "
                f"label=「{self.label}」 prompt=「{self.prompt}」 "
                f"{path_screenshot=} {page.url=} {issues=}"
            )

        return self.CHALLENGE_BACKCALL

    def anti_recaptcha(self, page: Page):
        """
        >> NOTE:
        ——————————————————————————————————————————————————————————————————————————
        在可访问的 `检测任务` 中，reCAPTCHA v2 实现了『多组多单位目标』的挑战呈现方案，即：
            1.「NEXT」需要识别的目标正常出现，通常是多单位目标
            2.「SKIP」16张图片组成的场景信息中未实际出现需要识别的目标，此时需要跳过挑战
            3.通常，遇到检测任务说明你已被标记为高风险访客，将会频繁遇到 traffic_lights，crosswalks 之类的标签
                最佳实践中，建议通过 `reload` 的方式切换到分类任务
        ——————————————————————————————————————————————————————————————————————————
        在可访问的 `分类任务` 中，reCAPTCHA v2 实现了『单组渐变加噪』的挑战呈现方案，即：
            1.「VERIFY」不同于检测任务，分类任务通常只有一组需要分类的图片，点击验证提交挑战
            2.通常，一组分类任务不止 9 张图（但一次仅呈现9张）
                - （OptionalStyle）点击某张图片后，被点击的网格句柄将以 **渐变** 的形式替换一张新的图片，
                    你的威胁评分越高，即，你短时间内的请求频率越高，渐变耗时越长
                - 当所有网格中的阳性对象消失，即，当前视图中所有阳性均已被选中后，
                点击提交才能通过挑战（要求正确率 100%）否则会遇到 error-prompt
                - 遇到 error-prompt 时，挑战不会自动刷新，而是停留在当前上下文，需要继续选完所有阳性图片。
            3. 分类任务中会出现「人类可见的」噪声图片。
        ——————————————————————————————————————————————————————————————————————————
        一阶状态机：
            - Reload challenge 刷新挑战后标签和图片一起改变
            - rc-imageselect-dynamic-selected 渐变时网格按钮的附加的 CLASS_NAME
            - rc-imageselect-tileselected 普通选中效果
        异常状态表：
            - Please select all matching images. 当前上下文仍有未消除的阳性样本
            - Please also check the new images. 分类任务中，在网格渐变时提交挑战，需要等待图片完全加载。
                弹出此提示时，挑战上下文不变，即，prompts 与 images 都不会变
            - Please try again. 评分过低，重试
        """
        if super().anti_recaptcha(page) is not True:
            return
        # [⚔] Register Challenge Framework
        # TODO: TASK_OBJECT_DETECTION, more label
        for _ in range(3):
            # [⚔] Skip objects detection tasks and unprepared classification tasks
            for _ in range(10):
                # [⚔] Get challenge labels
                self.get_label(page)
                if self._oncall_task == self.TASK_OBJECT_DETECTION:
                    self.reload(page)
                elif self.tactical_retreat(page) == self.CHALLENGE_BACKCALL:
                    self.reload(page)
                else:
                    break

            model = self.select_model()
            self.challenge(page, model=model)
            self.captcha_screenshot(page)
            if drop := self.check_accessible_status(page) == self.CHALLENGE_SUCCESS:
                self._response = page.evaluate("grecaptcha.getResponse()")
                return drop
        else:
            input("This method has not been implemented yet, press any key to exit the program.")


def _request_asset(asset_download_url: str, asset_path: str):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.27"
    }

    # FIXME: PTC-W6004
    #  Audit required: External control of file name or path
    with open(asset_path, "wb") as file, requests.get(
        asset_download_url, headers=headers, stream=True, proxies=getproxies()
    ) as response:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)


def new_challenger(
    style: str,
    dir_challenge_cache: str,
    dir_model: typing.Optional[str] = None,
    onnx_prefix: typing.Optional[str] = None,
    debug: typing.Optional[bool] = True,
) -> typing.Union[AudioChallenger, VisualChallenger]:
    # Check cache dir of challenge
    if not os.path.isdir(dir_challenge_cache):
        raise FileNotFoundError("dir_challenge_cache should be an existing file directory.")
    dir_payload = os.path.join(dir_challenge_cache, style)
    os.makedirs(dir_payload, exist_ok=True)

    # Check challenge style
    if style in [ChallengeStyle.AUDIO]:
        return AudioChallenger(dir_challenge_cache=dir_payload, debug=debug)
    elif style in [ChallengeStyle.VISUAL]:
        return VisualChallenger(
            dir_challenge_cache=dir_payload,
            debug=debug,
            dir_model=dir_model,
            onnx_prefix=onnx_prefix,
        )
    else:
        raise TypeError(
            f"style({style}) should be {ChallengeStyle.AUDIO} or {ChallengeStyle.VISUAL}"
        )
