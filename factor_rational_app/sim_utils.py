# -*- coding: utf-8 -*-
"""Shared utilities for factor simulation notebooks.

All ETF-specific parameters (NAV, AUM, shares, daily_amt) should be set
in each notebook's parameter cell, NOT here.
"""
import os, sys, datetime
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
for _p in (_THIS_DIR, _PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as project_config

DATE_COL = project_config.DATE_COL
ROLLING_W = project_config.ROLLING_ZSCORE_WINDOW
ROLLING_MIN = project_config.ROLLING_ZSCORE_MIN_VALID_IN_WINDOW
PAIR_LIST = list(project_config.RELATIVE_FACTOR_PAIRS)
MARK_DATES = [datetime.datetime.strptime(s, "%Y-%m-%d").date()
              for s in project_config.MARK_DATES]


def rolling_zscore(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    v = x.notna()
    xr = x.where(v)
    mu = xr.rolling(ROLLING_W, min_periods=ROLLING_MIN).mean()
    sd = xr.rolling(ROLLING_W, min_periods=ROLLING_MIN).std()
    return ((x - mu) / sd.where(sd > 1e-12)).where(v)


def zscore_sheet(df):
    out = df.copy()
    for c in out.columns:
        if c == DATE_COL:
            continue
        out[c] = rolling_zscore(pd.to_numeric(out[c], errors="coerce").ffill())
    return out


def diff_zscore_sheet(df):
    """First-difference (level → daily change), then rolling z-score.
    Used for level/stock variables like unit_total to improve signal sensitivity."""
    out = df.copy()
    for c in out.columns:
        if c == DATE_COL:
            continue
        s = pd.to_numeric(out[c], errors="coerce").ffill()
        out[c] = rolling_zscore(s.diff())
    return out




def relative_factor(zdf, code_a, code_b):
    return zdf[code_a] - zdf[code_b]


def load_raw():
    dd = project_config.get_data_dir()
    path = os.path.join(dd, project_config.AUGMENTED_FACTOR_FILENAME)
    sheets = pd.read_excel(path, sheet_name=None)
    out = {}
    for n, df in sheets.items():
        if n == "Target":
            continue
        if "Date" in df.columns and DATE_COL not in df.columns:
            df = df.rename(columns={"Date": DATE_COL})
        if DATE_COL in df.columns:
            df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce").dt.date
        out[n] = df
    return out


def load_y():
    dd = project_config.get_data_dir()
    fs = [f for f in os.listdir(dd)
          if any(f.endswith(e) for e in project_config.EXCEL_EXTENSIONS)
          and not f.startswith(project_config.SKIP_FILE_PREFIX)]
    f50 = next((f for f in fs if all(k in f for k in project_config.FILE_KEYWORDS_CSI50)), None)
    f1k = next((f for f in fs if all(k in f for k in project_config.FILE_KEYWORDS_CSI1000)), None)
    if not f50 or not f1k:
        return None
    pct = project_config.PCT_COL
    d50 = pd.read_excel(os.path.join(dd, f50))
    d1k = pd.read_excel(os.path.join(dd, f1k))
    for d in (d50, d1k):
        d[DATE_COL] = pd.to_datetime(d[DATE_COL], errors="coerce").dt.date
    d50 = d50[[DATE_COL, pct]].dropna().rename(columns={pct: "r50"})
    d1k = d1k[[DATE_COL, pct]].dropna().rename(columns={pct: "r1000"})
    m = d50.merge(d1k, on=DATE_COL, how="inner")
    m["y"] = pd.to_numeric(m["r50"], errors="coerce") - pd.to_numeric(m["r1000"], errors="coerce")
    return m.sort_values(DATE_COL).reset_index(drop=True)


def buy_split(total_yi, aum_a, aum_b, hold_pct_a, hold_pct_b):
    """按持仓市值比例分配买入金额。返回 (buy_a亿, buy_b亿)。"""
    hv_a, hv_b = hold_pct_a * aum_a, hold_pct_b * aum_b
    t = hv_a + hv_b
    if t <= 0:
        return total_yi / 2, total_yi / 2
    return total_yi * hv_a / t, total_yi * hv_b / t


def offset_date(all_dates, base, n):
    try:
        idx = all_dates.index(base)
    except ValueError:
        return None
    t = idx + n
    return all_dates[t] if 0 <= t < len(all_dates) else None


def inject_one(df, date, code, delta):
    out = df.copy()
    mask = out[DATE_COL] == date
    if mask.any() and code in out.columns:
        out.loc[mask, code] = pd.to_numeric(out.loc[mask, code], errors="coerce") + delta
    return out


# ── 详细计算过程 ──

def print_detail(df_orig, df_mod, z_before, z_after,
                 code_a, code_b, name_a, name_b, unit,
                 sim_date, all_dates, effect_date, half=5):
    """打印生效日前后每天的完整计算链: raw → mean → std → z → 相对因子。"""
    zoom = zoom_range(all_dates, sim_date, half)
    s_o = {c: pd.to_numeric(df_orig[c], errors="coerce").ffill() for c in [code_a, code_b]}
    s_m = {c: pd.to_numeric(df_mod[c],  errors="coerce").ffill() for c in [code_a, code_b]}
    stats = {}
    for tag, src in [("before", s_o), ("after", s_m)]:
        stats[tag] = {}
        for c in [code_a, code_b]:
            mu = src[c].rolling(ROLLING_W, min_periods=ROLLING_MIN).mean()
            sd = src[c].rolling(ROLLING_W, min_periods=ROLLING_MIN).std()
            stats[tag][c] = {"raw": src[c], "mu": mu, "sd": sd}

    for code, name in [(code_a, name_a), (code_b, name_b)]:
        print(f"\n{'='*80}")
        print(f"  {name} ({code})  —  单位: {unit}")
        print(f"{'='*80}")
        print(f"{'日期':>12} | {'raw_bef':>12} {'raw_aft':>12} | {'mean_bef':>10} {'mean_aft':>10} | {'std_bef':>10} {'std_aft':>10} | {'z_bef':>7} {'z_aft':>7} {'Δz':>7} |")
        print("-" * 115)
        for d in zoom:
            row = df_orig[df_orig[DATE_COL] == d]
            if row.empty:
                continue
            i = row.index[0]
            rb = stats["before"][code]["raw"].iloc[i]
            ra = stats["after"][code]["raw"].iloc[i]
            mb = stats["before"][code]["mu"].iloc[i]
            ma = stats["after"][code]["mu"].iloc[i]
            sb = stats["before"][code]["sd"].iloc[i]
            sa = stats["after"][code]["sd"].iloc[i]
            zb = z_before.loc[i, code]
            za = z_after.loc[i, code]
            mark = ""
            if d == sim_date:
                mark = " ★T+0"
            elif d == effect_date:
                mark = " ★生效"
            print(f"{str(d):>12} | {rb:>12,.0f} {ra:>12,.0f} | {mb:>10,.0f} {ma:>10,.0f} | {sb:>10,.0f} {sa:>10,.0f} | {zb:>7.3f} {za:>7.3f} {za-zb:>+7.3f} |{mark}")

    print(f"\n{'='*80}")
    print(f"  相对因子 = z({name_a}) − z({name_b})")
    print(f"{'='*80}")
    print(f"{'日期':>12} | {'z_A_bef':>8} {'z_B_bef':>8} {'rel_bef':>9} | {'z_A_aft':>8} {'z_B_aft':>8} {'rel_aft':>9} | {'Δrel':>8} |")
    print("-" * 90)
    for d in zoom:
        row = df_orig[df_orig[DATE_COL] == d]
        if row.empty:
            continue
        i = row.index[0]
        za_b = z_before.loc[i, code_a]
        zb_b = z_before.loc[i, code_b]
        za_a = z_after.loc[i, code_a]
        zb_a = z_after.loc[i, code_b]
        rb = za_b - zb_b
        ra = za_a - zb_a
        mark = ""
        if d == sim_date:
            mark = " ★T+0"
        elif d == effect_date:
            mark = " ★生效"
        print(f"{str(d):>12} | {za_b:>8.3f} {zb_b:>8.3f} {rb:>+9.4f} | {za_a:>8.3f} {zb_a:>8.3f} {ra:>+9.4f} | {ra-rb:>+8.4f} |{mark}")


# ── plotting ──

def setup_style():
    plt.rcParams.update({
        "font.sans-serif": ["Arial Unicode MS", "PingFang SC", "SimHei"],
        "axes.unicode_minus": False,
        "figure.dpi": 120,
    })


def zoom_range(all_dates, center, half=30):
    try:
        idx = all_dates.index(center)
    except ValueError:
        idx = len(all_dates) // 2
    lo = max(0, idx - half)
    hi = min(len(all_dates), idx + half + 1)
    return all_dates[lo:hi]


def plot_ba(ax, dates, before, after, title, ylabel, inj_date,
            t1=None, t2=None):
    ax.plot(dates, before, label="Before", color="#1f77b4", lw=2)
    ax.plot(dates, after, label="After", color="#ff7f0e", lw=2, ls="--")
    ax.axvline(inj_date, color="red", lw=1.5, label="T+0")
    if t1 and t1 in dates:
        ax.axvline(t1, color="orange", lw=1, ls="--", label="T+1")
    if t2 and t2 in dates:
        ax.axvline(t2, color="purple", lw=1, ls="--", label="T+2")
    for md in MARK_DATES:
        if md in dates:
            ax.axvline(md, color="#ccc", lw=0.5, ls=":")
    ax.set_title(title, fontsize=13)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.tick_params(axis="x", rotation=30)
    ax.grid(alpha=0.3)
