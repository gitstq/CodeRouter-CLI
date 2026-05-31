"""
CodeRouter-CLI 入口模块 / CodeRouter-CLI Entry Module

支持通过 python -m coderouter 方式运行。
Supports running via python -m coderouter.
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
