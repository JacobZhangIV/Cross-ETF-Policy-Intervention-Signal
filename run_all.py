#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键跑全 pipeline：按顺序执行 factor_build 与 factor_test 下所有 notebook。

用法（在项目根目录 p3_adjusted_program 下）：
    python run_all.py

使用 jupyter nbconvert --execute --inplace 执行每个 notebook，确保每次运行
都真实跑过一遍内核，且 config.py 修改生效（执行前自动清除 __pycache__）。
依赖：jupyter、nbconvert 及各 notebook 用到的包需已安装。
"""

from __future__ import print_function

import os
import shutil
import subprocess
import sys

# 项目根目录（run_all.py 所在目录）
ROOT = os.path.dirname(os.path.abspath(__file__))

# 按执行顺序列出的 (子目录, notebook 文件名)
PIPELINE = [
    ("factor_build", "01_load_data_and_build_y.ipynb"),
    ("factor_build", "02_load_augmented_factor.ipynb"),
    ("factor_build", "03_relative_factor_regression_and_selection.ipynb"),
    ("factor_build", "04_fusion_by_rules_and_corr_direction.ipynb"),
    ("factor_test",  "01_load_y_and_implication.ipynb"),
    ("factor_test",  "02_plot_factors_with_mark_dates.ipynb"),
    ("factor_test",  "03_regression_fusion_vs_implication.ipynb"),
]

# 每个 notebook 允许的最长执行时间（秒）
TIMEOUT = 600


def clear_pycache(root):
    """删除 root 目录树下所有 __pycache__ 文件夹，确保 config.py 等修改立即生效。"""
    removed = 0
    for dirpath, dirnames, _ in os.walk(root):
        for d in list(dirnames):
            if d == "__pycache__":
                full = os.path.join(dirpath, d)
                shutil.rmtree(full, ignore_errors=True)
                dirnames.remove(d)
                removed += 1
    print("已清除 __pycache__ 目录: {} 个\n".format(removed))


def run_notebook(path, cwd):
    """用 jupyter nbconvert --execute --inplace 执行 notebook，原地更新输出。"""
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--inplace",
        "--ExecutePreprocessor.timeout={}".format(TIMEOUT),
        path,
    ]
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError("notebook 执行失败，返回码: {}  路径: {}".format(result.returncode, path))


def main():
    os.chdir(ROOT)
    print("=" * 60)
    print("Pipeline 根目录:", ROOT)
    print("将依次执行 {} 个 notebook\n".format(len(PIPELINE)))

    # 执行前统一清除 __pycache__，避免 config.py 改动不生效
    clear_pycache(ROOT)

    for i, (folder, nb_name) in enumerate(PIPELINE, 1):
        path = os.path.join(ROOT, folder, nb_name)
        cwd  = os.path.join(ROOT, folder)
        if not os.path.isfile(path):
            print("[{}/{}] 跳过（文件不存在）: {}/{}".format(i, len(PIPELINE), folder, nb_name))
            continue
        print("[{}/{}] 执行: {}/{}".format(i, len(PIPELINE), folder, nb_name))
        try:
            run_notebook(path, cwd)
        except RuntimeError as e:
            print("  ✗ 失败: {}".format(e), file=sys.stderr)
            sys.exit(1)
        print("  ✓ 完成\n")

    print("=" * 60)
    print("全部完成.")


if __name__ == "__main__":
    main()
