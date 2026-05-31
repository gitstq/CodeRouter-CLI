from setuptools import setup, find_packages

setup(
    name="coderouter-cli",
    version="1.0.0",
    description="CodeRouter-CLI — 轻量级终端AI编程模型智能路由引擎",
    long_description="Lightweight Terminal AI Model Intelligent Routing Engine",
    author="CodeRouter Team",
    python_requires=">=3.8",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "coderouter=coderouter.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
