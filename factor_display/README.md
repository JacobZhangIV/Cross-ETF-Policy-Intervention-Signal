# 因子展示 (Factor Display)

在浏览器或桌面界面中查看 **factor_build** 与 **factor_test** 的全部输出。

## 推荐：Web 版（默认，无 Tk 崩溃）

在**项目根目录**下执行：

```bash
python factor_display/app.py
```

或在 `factor_display` 目录下执行：

```bash
cd factor_display && python app.py
```

会启动本地 HTTP 服务（默认端口 8765），并尝试自动打开浏览器。若未自动打开，请手动访问：**http://127.0.0.1:8765/**

指定端口示例：`python factor_display/app.py 8888`

## 可选：桌面 GUI（Tk）

若本机 Tk 正常（例如在系统「终端」中运行），可使用：

```bash
python factor_display/app_tk.py
```

**说明**：在 macOS 某些环境（如 Cursor 内运行）下，系统自带的 Tcl/Tk 可能触发崩溃（如 `TkpInit` / `Tcl_Panic`）。若遇此情况，请使用上面的 Web 版。

## 依赖

- Python 3.6+
- pandas、openpyxl（读 Excel）
- 仅 **app_tk.py** 需要：tkinter、matplotlib（图表预览）

## 功能说明

| 标签页 | 内容 |
|--------|------|
| **概览** | 列出 factor_build/outputs 与 factor_test/outputs 下所有预期文件/文件夹，并显示是否存在。 |
| **因子构建** | 下拉选择并预览：01_y 时序、03 回归结果（全部/显著）、04 融合成分、04 融合时序。 |
| **因子测试** | 预览 01_y_and_implication、03 单因子回归汇总（fusion vs 大盘涨跌等）。 |
| **图表** | 左侧选 02_factor_plots 子文件夹，右侧选图片文件，主区域显示 PNG 预览。 |
| **配置** | 只读展示项目根、输出路径、MARK_DATES、部分 config 参数。 |

若某文件或目录尚未生成（未跑 pipeline），对应位置会显示「文件不存在」或「无数据」，不会报错退出。
