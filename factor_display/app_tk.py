#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子展示 · 桌面 GUI（Tk）。若在 Cursor/某些环境下 Tk 崩溃，请改用：
    python factor_display/app.py
用浏览器打开 Web 版。
"""
from __future__ import print_function

import os
import sys

_cwd = os.getcwd()
_root = os.path.dirname(_cwd) if os.path.basename(_cwd) == "factor_display" else _cwd
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import config
except ImportError:
    config = None

import tkinter as tk
from tkinter import ttk
import pandas as pd

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except Exception:
    _HAS_MPL = False


def _get_paths():
    if config is None:
        root = _root
        fb_out = os.path.join(root, "factor_build", "outputs")
        ft_out = os.path.join(root, "factor_test", "outputs")
    else:
        root = config.get_base_dir()
        fb_out = os.path.join(root, "factor_build", getattr(config, "FACTOR_BUILD_OUTPUTS", "outputs"))
        ft_out = os.path.join(root, "factor_test", getattr(config, "FACTOR_TEST_OUTPUTS", "outputs"))
    plots_base = os.path.join(ft_out, "02_factor_plots")
    return root, fb_out, ft_out, plots_base


def _safe_read_excel(path, sheet_name=0, max_rows=500):
    if not path or not os.path.isfile(path):
        return None, "文件不存在"
    try:
        if sheet_name == 0:
            df = pd.read_excel(path, nrows=max_rows)
        else:
            df = pd.read_excel(path, sheet_name=sheet_name, nrows=max_rows)
        if df is None or df.empty:
            return None, "表为空"
        return df, None
    except Exception as e:
        return None, str(e)


def _safe_listdir(path):
    if not path or not os.path.isdir(path):
        return []
    try:
        return sorted(os.listdir(path))
    except Exception:
        return []


class FactorDisplayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("因子展示 · Factor Display (Tk)")
        self.root.geometry("1100x700")
        self.root.minsize(800, 500)
        self._root, self._fb_out, self._ft_out, self._plots_base = _get_paths()
        self._build_ui()
        self._load_overview()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.f_overview = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.f_overview, text="概览")
        self._build_overview_tab()
        self.f_build = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.f_build, text="因子构建")
        self._build_factor_build_tab()
        self.f_test = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.f_test, text="因子测试")
        self._build_factor_test_tab()
        self.f_charts = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.f_charts, text="图表")
        self._build_charts_tab()
        self.f_config = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.f_config, text="配置")
        self._build_config_tab()

    def _build_overview_tab(self):
        ttk.Label(self.f_overview, text="Pipeline 输出文件一览", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Separator(self.f_overview, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 8))
        self.overview_text = tk.Text(self.f_overview, wrap=tk.WORD, height=28, font=("Consolas", 10))
        self.overview_text.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(self.f_overview, command=self.overview_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.overview_text.config(yscrollcommand=sb.set)

    def _load_overview(self):
        self.overview_text.delete("1.0", tk.END)
        lines = [
            "项目根目录: " + self._root,
            "factor_build 输出: " + self._fb_out,
            "factor_test 输出: " + self._ft_out,
            "",
            "【factor_build/outputs】",
        ]
        for name, desc in [
            ("01_y_timeseries.xlsx", "大盘减小盘 y 时序"),
            ("02_relative_factors_timeseries.xlsx", "相对因子时序（多 sheet）"),
            ("03_regression_results.xlsx", "回归结果与显著因子"),
            ("04_fusion_timeseries.xlsx", "融合因子时序"),
            ("04_fusion_constituents.xlsx", "融合成分（sheet/标的对/lag/sign）"),
        ]:
            path = os.path.join(self._fb_out, name)
            status = "✓ 存在" if os.path.isfile(path) else "✗ 缺失"
            lines.append("  {}  {}  — {}".format(status, name, desc))
        lines.extend(["", "【factor_test/outputs】"])
        for name, desc in [
            ("01_y_and_implication.xlsx", "y + 股债/波动率等指标"),
            ("02_factor_plots/", "因子折线图与 event 图"),
            ("03_regression_fusion_implication.xlsx", "fusion 单因子回归汇总"),
        ]:
            path = os.path.join(self._ft_out, name.rstrip("/"))
            if name.endswith("/"):
                status = "✓ 存在" if os.path.isdir(path) else "✗ 缺失"
            else:
                status = "✓ 存在" if os.path.isfile(path) else "✗ 缺失"
            lines.append("  {}  {}  — {}".format(status, name, desc))
        if os.path.isdir(self._plots_base):
            sub = _safe_listdir(self._plots_base)
            lines.append("  子文件夹: " + ", ".join(sub[:20]) + (" ..." if len(sub) > 20 else ""))
        self.overview_text.insert(tk.END, "\n".join(lines))

    def _build_factor_build_tab(self):
        row0 = ttk.Frame(self.f_build)
        row0.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(row0, text="选择表:").pack(side=tk.LEFT, padx=(0, 6))
        self.build_combo = ttk.Combobox(
            row0,
            values=[
                "01_y_timeseries（预览）",
                "03_regression_results（全部）",
                "03_regression_results（显著）",
                "04_fusion_constituents",
                "04_fusion_timeseries（预览）",
            ],
            state="readonly",
            width=36,
        )
        self.build_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.build_combo.current(0)
        ttk.Button(row0, text="刷新", command=self._load_build_table).pack(side=tk.LEFT)
        self.build_tree_frame = ttk.Frame(self.f_build)
        self.build_tree_frame.pack(fill=tk.BOTH, expand=True)
        self.build_tree = ttk.Treeview(self.build_tree_frame, show="headings", height=18)
        vsb = ttk.Scrollbar(self.build_tree_frame, orient=tk.VERTICAL, command=self.build_tree.yview)
        hsb = ttk.Scrollbar(self.build_tree_frame, orient=tk.HORIZONTAL, command=self.build_tree.xview)
        self.build_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.build_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._load_build_table()

    def _load_build_table(self):
        for c in self.build_tree.get_children(""):
            self.build_tree.delete(c)
        for col in self.build_tree["columns"]:
            self.build_tree.heading(col, text="")
            self.build_tree.column(col, width=0)
        self.build_tree["columns"] = []
        idx = self.build_combo.current()
        if idx == 0:
            df, err = _safe_read_excel(os.path.join(self._fb_out, "01_y_timeseries.xlsx"), max_rows=200)
        elif idx == 1:
            df, err = _safe_read_excel(os.path.join(self._fb_out, "03_regression_results.xlsx"), sheet_name=0, max_rows=300)
        elif idx == 2:
            path = os.path.join(self._fb_out, "03_regression_results.xlsx")
            try:
                sheets = pd.ExcelFile(path).sheet_names if os.path.isfile(path) else []
                sn = "significant" if "significant" in sheets else ("显著" if any("显著" in s for s in sheets) else 1)
                df, err = _safe_read_excel(path, sheet_name=sn if isinstance(sn, str) else 1, max_rows=100)
            except Exception:
                df, err = None, "无法读取"
        elif idx == 3:
            df, err = _safe_read_excel(os.path.join(self._fb_out, "04_fusion_constituents.xlsx"), max_rows=50)
        else:
            df, err = _safe_read_excel(os.path.join(self._fb_out, "04_fusion_timeseries.xlsx"), max_rows=200)
        if err or df is None:
            self.build_tree["columns"] = ["说明"]
            self.build_tree.heading("说明", text="说明")
            self.build_tree.column("说明", width=400)
            self.build_tree.insert("", tk.END, values=(err or "无数据",))
            return
        cols = list(df.columns)
        self.build_tree["columns"] = cols
        for c in cols:
            self.build_tree.heading(c, text=str(c)[:20])
            self.build_tree.column(c, width=min(120, 800 // max(len(cols), 1)))
        df = df.astype(str).replace("nan", "")
        for _, row in df.iterrows():
            self.build_tree.insert("", tk.END, values=list(row))

    def _build_factor_test_tab(self):
        row0 = ttk.Frame(self.f_test)
        row0.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(row0, text="选择表:").pack(side=tk.LEFT, padx=(0, 6))
        self.test_combo = ttk.Combobox(
            row0,
            values=["01_y_and_implication（预览）", "03_regression_fusion_implication（单因子汇总）"],
            state="readonly",
            width=42,
        )
        self.test_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.test_combo.current(0)
        ttk.Button(row0, text="刷新", command=self._load_test_table).pack(side=tk.LEFT)
        self.test_tree_frame = ttk.Frame(self.f_test)
        self.test_tree_frame.pack(fill=tk.BOTH, expand=True)
        self.test_tree = ttk.Treeview(self.test_tree_frame, show="headings", height=18)
        vsb = ttk.Scrollbar(self.test_tree_frame, orient=tk.VERTICAL, command=self.test_tree.yview)
        hsb = ttk.Scrollbar(self.test_tree_frame, orient=tk.HORIZONTAL, command=self.test_tree.xview)
        self.test_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.test_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._load_test_table()

    def _load_test_table(self):
        for c in self.test_tree.get_children(""):
            self.test_tree.delete(c)
        for col in self.test_tree["columns"]:
            self.test_tree.heading(col, text="")
            self.test_tree.column(col, width=0)
        self.test_tree["columns"] = []
        idx = self.test_combo.current()
        if idx == 0:
            df, err = _safe_read_excel(os.path.join(self._ft_out, "01_y_and_implication.xlsx"), max_rows=200)
        else:
            path = os.path.join(self._ft_out, "03_regression_fusion_implication.xlsx")
            df, err = _safe_read_excel(path, sheet_name="单因子回归汇总", max_rows=20)
            if err and os.path.isfile(path):
                df, err = _safe_read_excel(path, sheet_name=0, max_rows=20)
        if err or df is None:
            self.test_tree["columns"] = ["说明"]
            self.test_tree.heading("说明", text="说明")
            self.test_tree.column("说明", width=400)
            self.test_tree.insert("", tk.END, values=(err or "无数据",))
            return
        cols = list(df.columns)
        self.test_tree["columns"] = cols
        for c in cols:
            self.test_tree.heading(c, text=str(c)[:20])
            self.test_tree.column(c, width=min(120, 800 // max(len(cols), 1)))
        df = df.astype(str).replace("nan", "")
        for _, row in df.iterrows():
            self.test_tree.insert("", tk.END, values=list(row))

    def _build_charts_tab(self):
        paned = ttk.PanedWindow(self.f_charts, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(paned, width=220)
        paned.add(left, weight=0)
        ttk.Label(left, text="因子文件夹", font=("", 10, "bold")).pack(anchor=tk.W)
        self.chart_folders = tk.Listbox(left, height=12, font=("", 10), selectmode=tk.SINGLE)
        self.chart_folders.pack(fill=tk.BOTH, expand=True, pady=4)
        self.chart_folders.bind("<<ListboxSelect>>", self._on_folder_select)
        ttk.Label(left, text="图片", font=("", 10, "bold")).pack(anchor=tk.W, pady=(8, 0))
        self.chart_images = tk.Listbox(left, height=10, font=("", 10), selectmode=tk.SINGLE)
        self.chart_images.pack(fill=tk.BOTH, expand=True, pady=4)
        self.chart_images.bind("<<ListboxSelect>>", self._on_image_select)
        right = ttk.Frame(paned)
        paned.add(right, weight=1)
        self.chart_canvas_frame = ttk.Frame(right)
        self.chart_canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.chart_fig = None
        self.chart_canvas = None
        self._refresh_chart_folders()

    def _refresh_chart_folders(self):
        self.chart_folders.delete(0, tk.END)
        self.chart_images.delete(0, tk.END)
        if not os.path.isdir(self._plots_base):
            self.chart_folders.insert(tk.END, "(无 02_factor_plots 目录)")
            return
        for name in _safe_listdir(self._plots_base):
            path = os.path.join(self._plots_base, name)
            if os.path.isdir(path):
                self.chart_folders.insert(tk.END, name)
        if self.chart_folders.size() > 0:
            self.chart_folders.selection_set(0)
            self.chart_folders.event_generate("<<ListboxSelect>>")

    def _on_folder_select(self, evt):
        self.chart_images.delete(0, tk.END)
        sel = self.chart_folders.curselection()
        if not sel:
            return
        name = self.chart_folders.get(sel[0])
        path = os.path.join(self._plots_base, name)
        if not os.path.isdir(path):
            return
        for f in _safe_listdir(path):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                self.chart_images.insert(tk.END, f)
        if self.chart_images.size() > 0:
            self.chart_images.selection_set(0)
            self.chart_images.event_generate("<<ListboxSelect>>")
        self._clear_chart_display()

    def _on_image_select(self, evt=None):
        sel_img = self.chart_images.curselection()
        sel_fold = self.chart_folders.curselection()
        if not sel_img or not sel_fold:
            return
        img_name = self.chart_images.get(sel_img[0])
        fold_name = self.chart_folders.get(sel_fold[0])
        path = os.path.join(self._plots_base, fold_name, img_name)
        if not os.path.isfile(path):
            return
        self._show_image(path)

    def _clear_chart_display(self):
        if self.chart_canvas:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None
        if self.chart_fig and _HAS_MPL:
            plt.close(self.chart_fig)
            self.chart_fig = None

    def _show_image(self, path):
        if not _HAS_MPL:
            return
        self._clear_chart_display()
        try:
            img = plt.imread(path)
            self.chart_fig = Figure(figsize=(8, 5), dpi=100)
            ax = self.chart_fig.add_subplot(111)
            ax.imshow(img)
            ax.axis("off")
            self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, master=self.chart_canvas_frame)
            self.chart_canvas.draw()
            self.chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            for w in self.chart_canvas_frame.winfo_children():
                w.destroy()
            ttk.Label(self.chart_canvas_frame, text="无法显示图片: " + str(e), font=("", 11)).pack(expand=True)

    def _build_config_tab(self):
        self.config_text = tk.Text(self.f_config, wrap=tk.WORD, height=24, font=("Consolas", 10))
        self.config_text.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(self.f_config, command=self.config_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_text.config(yscrollcommand=sb.set)
        lines = [
            "项目根: " + self._root,
            "factor_build 输出: " + self._fb_out,
            "factor_test 输出: " + self._ft_out,
            "图表目录: " + self._plots_base,
            "",
        ]
        if config is not None:
            lines.append("MARK_DATES (国家队出手公告日):")
            for d in getattr(config, "MARK_DATES", []):
                lines.append("  " + str(d))
            lines.extend([
                "",
                "ROLLING_ZSCORE_WINDOW: " + str(getattr(config, "ROLLING_ZSCORE_WINDOW", "")),
                "FUSION_LAG_ALLOWED: " + str(getattr(config, "FUSION_LAG_ALLOWED", "")),
                "REGRESSION_MAX_PVALUE: " + str(getattr(config, "REGRESSION_MAX_PVALUE", "")),
            ])
        else:
            lines.append("(未加载 config)")
        self.config_text.insert(tk.END, "\n".join(lines))

    def run(self):
        self.root.mainloop()


def main():
    app = FactorDisplayApp()
    app.run()


if __name__ == "__main__":
    main()
