#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare fusion with and without 90-day pre-fusion rolling z-score."""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


DATE_COL = config.DATE_COL
WINDOW = 90
MIN_VALID = 90
VIX_COL = "中国波动率收盘价"

FB_OUT = ROOT / "factor_build" / getattr(config, "FACTOR_BUILD_OUTPUTS", "outputs")
DATA_DIR = Path(config.get_data_dir())
OUT_DIR = Path(__file__).resolve().parent / "outputs"


def rolling_zscore(series: pd.Series, window: int = WINDOW, min_valid: int = MIN_VALID) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    valid = x.notna()
    x_for_roll = x.where(valid)
    roll_mean = x_for_roll.rolling(window=window, min_periods=min_valid).mean()
    roll_std = x_for_roll.rolling(window=window, min_periods=min_valid).std()
    z = (x - roll_mean) / roll_std.where(roll_std > 1e-12)
    return z.where(valid)


def normalize_date_col(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if DATE_COL not in out.columns:
        for cand in ("交易日期", "Date", "日期", "date"):
            if cand in out.columns:
                out = out.rename(columns={cand: DATE_COL})
                break
    if DATE_COL not in out.columns:
        out = out.rename(columns={out.columns[0]: DATE_COL})
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Could not infer format")
        out[DATE_COL] = pd.to_datetime(out[DATE_COL], errors="coerce").dt.date
    return out


def load_relative_factors() -> dict[str, pd.DataFrame]:
    path = FB_OUT / "02_relative_factors_timeseries.xlsx"
    sheets = pd.read_excel(path, sheet_name=None)
    out = {}
    for name, df in sheets.items():
        out[name] = normalize_date_col(df)
    return out


def load_constituents() -> pd.DataFrame:
    path = FB_OUT / "04_fusion_constituents.xlsx"
    df = pd.read_excel(path)
    return df[["sheet", "标的对", "corr", "lag", "sign"]].copy()


def load_y_calendar() -> pd.DataFrame:
    path = FB_OUT / "01_y_timeseries.xlsx"
    df = pd.read_excel(path)
    df = normalize_date_col(df)
    return df.sort_values(DATE_COL).reset_index(drop=True)


def load_official_fusion() -> pd.DataFrame:
    path = FB_OUT / "04_fusion_timeseries.xlsx"
    df = pd.read_excel(path)
    df = normalize_date_col(df)
    return df[[DATE_COL, "fusion"]].rename(columns={"fusion": "fusion_official"})


def load_vix() -> pd.DataFrame:
    impl_path = DATA_DIR / getattr(config, "IMPLICATION_EXCEL_FILENAME", "数据_波动率与股债指数.xlsx")
    sheets = pd.read_excel(impl_path, sheet_name=None)
    vix_sheet = None
    for sname, sdf in sheets.items():
        if VIX_COL in sname:
            vix_sheet = sdf.copy()
            break
    if vix_sheet is None:
        raise KeyError(f"未找到 {VIX_COL} 对应 sheet")
    vix_sheet = normalize_date_col(vix_sheet)
    value_cols = [c for c in vix_sheet.columns if c != DATE_COL]
    if not value_cols:
        raise KeyError("VIX sheet 没有数值列")
    col = value_cols[0]
    vix_sheet = vix_sheet[[DATE_COL, col]].rename(columns={col: VIX_COL})
    vix_sheet[VIX_COL] = pd.to_numeric(vix_sheet[VIX_COL], errors="coerce")
    return vix_sheet.dropna().sort_values(DATE_COL).reset_index(drop=True)


def pick_sheet(rf_sheets: dict[str, pd.DataFrame], sheet_name: str) -> pd.DataFrame:
    if sheet_name in rf_sheets:
        return rf_sheets[sheet_name]
    if len(sheet_name) > 31 and sheet_name[:31] in rf_sheets:
        return rf_sheets[sheet_name[:31]]
    for name, df in rf_sheets.items():
        if name.strip() == sheet_name or sheet_name.startswith(name):
            return df
    raise KeyError(f"未找到 sheet: {sheet_name}")


def build_aligned_components(
    rf_sheets: dict[str, pd.DataFrame],
    constituents: pd.DataFrame,
    df_y: pd.DataFrame,
) -> pd.DataFrame:
    all_dates = df_y[DATE_COL].drop_duplicates().tolist()
    date_to_idx = {d: i for i, d in enumerate(all_dates)}
    idx_to_date = {i: d for i, d in enumerate(all_dates)}
    n_dates = len(all_dates)

    merged = None
    for row in constituents.itertuples(index=False):
        sheet_name = row.sheet
        pair_name = row._1 if hasattr(row, "_1") else getattr(row, "标的对")
        lag = int(row.lag)
        sign = float(row.sign)
        df_f = pick_sheet(rf_sheets, sheet_name)[[DATE_COL, pair_name]].copy()
        df_f["pos"] = df_f[DATE_COL].map(date_to_idx)
        df_f = df_f.dropna(subset=["pos"])
        df_f["target_pos"] = df_f["pos"].astype(int) + lag
        df_f = df_f[df_f["target_pos"].between(0, n_dates - 1)]
        df_f["target_date"] = df_f["target_pos"].map(idx_to_date)
        col_name = f"{sheet_name}__{pair_name}"
        out = df_f[["target_date"]].copy()
        out[col_name] = sign * pd.to_numeric(df_f[pair_name], errors="coerce")
        merged = out if merged is None else merged.merge(out, on="target_date", how="outer")

    if merged is None:
        raise ValueError("没有可用 constituent")

    merged = merged.rename(columns={"target_date": DATE_COL})
    return merged.sort_values(DATE_COL).reset_index(drop=True)


def build_variants(aligned: pd.DataFrame) -> pd.DataFrame:
    out = aligned.copy()
    component_cols = [c for c in out.columns if c != DATE_COL]
    z_cols = []
    for col in component_cols:
        z_col = f"{col}__z90"
        out[z_col] = rolling_zscore(out[col], WINDOW, MIN_VALID)
        z_cols.append(z_col)

    result = out[[DATE_COL]].copy()
    result["fusion_plain"] = out[component_cols].mean(axis=1)
    result["fusion_pre_z90"] = out[z_cols].mean(axis=1)
    result["fusion_post_z90"] = rolling_zscore(result["fusion_pre_z90"], WINDOW, MIN_VALID)
    return result


def compute_vix_metrics(df_series: pd.DataFrame, vix_df: pd.DataFrame) -> pd.DataFrame:
    merged = df_series.merge(vix_df, on=DATE_COL, how="inner").dropna(subset=[VIX_COL]).reset_index(drop=True)
    rows = []
    for series_name in ("fusion_plain", "fusion_pre_z90", "fusion_post_z90", "fusion_official"):
        if series_name not in merged.columns:
            continue
        for horizon in (0, 1, 3, 5, 10):
            future = merged[VIX_COL].shift(-horizon)
            sub = pd.DataFrame({"x": merged[series_name], "y": future}).dropna()
            if len(sub) < 20:
                continue
            corr, p_value = pearsonr(sub["x"], sub["y"])
            rows.append(
                {
                    "series": series_name,
                    "horizon_days": horizon,
                    "n": len(sub),
                    "corr_with_future_vix": round(float(corr), 4),
                    "p_value": float(p_value),
                    "abs_corr": round(abs(float(corr)), 4),
                }
            )
    return pd.DataFrame(rows).sort_values(["series", "horizon_days"]).reset_index(drop=True)


def compute_mark_date_stats(df_series: pd.DataFrame) -> pd.DataFrame:
    dates = df_series[DATE_COL].tolist()
    rows = []
    for mark_str in getattr(config, "MARK_DATES", []):
        mark_date = pd.to_datetime(mark_str).date()
        if mark_date in dates:
            idx = dates.index(mark_date)
        else:
            idx = int(np.searchsorted(dates, mark_date))
            idx = min(max(idx, 0), len(dates) - 1)
        lo = max(0, idx - 5)
        hi = min(len(dates), idx + 6)
        window = df_series.iloc[lo:hi].copy()
        for series_name in ("fusion_plain", "fusion_pre_z90", "fusion_post_z90", "fusion_official"):
            if series_name not in window.columns:
                continue
            exact_row = window[window[DATE_COL] == mark_date]
            exact_val = np.nan if exact_row.empty else float(exact_row.iloc[0][series_name])
            tmp = window[[DATE_COL, series_name]].dropna().copy()
            if len(tmp) == 0:
                peak_date = None
                peak_val = np.nan
            else:
                peak_idx = tmp[series_name].abs().idxmax()
                peak_date = tmp.loc[peak_idx, DATE_COL]
                peak_val = float(tmp.loc[peak_idx, series_name])
            rows.append(
                {
                    "mark_date": mark_date,
                    "series": series_name,
                    "exact_value": exact_val,
                    "window_peak_abs_date": peak_date,
                    "window_peak_value": peak_val,
                }
            )
    return pd.DataFrame(rows)


def compute_rebuild_check(df_variants: pd.DataFrame, df_official: pd.DataFrame) -> pd.DataFrame:
    merged = df_variants.merge(df_official, on=DATE_COL, how="inner").dropna()
    diff = merged["fusion_pre_z90"] - merged["fusion_official"]
    return pd.DataFrame(
        [
            {
                "metric": "n_overlap",
                "value": len(merged),
            },
            {
                "metric": "max_abs_diff_pre_z90_vs_official",
                "value": float(diff.abs().max()),
            },
            {
                "metric": "mean_abs_diff_pre_z90_vs_official",
                "value": float(diff.abs().mean()),
            },
            {
                "metric": "corr_pre_z90_vs_official",
                "value": float(merged["fusion_pre_z90"].corr(merged["fusion_official"])),
            },
        ]
    )


def plot_timeseries(df_plot: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
    series_specs = [
        ("fusion_plain", "No Pre-Z", "#6c757d"),
        ("fusion_pre_z90", "Pre-Z 90D", "#1f77b4"),
        ("fusion_post_z90", "Pre-Z 90D + Post-Z 90D", "#d62728"),
    ]
    if "fusion_official" in df_plot.columns:
        series_specs.append(("fusion_official", "Official", "#2ca02c"))

    for ax, (series_name, label, color) in zip(axes, series_specs[:3]):
        ax.plot(df_plot[DATE_COL], df_plot[series_name], color=color, linewidth=0.8, label=label)
        for mark_str in getattr(config, "MARK_DATES", []):
            d = pd.to_datetime(mark_str).date()
            ax.axvline(d, color="red", linestyle="--", linewidth=0.6, alpha=0.5)
        ax.axhline(0.0, color="black", linestyle=":", linewidth=0.5)
        ax.set_ylabel(label)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(alpha=0.25)

    if "fusion_official" in df_plot.columns:
        axes[2].plot(df_plot[DATE_COL], df_plot["fusion_pre_z90"], color="#1f77b4", linewidth=0.8, label="Pre-Z 90D")
        axes[2].plot(df_plot[DATE_COL], df_plot["fusion_official"], color="#2ca02c", linewidth=0.8, alpha=0.75, label="Official")
        axes[2].legend(loc="upper left", fontsize=9)
        axes[2].set_ylabel("Match Check")

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=30)
    plt.suptitle("Fusion Comparison Around the Same Constituents", fontsize=12)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fusion_timeseries_compare.png", dpi=160)
    plt.close()


def plot_mark_windows(df_series: pd.DataFrame) -> None:
    mark_dates = [pd.to_datetime(s).date() for s in getattr(config, "MARK_DATES", [])]
    if not mark_dates:
        return
    dates = df_series[DATE_COL].tolist()
    fig, axes = plt.subplots(len(mark_dates), 1, figsize=(12, 3.2 * len(mark_dates)), sharex=False)
    if len(mark_dates) == 1:
        axes = [axes]
    for ax, mark_date in zip(axes, mark_dates):
        if mark_date in dates:
            idx = dates.index(mark_date)
        else:
            idx = int(np.searchsorted(dates, mark_date))
            idx = min(max(idx, 0), len(dates) - 1)
        lo = max(0, idx - 20)
        hi = min(len(dates), idx + 21)
        sub = df_series.iloc[lo:hi].copy().reset_index(drop=True)
        if len(sub) == 0:
            continue
        event_idx = int(np.argmin(np.abs(np.array([(d - mark_date).days for d in sub[DATE_COL]]))))
        t = np.arange(len(sub)) - event_idx
        ax.plot(t, sub["fusion_plain"], color="#6c757d", linewidth=1.0, label="No Pre-Z")
        ax.plot(t, sub["fusion_pre_z90"], color="#1f77b4", linewidth=1.0, label="Pre-Z 90D")
        ax.plot(t, sub["fusion_post_z90"], color="#d62728", linewidth=1.0, label="Pre-Z 90D + Post-Z")
        ax.axvline(0, color="red", linestyle="--", linewidth=0.8)
        ax.axhline(0, color="black", linestyle=":", linewidth=0.5)
        ax.set_title(f"Mark Date {mark_date}")
        ax.set_xlabel("Trading-Day Offset")
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fusion_mark_date_windows.png", dpi=160)
    plt.close()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rf_sheets = load_relative_factors()
    constituents = load_constituents()
    df_y = load_y_calendar()
    df_official = load_official_fusion()
    df_vix = load_vix()

    aligned = build_aligned_components(rf_sheets, constituents, df_y)
    df_variants = build_variants(aligned)
    df_series = df_variants.merge(df_official, on=DATE_COL, how="outer").sort_values(DATE_COL).reset_index(drop=True)

    component_cols = [c for c in aligned.columns if c != DATE_COL]
    component_summary = pd.DataFrame(
        [{"component": c, "non_null_count": int(aligned[c].notna().sum())} for c in component_cols]
    ).sort_values("component")
    vix_metrics = compute_vix_metrics(df_series, df_vix)
    mark_stats = compute_mark_date_stats(df_series)
    rebuild_check = compute_rebuild_check(df_variants, df_official)

    with pd.ExcelWriter(OUT_DIR / "fusion_prefusion_z90_experiment.xlsx", engine="openpyxl") as writer:
        df_series.to_excel(writer, sheet_name="series", index=False)
        component_summary.to_excel(writer, sheet_name="components", index=False)
        vix_metrics.to_excel(writer, sheet_name="vix_metrics", index=False)
        mark_stats.to_excel(writer, sheet_name="mark_dates", index=False)
        rebuild_check.to_excel(writer, sheet_name="rebuild_check", index=False)

    plot_timeseries(df_series.dropna(subset=["fusion_plain", "fusion_pre_z90"], how="all"))
    plot_mark_windows(df_series.dropna(subset=["fusion_plain", "fusion_pre_z90"], how="all"))

    print("输出目录:", OUT_DIR)
    print("主结果:", OUT_DIR / "fusion_prefusion_z90_experiment.xlsx")
    print("\n重建校验:")
    print(rebuild_check.to_string(index=False))
    print("\nVIX 指标:")
    print(vix_metrics.to_string(index=False))


if __name__ == "__main__":
    main()
