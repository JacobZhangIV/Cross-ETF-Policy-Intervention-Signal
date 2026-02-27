# factor_build 各层输出

以下 Excel 由 factor_build 中各 notebook 在**每次运行**时**覆盖更新**生成。

| 文件 | 来源 | 内容 |
|------|------|------|
| `01_y_timeseries.xlsx` | 01_load_data_and_build_y | 大盘减小盘 y 时间序列（交易日期, 涨跌幅_50, 涨跌幅_1000, y） |
| `02_relative_factors_timeseries.xlsx` | 02_load_augmented_factor | 各 relative 因子时间序列，按 sheet 分 sheet 存放 |
| `03_regression_results.xlsx` | 03_relative_factor_regression_and_selection | sheet「all_results」为全部回归结果，「significant」为显著因子表 |
| `04_fusion_timeseries.xlsx` | 04_fusion_by_rules_and_corr_direction | 等权融合因子时间序列（交易日期, fusion） |
| `04_fusion_constituents.xlsx` | 04_fusion_by_rules_and_corr_direction | 筛选出的、用于构成 fusion 的 relative 因子对（sheet, 标的对, corr, sign） |

输出目录名可在 `config.FACTOR_BUILD_OUTPUTS` 中修改（默认 `outputs`）。
