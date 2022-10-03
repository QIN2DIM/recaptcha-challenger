from setuptools import setup, find_packages

import recaptcha_challenger

# python setup.py sdist bdist_wheel && python -m twine upload dist/*
setup(
    name="recaptcha-challenger",
    version=recaptcha_challenger.__version__,
    keywords=["recaptcha", "recaptcha-challenger", "recaptcha-solver"],
    author="QIN2DIM",
    author_email="yaoqinse@gmail.com",
    maintainer="QIN2DIM, Bingjie Yan",
    maintainer_email="yaoqinse@gmail.com, bj.yan.pa@qq.com",
    url="https://github.com/QIN2DIM/recaptcha-challenger",
    description="🦉 Gracefully face reCAPTCHA challenge with ModelHub embedded solution.",
    license="GNU General Public License v3.0",
    packages=find_packages(include=["recaptcha_challenger", "recaptcha_challenger.*", "LICENSE"]),
    install_requires=[
        "loguru>=0.6.0",
        "playwright>=1.26.1",
        "pydub>=0.25.1",
        "SpeechRecognition==3.8.1",
        "requests>=2.28.1",
        "opencv-python==4.5.5.64",
        "numpy>=1.22.4",
        "pyyaml~=6.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
)
