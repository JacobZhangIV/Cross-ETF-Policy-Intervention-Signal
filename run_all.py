#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键跑全 pipeline：按顺序执行 factor_build 与 factor_test 下所有 notebook。

用法（在项目根目录 p3_adjusted_program 下）：
    python run_all.py

不启动 Jupyter kernel，而是在当前进程内逐 cell 执行 notebook 代码，避免「Kernel died」等环境问题。
依赖：各 notebook 用到的包（pandas、scipy、matplotlib、openpyxl 等）需已安装。
"""

from __future__ import print_function

import json
import os
import sys

# 项目根目录（run_all.py 所在目录）
ROOT = os.path.dirname(os.path.abspath(__file__))

# 按执行顺序列出的 (子目录, notebook 文件名)
PIPELINE = [
    ("factor_build", "01_load_data_and_build_y.ipynb"),
    ("factor_build", "02_load_augmented_factor.ipynb"),
    ("factor_build", "03_relative_factor_regression_and_selection.ipynb"),
    ("factor_build", "04_fusion_by_rules_and_corr_direction.ipynb"),
    ("factor_test", "01_load_y_and_implication.ipynb"),
    ("factor_test", "02_plot_factors_with_mark_dates.ipynb"),
    ("factor_test", "03_regression_fusion_vs_implication.ipynb"),
]


def _cell_source(cell):
    """取 cell 的源代码字符串（兼容 list 或 str）。"""
    src = cell.get("source", [])
    if isinstance(src, list):
        return "".join(src)
    return src


def run_notebook_in_process(path, cwd):
    """在当前进程内执行一个 notebook 的所有 code cell；cwd 为 notebook 所在目录。"""
    with open(path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb.get("cells", [])
    # 保证项目根在 path 最前，便于 import config
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    elif sys.path[0] != ROOT:
        sys.path.remove(ROOT)
        sys.path.insert(0, ROOT)
    orig_cwd = os.getcwd()
    os.chdir(cwd)
    # 供 notebook 里可能用到的 display / get_ipython
    def _display(x):
        try:
            from IPython.display import display as _d
            _d(x)
        except Exception:
            print(x)
    def _get_ipython():
        return None
    globals_dict = {
        "__name__": "__main__",
        "display": _display,
        "get_ipython": _get_ipython,
    }
    try:
        for i, cell in enumerate(cells):
            if cell.get("cell_type") != "code":
                continue
            src = _cell_source(cell)
            if not src.strip():
                continue
            exec(compile(src, "<cell {}>".format(i), "exec"), globals_dict)
    finally:
        os.chdir(orig_cwd)


def main():
    os.chdir(ROOT)
    print("Pipeline 根目录:", ROOT)
    print("将依次执行 {} 个 notebook（进程内执行，不启动 kernel）\n".format(len(PIPELINE)))

    for i, (folder, nb_name) in enumerate(PIPELINE, 1):
        path = os.path.join(ROOT, folder, nb_name)
        if not os.path.isfile(path):
            print("[{}/{}] 跳过（文件不存在）: {}".format(i, len(PIPELINE), path))
            continue
        cwd = os.path.join(ROOT, folder)
        print("[{}/{}] 执行: {}/{}".format(i, len(PIPELINE), folder, nb_name))
        try:
            run_notebook_in_process(path, cwd)
        except Exception as e:
            print("失败: {}".format(path), file=sys.stderr)
            raise
        print("  完成\n")

    print("全部完成.")


if __name__ == "__main__":
    main()
