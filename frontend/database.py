import pandas as pd
import requests
from sqlalchemy import create_engine
import streamlit as st

# ── 20 ngân hàng đúng theo HTML mock-up ─────────────────────────────────────
BANK_META = {
    # CafeF — 8 mã lớn
    "VCB": {"name": "Vietcombank",          "source": "CafeF"},
    "BID": {"name": "BIDV",                  "source": "CafeF"},
    "CTG": {"name": "Vietinbank",            "source": "CafeF"},
    "MBB": {"name": "MB Bank",               "source": "CafeF"},
    "TCB": {"name": "Techcombank",           "source": "CafeF"},
    "VPB": {"name": "VPBank",                "source": "CafeF"},
    "ACB": {"name": "Asia Comm. Bank",       "source": "CafeF"},
    "STB": {"name": "Sacombank",             "source": "CafeF"},
    # TCBS — 8 mã
    "SHB": {"name": "SHB",                   "source": "TCBS"},
    "HDB": {"name": "HDBank",                "source": "TCBS"},
    "VIB": {"name": "VIB",                   "source": "TCBS"},
    "TPB": {"name": "TPBank",                "source": "TCBS"},
    "EIB": {"name": "Eximbank",              "source": "TCBS"},
    "MSB": {"name": "MSB",                   "source": "TCBS"},
    "SSB": {"name": "SeABank",               "source": "TCBS"},
    "LPB": {"name": "LienVietPostBank",      "source": "TCBS"},
    # FireAnt — 4 mã nhỏ
    "OCB": {"name": "Orient Comm. Bank",     "source": "FireAnt"},
    "NAB": {"name": "Nam A Bank",            "source": "FireAnt"},
    "KLB": {"name": "Kien Long Bank",        "source": "FireAnt"},
    "BVB": {"name": "Viet Capital Bank",     "source": "FireAnt"},
}

# Nhóm theo nguồn (dùng cho Sources page & filter)
SOURCE_GROUPS = {
    "CafeF":   [s for s, m in BANK_META.items() if m["source"] == "CafeF"],
    "TCBS":    [s for s, m in BANK_META.items() if m["source"] == "TCBS"],
    "FireAnt": [s for s, m in BANK_META.items() if m["source"] == "FireAnt"],
}

# Badge CSS class theo nguồn
SOURCE_BADGE = {
    "CafeF":   "badge-blue",
    "TCBS":    "badge-purple",
    "FireAnt": "badge-cyan",
}
def get_dynamic_bank_meta():
    """Lấy danh sách mã từ session_state để tự động cập nhật khi có mã mới"""
    if "DYNAMIC_BANK_META" not in st.session_state:
        st.session_state.DYNAMIC_BANK_META = BANK_META.copy()
    return st.session_state.DYNAMIC_BANK_META

class DatabaseManager:
    def __init__(self, mode="drill", vm_ip="100.80.217.65"):
        self.mode = mode
        self.vm_ip = vm_ip
        self.drill_url = f"http://{self.vm_ip}:8047/query.json"
        self.hdfs_path = "/user/hadoop/stock_cleaned_csv/000000_0"
        self._engine = create_engine(
            "mysql+mysqlconnector://root:123456@100.80.217.65:3306/bigdata_stock"
        )

    def connect(self) -> bool:
        try:
            r = requests.post(
                self.drill_url,
                json={"queryType": "SQL", "query": "SELECT 1"},
                headers={"Content-Type": "application/json"},
                timeout=3,
            )
            return r.status_code == 200
        except Exception as e:
            print(f"Lỗi khi ping Drill: {e}")
            return False

    def _run_drill_query(self, sql: str) -> pd.DataFrame:
        payload = {"queryType": "SQL", "query": sql}
        headers = {"Content-Type": "application/json"}
        try:
            r = requests.post(self.drill_url, json=payload, headers=headers)
            if r.status_code == 200:
                rows = r.json().get("rows", [])
                return pd.DataFrame(rows)
            print("Lỗi từ Drill:", r.text)
            return pd.DataFrame()
        except Exception as e:
            print("Kết nối Drill thất bại:", str(e))
            return pd.DataFrame()

    def get_raw_data(self, symbols=None, start_date=None, end_date=None) -> pd.DataFrame:
        sql = f"""
        SELECT
            columns[0] AS symbol,
            columns[1] AS trading_date,
            columns[2] AS scrape_time,
            columns[3] AS source,
            CAST(columns[4] AS DOUBLE) AS close,
            CAST(columns[5] AS DOUBLE) AS volume,
            CAST(columns[6] AS DOUBLE) AS open,
            CAST(columns[7] AS DOUBLE) AS high,
            CAST(columns[8] AS DOUBLE) AS low
        FROM table(dfs.`{self.hdfs_path}`
            (type => 'text', fieldDelimiter => ',', extractHeader => false))
        WHERE 1=1
        """
        if symbols:
            sym_str = ", ".join(f"'{s}'" for s in symbols)
            sql += f" AND columns[0] IN ({sym_str})"

        df = self._run_drill_query(sql)
        if not df.empty:
            df["trading_date"] = pd.to_datetime(df["trading_date"], errors="coerce")
            df = df.dropna(subset=["trading_date"]).rename(
                columns={"trading_date": "date"}
            )
            for col in ["close", "volume", "open", "high", "low"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if start_date and end_date:
                s = pd.to_datetime(start_date).date()
                e = pd.to_datetime(end_date).date()
                df = df[(df["date"].dt.date >= s) & (df["date"].dt.date <= e)]
        return df

    def get_analysis_data(self, symbols=None, start_date=None, end_date=None) -> pd.DataFrame:
        sql = "SELECT * FROM mysql_db.bigdata_stock.tbl_stock_daily_analysis WHERE 1=1"
        if symbols:
            sym_str = ", ".join(f"'{s}'" for s in symbols)
            sql += f" AND symbol IN ({sym_str})"
        df = self._run_drill_query(sql)
        if not df.empty:
            df["calc_date"] = pd.to_datetime(df["calc_date"], errors="coerce")
            df = df.dropna(subset=["calc_date"])
            for col in ["total_volume", "max_close_price", "min_close_price",
                        "max_intraday_drop", "max_intraday_volatility"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "max_close_price" in df.columns:
                df["avg_close_price"] = df["max_close_price"]
        return df
    
    def get_monthly_analysis_data(self, symbols=None) -> pd.DataFrame:
        sql = "SELECT * FROM mysql_db.bigdata_stock.tbl_stock_monthly_analysis WHERE 1=1"
        if symbols:
            sym_str = ", ".join(f"'{s}'" for s in symbols)
            sql += f" AND symbol IN ({sym_str})"
        df = self._run_drill_query(sql)
        return df

    def get_summary(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=["symbol", "price", "price_variance", "pct_change", "total_volume"]
        )
    
    