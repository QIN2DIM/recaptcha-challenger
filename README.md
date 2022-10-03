<div align="center">
    <h1> reCAPTCHA Challenger</h1>
    <p>🦉<i>Gracefully face reCAPTCHA challenge with ModelHub embedded solution.</i></p>
    <img src="https://img.shields.io/static/v1?message=reference&color=blue&style=for-the-badge&logo=micropython&label=python">
    <img src="https://img.shields.io/github/license/QIN2DIM/recaptcha-challenger?style=for-the-badge">
    <a href="https://github.com/QIN2DIM/recaptcha-challenger/releases"><img src="https://img.shields.io/github/downloads/qin2dim/recaptcha-challenger/total?style=for-the-badge"></a>
	<br>
    <a href="https://github.com/QIN2DIM/recaptcha-challenger/"><img src="https://img.shields.io/github/stars/QIN2DIM/recaptcha-challenger?style=social"></a>
	<a href = "https://t.me/+tJrSQ0_0ujkwZmZh"><img src="https://img.shields.io/static/v1?style=social&logo=telegram&label=chat&message=studio" ></a>
	<br>
	<br>
</div>

![recaptcha-challenge-demo](https://user-images.githubusercontent.com/62018067/193613510-ffb6b316-f027-47f5-9f7a-9795465b635c.gif)

## Quick Start

1. **Pull PyPi packages**

   ```bash
   pip install recaptcha-challenger
   ```

2. **Just do it**

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
   
   
   if __name__ == "__main__":
       bytedance()
   
   ```

   
