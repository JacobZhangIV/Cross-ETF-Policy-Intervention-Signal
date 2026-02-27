#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子展示：默认用浏览器打开 Web 界面，避免 macOS 上 Tk 崩溃。

运行方式（在项目根或 factor_display 目录下）：
    python factor_display/app.py
或
    cd factor_display && python app.py

可选：指定端口
    python factor_display/app.py 8888

若需桌面 GUI（需本机 Tk 正常），请运行：
    python factor_display/app_tk.py
"""
from __future__ import print_function

import os
import sys

# 保证可 import 同目录 web_app 及 config
_cwd = os.getcwd()
_root = os.path.dirname(_cwd) if os.path.basename(_cwd) == "factor_display" else _cwd
if _root not in sys.path:
    sys.path.insert(0, _root)

# 默认不导入 tkinter，直接启动 Web 版
def main():
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    from factor_display.web_app import run
    run(port=port, open_browser=True)


if __name__ == "__main__":
    main()
