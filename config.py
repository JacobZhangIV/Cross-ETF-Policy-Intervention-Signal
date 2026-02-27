# -*- coding: utf-8 -*-
"""
统一配置：运行 notebook 时可能需修改的参数集中在此修改。

使用：在 01_load_data_and_build_y.ipynb 等 notebook 开头 import config，
     路径、列名、样本截止等均从 config 读取；改参数只需改本文件。
"""
import os

# -----------------------------------------------------------------------------
# 路径（一般不用改；若数据不在默认位置可在此指定）
# -----------------------------------------------------------------------------
# 项目根目录。None = 自动根据当前工作目录推断（在 factor_build 下运行时取上一级）
BASE_DIR = None

# 数据目录。None = 使用 BASE_DIR/Data
DATA_DIR = None

# -----------------------------------------------------------------------------
# 样本截止（用于留出样本外测试）
# -----------------------------------------------------------------------------
# 只使用该日期及之前的数据；None = 使用全部数据
# 例：CUTOFF_DATE = (2025, 1, 1)  或  datetime.date(2025, 1, 1)
CUTOFF_DATE = None

# -----------------------------------------------------------------------------
# 列名（若 Excel 表头与默认不同可在此修改）
# -----------------------------------------------------------------------------
# 日期列名（行情表、因子表里的交易日期）
DATE_COL = "交易日期"

# 涨跌幅列名（行情表里一般为 涨跌幅(%)）
PCT_COL = "涨跌幅(%)"

# -----------------------------------------------------------------------------
# 行情文件匹配（用于从 Data 下多个文件中识别 上证50 / 上证1000 行情）
# -----------------------------------------------------------------------------
# 文件名需同时包含这些关键词才视为「上证50 行情」
FILE_KEYWORDS_CSI50 = ("上证50", "行情")

# 文件名需同时包含这些关键词才视为「上证1000 行情」
FILE_KEYWORDS_CSI1000 = ("上证1000", "行情")

# 增强版国家队因子 Excel 文件名（Data 目录下）
AUGMENTED_FACTOR_FILENAME = "因子_国家队_增强版_pair_zscore.xlsx"

# 每个因子（标的列）做 rolling z-score 的窗口长度
ROLLING_ZSCORE_WINDOW = 90
# 窗口内参与均值和标准差的只取有效值（非 0 且非空）；至少需要该个数的有效值才输出 z，保证因子一旦开始就连续
ROLLING_ZSCORE_MIN_VALID_IN_WINDOW = 90

# 相对因子：在同一因子(sheet)内按 (标的A, 标的B) 做差，形成 标的A - 标的B 的相对资金净流入类因子
# 每项为 (code_a, code_b)，结果为 rolling_z(code_a) - rolling_z(code_b)
RELATIVE_FACTOR_PAIRS = [
    ("510050.SH", "510100.SH"),
    ("588080.SH", "588050.SH"),
    ("159915.SZ", "159952.SZ"),
    ("159915.SZ", "159977.SZ"),
]

# -----------------------------------------------------------------------------
# Excel 读取
# -----------------------------------------------------------------------------
# 数据目录下要读取的扩展名
EXCEL_EXTENSIONS = (".xlsx", ".xls")

# 排除的文件名前缀（如 Excel 临时文件）
SKIP_FILE_PREFIX = "~$"

# 波动率与股债指数 Excel 文件名（Data 目录下，factor_test 用）
IMPLICATION_EXCEL_FILENAME = "数据_波动率与股债指数.xlsx"

# -----------------------------------------------------------------------------
# 因子回归与筛选（03 用）
# -----------------------------------------------------------------------------
# 时滞：因子早、大盘减小盘反应晚。回归 y(当日+lag) ~ factor(当日)，lag 取以下列表中的值（单位：交易日）
# 如 [0,1,2,3] 表示当日因子预测当日/次日/2日后/3日后 的 y
REGRESSION_LAG_DAYS = [0, 1, 2, 3]
# 单因子对 y 的回归：p 值低于此阈值视为显著
REGRESSION_MAX_PVALUE = 0.05
# 单因子与 y 的 |相关系数| 不低于此才考虑入选（可选，None 表示不按相关系数过滤）
REGRESSION_MIN_ABS_CORR = None

# -----------------------------------------------------------------------------
# 融合筛选规则（04 用）：按 lag 与名字筛选后等权融合
# -----------------------------------------------------------------------------
# 参与融合的 lag：只保留回归结果中 lag 在此列表中的因子
FUSION_LAG_ALLOWED = [0, 1, 2, 3]
# 参与融合的 sheet（因子类型）：None = 全部；否则为要保留的 sheet 名列表
FUSION_SHEET_INCLUDE = None
# 参与融合的标的对：None = 全部；否则为 标的对 列中需包含的字符串（满足任一即保留）
# 例：["510050", "588080"] 表示只保留名称中含 510050 或 588080 的标的对
FUSION_PAIR_INCLUDE = None

# factor_build 各层 Excel 输出目录（相对 factor_build 文件夹）；每次运行会覆盖更新
FACTOR_BUILD_OUTPUTS = "outputs"

# factor_test 各层 Excel 输出目录（相对 factor_test 文件夹）；后续步骤读取上一步输出
FACTOR_TEST_OUTPUTS = "outputs"

# 国家队出手公告日期（因子测试 02 等在折线图上标注）
MARK_DATES = [
    "2023-10-23",
    "2024-02-06",
    "2024-09-24",
    "2025-04-07",
]


def get_base_dir():
    """解析项目根目录：优先用 config 中的 BASE_DIR，否则按 cwd 推断。"""
    if BASE_DIR is not None and os.path.isdir(BASE_DIR):
        return os.path.abspath(BASE_DIR)
    cwd = os.getcwd()
    if os.path.basename(cwd) in ("factor_build", "factor_test", "factor_display"):
        return os.path.dirname(cwd)
    return cwd


def get_data_dir():
    """解析数据目录。"""
    base = get_base_dir()
    if DATA_DIR is not None and os.path.isdir(DATA_DIR):
        return os.path.abspath(DATA_DIR)
    return os.path.join(base, "Data")
