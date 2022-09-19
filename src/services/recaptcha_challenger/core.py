# -*- coding: utf-8 -*-
# Time       : 2022/2/24 22:29
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import os
import random
import time
import typing
from urllib.parse import quote
from urllib.request import getproxies

import pydub
import requests
from loguru import logger
from selenium.common.exceptions import (
    ElementNotVisibleException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from speech_recognition import Recognizer, AudioFile

from .exceptions import (
    AntiBreakOffWarning,
    RiskControlSystemArmor,
    ChallengeTimeoutException,
    ChallengeReset,
    LabelNotFoundException,
)
from .solutions import yolo


class ChallengeStyle:
    AUDIO = "audio"
    VISUAL = "visual"


class ArmorUtils:
    """判断遇见 reCAPTCHA 的各种断言方法"""

    @staticmethod
    def fall_in_captcha_login(ctx: Chrome) -> typing.Optional[bool]:
        """检测在登录时遇到的 reCAPTCHA challenge"""

    @staticmethod
    def fall_in_captcha_runtime(ctx: Chrome) -> typing.Optional[bool]:
        """检测在运行时遇到的 reCAPTCHA challenge"""

    @staticmethod
    def face_the_checkbox(ctx: Chrome) -> typing.Optional[bool]:
        """遇见 reCAPTCHA checkbox"""
        try:
            WebDriverWait(ctx, 8, ignored_exceptions=WebDriverException).until(
                EC.presence_of_element_located((By.XPATH, "//iframe[@title='reCAPTCHA']"))
            )
            return True
        except TimeoutException:
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

    @property
    def utils(self):
        return ArmorUtils

    def captcha_screenshot(
            self, ctx: typing.Union[Chrome, WebElement], name_screenshot: str = None
    ):
        """
        保存挑战截图，需要在 get_label 之后执行

        :param name_screenshot: filename of the Challenge image
        :param ctx: Webdriver 或 Element
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
        try:
            ctx.screenshot(_out_path)
        except AttributeError:
            ctx.save_screenshot(_out_path)
        return _out_path

    def log(self, message: str, **params) -> None:
        """格式化日志信息"""
        if not self.debug:
            return

        motive = "Challenge"
        flag_ = f">> {motive} [{self.action_name}] {message}"
        if params:
            flag_ += " - "
            flag_ += " ".join([f"{i[0]}={i[1]}" for i in params.items()])
        logger.debug(flag_)

    def _activate_recaptcha(self, ctx: Chrome):
        """处理 checkbox 激活 reCAPTCHA"""
        # --> reCAPTCHA iframe
        WebDriverWait(ctx, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[@title='reCAPTCHA']"))
        )

        # 点击并激活 reCAPTCHA
        WebDriverWait(ctx, 10, poll_frequency=0.5, ignored_exceptions=NoSuchElementException).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
        ).click()
        self.log("Active reCAPTCHA")

        # Check reCAPTCHA accessible status for the checkbox-result
        try:
            status = (
                WebDriverWait(ctx, 2, poll_frequency=0.1)
                .until(EC.presence_of_element_located((By.ID, "recaptcha-accessible-status")))
                .text
            )
            if status:
                raise AntiBreakOffWarning(status)
        except (TimeoutException, AttributeError):
            pass
        finally:
            ctx.switch_to.default_content()

    def _switch_to_style(self, ctx: Chrome) -> typing.Optional[bool]:
        """
        切换验证模式 在 anti_checkbox() 执行前使用
        :param ctx:
        :raise AntiBreakOffWarning: 无法切换至 <声纹验证模式>
        :return:
        """
        time.sleep(2)

        # 切换到 reCAPTCHA 验证框架
        WebDriverWait(ctx, 8).until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.XPATH, f"//iframe[contains(@src,'bframe')]")
            )
        )

        # 切换至<声纹验证模式>或停留在<视觉验证模式>
        self.log("Accept the challenge", style=self.style)
        if self.style == ChallengeStyle.AUDIO:
            ctx.find_element(By.ID, "recaptcha-audio-button").click()
            time.sleep(random.uniform(1, 3))
        return True

    def anti_recaptcha(self, ctx: Chrome):
        """人机挑战的执行流"""
        # [⚔] 激活 reCAPTCHA 并切换至<声纹验证模式>或<视觉验证模式>
        try:
            self._activate_recaptcha(ctx)
        except AntiBreakOffWarning as err:
            logger.info(err)
            return
        return self._switch_to_style(ctx)


class AudioChallenger(ArmorKernel):
    def __init__(self, dir_challenge_cache: str, debug: typing.Optional[bool] = True, **kwargs):
        super().__init__(
            dir_challenge_cache=dir_challenge_cache,
            style=ChallengeStyle.AUDIO,
            debug=debug,
            kwargs=kwargs,
        )

    def get_audio_download_link(
            self, ctx: Chrome, click_on_player: typing.Optional[bool] = True
    ) -> typing.Optional[str]:
        """返回声源文件的下载地址"""
        if click_on_player:
            self.log("Play challenge audio")
            try:
                ctx.find_element(By.XPATH, "//button[@aria-labelledby]").click()
            except NoSuchElementException:
                try:
                    header_obj = ctx.find_element(By.CLASS_NAME, "rc-doscaptcha-header-text")
                    if "Try again later" in header_obj.text:
                        raise ConnectionError("Your computer or network may be sending automated queries.")
                except NoSuchElementException:
                    return

        # 定位声源文件 url
        try:
            audio_url = ctx.find_element(By.ID, "audio-source").get_attribute("src")
        except NoSuchElementException:
            raise RiskControlSystemArmor("Trapped in an inescapable risk control context")
        else:
            return audio_url

    def handle_audio(self, audio_url: str) -> str:
        """
        reCAPTCHA Audio 音频文件的定位、下载、转码

        :param audio_url: reCAPTCHA Audio 链接地址
        :return:
        """

        # 拼接音频缓存文件路径
        timestamp_ = int(time.time())
        path_audio_mp3 = os.path.join(self.dir_challenge_cache, f"audio_{timestamp_}.mp3")
        path_audio_wav = os.path.join(self.dir_challenge_cache, f"audio_{timestamp_}.wav")

        # 将声源文件下载到本地
        self.log("Downloading challenge audio")
        _request_asset(audio_url, path_audio_mp3)

        # 转换音频格式 mp3 --> wav
        self.log("Audio transcoding MP3 --> WAV")
        pydub.AudioSegment.from_mp3(path_audio_mp3).export(path_audio_wav, format="wav")
        self.log("Transcoding complete", path_audio_wav=path_audio_wav)

        # 返回 wav 格式的音频文件 增加识别精度
        return path_audio_wav

    def parse_audio_to_text(self, path_audio_wav: str) -> str:
        """
        声纹识别，音频转文本

        :param path_audio_wav: reCAPTCHA Audio 音频文件的本地路径（wav格式）
        :exception speech_recognition.RequestError: 需要挂起代理
        :exception http.client.IncompleteRead: 网速不佳，音频文件未下载完整就开始解析
        :return:
        """
        # 音频文件的国际化语言格式，默认 en-US 美式发音。非必要参数，但可增加模型精度。
        language = "en-US"

        # 将音频读入并切割成帧矩阵
        recognizer = Recognizer()
        audio_file = AudioFile(path_audio_wav)
        with audio_file as stream:
            audio = recognizer.record(stream)

        # 返回短音频对应的文本(str)，en-US 情况下为不成句式的若干个单词
        self.log("正在解析音频文件 ... ")
        audio_answer = recognizer.recognize_google(audio, language=language)
        self.log("解析完毕", audio_answer=audio_answer)

        return audio_answer

    def submit_text(self, ctx: Chrome, text: str) -> typing.Optional[bool]:
        """
        提交 reCAPTCHA 人机验证，需要传入 answer 文本信息，需要 action 停留在可提交界面

        :param ctx: 为尽可能消除 driver 指纹特征，可使用  undetected_chromedriver.v2 替代 selenium
        :param text: 声纹识别数据
        :return:
        """
        try:
            # 定位回答框
            input_field = ctx.find_element(By.ID, "audio-response")

            # 提交文本数据
            input_field.clear()
            input_field.send_keys(text.lower())

            # 使用 clear + ENTER 消除控制特征
            self.log("Submit the challenge")
            input_field.send_keys(Keys.ENTER)
            return True
        except (NameError, NoSuchElementException):
            return False

    def is_correct(self, ctx: Chrome) -> typing.Optional[str]:
        """检查挑战是否通过"""
        try:
            err_message = (
                WebDriverWait(ctx, 1)
                .until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "rc-audiochallenge-error-message")
                    )
                )
                .text
            )
            if err_message:
                self.log("挑战失败", err_message=err_message)
            return self.CHALLENGE_RETRY
        except TimeoutException:
            self.log("挑战成功")
            return self.CHALLENGE_SUCCESS

    def anti_recaptcha(self, ctx: Chrome):
        if super().anti_recaptcha(ctx) is not True:
            return

        # [⚔] 获取音频文件下载链接
        audio_url: str = self.get_audio_download_link(ctx)

        # [⚔] 音频转码（MP3 --> WAV）增加识别精度
        path_audio_wav: str = self.handle_audio(audio_url=audio_url)

        # [⚔] 声纹识别 --(output)--> 文本数据
        audio_answer: str = self.parse_audio_to_text(path_audio_wav)

        # [⚔] 定位输入框并填写文本数据
        if self.submit_text(ctx, text=audio_answer) is not True:
            self.log("reCAPTCHA 挑战提交失败")
            raise ChallengeTimeoutException

        # 回到 main-frame 否则后续 DOM 操作无法生效
        ctx.switch_to.default_content()

        # 判断挑战是否成功
        return self.is_correct(ctx)


class VisualChallenger(ArmorKernel):
    TASK_OBJECT_DETECTION = "ObjectDetection"
    TASK_BINARY_CLASSIFICATION = "BinaryClassification"

    FEATURE_DYNAMIC = "rc-imageselect-dynamic-selected"
    FEATURE_SELECTED = "rc-imageselect-tileselected"

    # crosswalks
    # stairs
    # vehicles
    # tractors
    # taxis
    # chimneys
    # mountains or hills
    # bridge
    # cars
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
            "traffic lights": "traffic light",
            "car": "car",
            "bicycles": "bicycle",
            "motorcycles": "motorcycle",
            "bus": "bus",
            "buses": "bus",
            "cars": "car",
            "boats": "boat",
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

    @staticmethod
    def reload(ctx: Chrome):
        """Overload Visual Challenge :: In the BFrame"""
        WebDriverWait(ctx, 5).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-reload-button"))
        ).click()
        time.sleep(1)

    def check_oncall_task(self, ctx: Chrome) -> typing.Optional[str]:
        """识别任务类型：检测任务或分类任务"""
        try:
            WebDriverWait(ctx, 10).until(
                EC.presence_of_element_located((By.XPATH, "//td[@aria-label]"))
            )
        except TimeoutException as err:
            raise RuntimeError("Check task type timeout, need to refresh challenge") from err
        else:
            # Usually, when the number of clickable pictures is 16, it is an object detection task,
            # and when the number of clickable pictures is 9, it is a classification task.
            image_objs = ctx.find_elements(By.XPATH, "//td[@aria-label]")
            self._oncall_task = (
                self.TASK_OBJECT_DETECTION
                if len(image_objs) > 9
                else self.TASK_BINARY_CLASSIFICATION
            )
            return self._oncall_task

    def get_label(self, ctx: Chrome):
        def split_prompt_message(prompt_message: str) -> str:
            prompt_message = prompt_message.strip()
            return prompt_message

        # Captcha prompts
        try:
            label_obj = WebDriverWait(ctx, 30, ignored_exceptions=ElementNotVisibleException).until(
                EC.presence_of_element_located((By.TAG_NAME, "strong"))
            )
        except TimeoutException:
            raise ChallengeReset("人机挑战意外通过")
        else:
            self.prompt = label_obj.text

        # Parse prompts to model label
        try:
            _label = split_prompt_message(prompt_message=self.prompt)
        except (AttributeError, IndexError):
            raise LabelNotFoundException("Get the exception label object")
        else:
            self.label = _label
            self.log(
                message="Get label", label=f"「{self.label}」", task=f"{self.check_oncall_task(ctx)}"
            )

    def select_model(self):
        """Optimizing solutions based on different challenge labels"""
        # label_alias = self.label_alias.get(self.label)
        return self.yolo_model

    def mark_samples(self, ctx: Chrome):
        """Get the download link and locator of each challenge image"""
        samples = ctx.find_elements(By.XPATH, "//td[@aria-label]")
        if samples:
            for index, sample in enumerate(samples):
                fn = f"{int(time.time())}_/Challenge Image {index + 1}.png"
                self.captcha_screenshot(sample, name_screenshot=fn)
                self.log("save image", fn=fn)

        image_link = ctx.find_element(By.XPATH, "//td[@aria-label]//img").get_attribute("src")
        self.log(image_link)

    def check_positive_element(
            self, element: WebElement, model, screenshot: typing.Optional[bool] = False
    ) -> typing.Optional[bool]:
        """审查阳性样本"""
        result = model.solution(
            img_stream=bytes(element.screenshot_as_png), label=self.label_alias[self.label]
        )

        # Pass: Hit at least one object
        if result:
            try:
                time.sleep(random.uniform(0.2, 0.3))
                element.click()
            except StaleElementReferenceException:
                pass
            except WebDriverException as err:
                logger.warning(err)

        # Check result of the challenge.
        if screenshot or self.screenshot:
            _filename = f"{int(time.time())}.{model.flag}.{self.label_alias[self.label]}.png"
            self.captcha_screenshot(element, name_screenshot=_filename)

        return result

    def challenge(self, ctx: Chrome, model):
        """Image classification, element clicks, answer submissions"""

        def hit_dynamic_samples(target: list):
            if not target:
                return
            for i in target:
                locator_ = f'//td[@tabindex="{i + 4}"]'

                # 渐变控制，尽可能确保送入模型的图片的曝光正确
                start = time.time()
                WebDriverWait(ctx, 60, poll_frequency=1).until_not(
                    EC.text_to_be_present_in_element_attribute(
                        locator=(By.XPATH, locator_), attribute_="class", text_=self.FEATURE_DYNAMIC
                    )
                )
                time.sleep(time.time() - start)

                dynamic_element = ctx.find_element(By.XPATH, locator_)
                result_ = self.check_positive_element(element=dynamic_element, model=model)
                if not result_:
                    target.remove(i)
            return hit_dynamic_samples(target)

        is_dynamic = None
        dynamic_index = []
        samples = ctx.find_elements(By.XPATH, "//td[@aria-label]")
        for index, sample in enumerate(samples):
            result = self.check_positive_element(element=sample, model=model)
            if is_dynamic is None:
                try:
                    motion_status = ctx.find_element(
                        By.XPATH, f'//td[@tabindex="{index + 4}"]'
                    ).get_attribute("class")
                except (NoSuchElementException, AttributeError):
                    pass
                else:
                    if self.FEATURE_SELECTED in motion_status:
                        is_dynamic = False
                    elif self.FEATURE_DYNAMIC in motion_status:
                        is_dynamic = True
            if result:
                dynamic_index.append(index)

        # 凛冬将至
        if is_dynamic:
            hit_dynamic_samples(target=dynamic_index)

        # Submit challenge
        try:
            WebDriverWait(ctx, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@id='recaptcha-verify-button']"))
            ).click()
        except ElementClickInterceptedException:
            pass
        except WebDriverException as err:
            logger.exception(err)

    def check_accessible_status(self, ctx: Chrome) -> typing.Optional[str]:
        """Judging whether the challenge was successful"""
        try:
            prompt_obj = WebDriverWait(ctx, 1).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@class='rc-imageselect-error-select-more']")
                )
            )
        except TimeoutException:
            try:
                prompt_obj = WebDriverWait(ctx, 1).until(
                    EC.visibility_of_element_located(
                        (By.CLASS_NAME, "rc-imageselect-incorrect-response")
                    )
                )
            except TimeoutException:
                self.log("挑战成功")
                return self.CHALLENGE_SUCCESS

        prompts = prompt_obj.text
        return prompts

    def tactical_retreat(self, ctx) -> typing.Optional[str]:
        """
        「blacklist mode」 skip unchoreographed challenges
        :param ctx:
        :return: the screenshot storage path
        """
        if self.label_alias.get(self.label):
            return self.CHALLENGE_CONTINUE

        # Save a screenshot of the challenge
        path_screenshot = ""
        try:
            challenge_container = ctx.find_element(By.XPATH, "//body[@class='no-selection']")
            path_screenshot = self.captcha_screenshot(challenge_container)
        except NoSuchElementException:
            pass
        except WebDriverException as err:
            logger.exception(err)
        finally:
            q = quote(self.label, "utf8")
            logger.warning(
                runtime_report(
                    motive="ALERT",
                    action_name=self.action_name,
                    message="Types of challenges not yet scheduled",
                    label=f"「{self.label}」",
                    prompt=f"「{self.prompt}」",
                    screenshot=path_screenshot,
                    site_link=ctx.current_url,
                    issues=f"https://github.com/QIN2DIM/hcaptcha-challenger/issues?q={q}",
                )
            )
            return self.CHALLENGE_BACKCALL

    def anti_recaptcha(self, ctx: Chrome):
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
        if super().anti_recaptcha(ctx) is not True:
            return

        # TODO: TASK_OBJECT_DETECTION, more label
        for _ in range(3):
            for _ in range(10):
                # [⚔] 获取挑战标签
                self.get_label(ctx)

                if self._oncall_task == self.TASK_OBJECT_DETECTION:
                    self.reload(ctx)
                elif self.tactical_retreat(ctx) == self.CHALLENGE_BACKCALL:
                    self.reload(ctx)
                else:
                    break

            model = self.select_model()
            self.challenge(ctx, model=model)
            self.captcha_screenshot(ctx)

            if drop := self.check_accessible_status(ctx) == self.CHALLENGE_SUCCESS:
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


def runtime_report(action_name: str, motive: str = "RUN", message: str = "", **params) -> str:
    """格式化输出"""
    flag_ = f">> {motive} [{action_name}]"
    if message != "":
        flag_ += f" {message}"
    if params:
        flag_ += " - "
        flag_ += " ".join([f"{i[0]}={i[1]}" for i in params.items()])

    return flag_


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
