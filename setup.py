from setuptools import setup

setup(
    name="go2web",
    version="0.1",
    py_modules=["go2web"],
    entry_points={
        "console_scripts": [
            "go2web=go2web:main",
        ],
    },
)