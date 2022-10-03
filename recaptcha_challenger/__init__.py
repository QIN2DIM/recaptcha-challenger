from .core import AudioChallenger, VisualChallenger, ChallengeStyle
from .settings import config

__all__ = ["AudioChallenger", "VisualChallenger", "ChallengeStyle", "new_audio_solver"]

__version__ = "0.0.1"


def new_audio_solver() -> AudioChallenger:
    """
    ```python
    import typing

    from playwright.sync_api import sync_playwright, Page

    from recaptcha_challenger import new_audio_solver


    def motion(page: Page) -> typing.Optional[str]:
        solver = new_audio_solver()
        if solver.utils.face_the_checkbox(page):
            solver.anti_recaptcha(page)
        return solver.response


    def bytedance():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context(locale="en-US")
            page = ctx.new_page()
            page.goto("https://www.google.com/recaptcha/api2/demo")
            response = motion(page)
            print(response)
            browser.close()


    if __name__ == '__main__':
        bytedance()
    ```
    :return:
    """
    return AudioChallenger(dir_challenge_cache=config.DIR_CHALLENGE_CACHE, debug=False)
