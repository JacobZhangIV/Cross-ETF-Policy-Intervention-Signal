#!/bin/bash
# 一键跑全 pipeline（在项目根目录下执行）
cd "$(dirname "$0")"
python run_all.py
exit $?
