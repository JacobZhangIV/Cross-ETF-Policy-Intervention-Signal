"""Diagnose why sample count is 0 when loading 行情 and building y."""
import os
import sys

try:
    import pandas as pd
except ImportError:
    print("pandas not installed. Install with: pip install pandas openpyxl")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")

# Find files
all_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx") and not f.startswith("~$")]
file_50 = next((f for f in all_files if "上证50" in f and "行情" in f), None)
file_1000 = next((f for f in all_files if "上证1000" in f and "行情" in f), None)

if not file_50 or not file_1000:
    print("Files not found. file_50:", file_50, "file_1000:", file_1000)
    sys.exit(1)

path_50 = os.path.join(DATA_DIR, file_50)
path_1000 = os.path.join(DATA_DIR, file_1000)

print("=== Raw read (no normalize_dtypes) ===")
df50_raw = pd.read_excel(path_50, sheet_name=0)
df1000_raw = pd.read_excel(path_1000, sheet_name=0)

print("\n--- 上证50 ---")
print("Columns:", list(df50_raw.columns))
print("dtypes:\n", df50_raw.dtypes)
print("First 3 rows 交易日期:", df50_raw["交易日期"].head(3).tolist() if "交易日期" in df50_raw.columns else "NO COL 交易日期")
close_col = "收盘价" if "收盘价" in df50_raw.columns else None
if close_col:
    print("First 3 rows 收盘价:", df50_raw[close_col].head(3).tolist())
    print("收盘价 dtype:", df50_raw[close_col].dtype)
    print("收盘价 non-null count:", df50_raw[close_col].notna().sum())

print("\n--- 上证1000 ---")
print("Columns:", list(df1000_raw.columns))
print("First 3 rows 交易日期:", df1000_raw["交易日期"].head(3).tolist() if "交易日期" in df1000_raw.columns else "NO COL")
if "收盘价" in df1000_raw.columns:
    print("First 3 rows 收盘价:", df1000_raw["收盘价"].head(3).tolist())
    print("收盘价 non-null:", df1000_raw["收盘价"].notna().sum())

print("\n=== After to_datetime(交易日期).dt.date ===")
d50 = pd.to_datetime(df50_raw["交易日期"], errors="coerce").dt.date
d1000 = pd.to_datetime(df1000_raw["交易日期"], errors="coerce").dt.date
print("上证50 date non-null:", d50.notna().sum(), "sample:", d50.dropna().head(2).tolist())
print("上证1000 date non-null:", d1000.notna().sum(), "sample:", d1000.dropna().head(2).tolist())

print("\n=== After to_numeric(收盘价) ===")
c50 = pd.to_numeric(df50_raw["收盘价"], errors="coerce")
c1000 = pd.to_numeric(df1000_raw["收盘价"], errors="coerce")
print("上证50 收盘价 non-null:", c50.notna().sum())
print("上证1000 收盘价 non-null:", c1000.notna().sum())

print("\n=== Build date string and merge ===")
df50 = df50_raw.copy()
df50["交易日期"] = pd.to_datetime(df50["交易日期"], errors="coerce").dt.date
df50["收盘价"] = pd.to_numeric(df50["收盘价"], errors="coerce")
df50 = df50[["交易日期", "收盘价"]].dropna()
df50["_date"] = df50["交易日期"].astype(str)

df1000 = df1000_raw.copy()
df1000["交易日期"] = pd.to_datetime(df1000["交易日期"], errors="coerce").dt.date
df1000["收盘价"] = pd.to_numeric(df1000["收盘价"], errors="coerce")
df1000 = df1000[["交易日期", "收盘价"]].dropna()
df1000["_date"] = df1000["交易日期"].astype(str)

print("After dropna: df50 rows:", len(df50), "df1000 rows:", len(df1000))
print("df50 _date sample:", df50["_date"].head(2).tolist())
print("df1000 _date sample:", df1000["_date"].head(2).tolist())

merged = df50[["_date", "收盘价"]].rename(columns={"收盘价": "收盘价_50"}).merge(
    df1000[["_date", "收盘价"]].rename(columns={"收盘价": "收盘价_1000"}),
    on="_date", how="inner"
)
print("Merge on _date (string): rows =", len(merged))
if len(merged) == 0:
    print("Overlap check: df50 _date set size:", df50["_date"].nunique())
    print("df1000 _date set size:", df1000["_date"].nunique())
    inter = set(df50["_date"]) & set(df1000["_date"])
    print("Intersection size:", len(inter))
    if len(inter) == 0:
        print("Sample df50 _date:", df50["_date"].iloc[0], "type:", type(df50["_date"].iloc[0]))
        print("Sample df1000 _date:", df1000["_date"].iloc[0], "type:", type(df1000["_date"].iloc[0]))
