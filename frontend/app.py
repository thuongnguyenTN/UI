"""
app.py — Entry point chính
Chạy: streamlit run app.py --server.port 8501 --server.address 0.0.0.0

Đồ án môn Dữ liệu lớn — Hệ thống phân tích cổ phiếu ngân hàng Việt Nam
Stack: Hadoop · Hive · Spark · Sqoop · Apache airflow · Apache Drill · Streamlit
"""

import streamlit as st

st.set_page_config(
    page_title            = "BigData Stock Dashboard",
    page_icon             = "📊",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)

from database import DatabaseManager
from utils    import load_css

from pages.dashboard    import render as page_dashboard
from pages.sources      import render as page_sources
from pages.stock_detail import render as page_stock_detail
from pages.analytics    import render as page_analytics
from pages.data_table   import render as page_data_table
from pages.crud         import render as page_crud

load_css("style.css")

# Ẩn Streamlit multipage nav mặc định
st.markdown("""
<style>
  [data-testid="stSidebarNav"],
  section[data-testid="stSidebarNav"],
  div[data-testid="stSidebarNavItems"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_db() -> DatabaseManager:
    return DatabaseManager()


db        = get_db()
connected = db.connect()

# ── Nav config — khớp với sidebar HTML mock-up ────────────────────────────────
NAV_ITEMS = [
    ("🏠",  "Dashboard",     "Tổng quan thị trường"),
    ("🗄",  "Nguồn dữ liệu", "CafeF · TCBS · FireAnt"),
    ("📈",  "Stock Detail",  "Phân tích kỹ thuật"),
    ("📊",  "Analytics",     "Phân tích chuyên sâu"),
    ("📋",  "Data Table",    "Dữ liệu & Xuất CSV"),
    ("✏️", "Quản lý mã",           "Quản lý mã ngân hàng"),
]
PAGE_KEYS = [label for _, label, _ in NAV_ITEMS]

ROUTE_MAP = {
    "Dashboard":     page_dashboard,
    "Nguồn dữ liệu": page_sources,
    "Stock Detail":  page_stock_detail,
    "Analytics":     page_analytics,
    "Data Table":    page_data_table,
    "Quản lý mã":          page_crud,
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    conn_chip_cls = "sb-chip-green" if connected else "sb-chip-amber"
    conn_text     = "Connected"    if connected else "Offline"

    # Logo + brand + tech-stack chips — khớp HTML mock-up
    st.markdown(f"""
    <div class="sb-brand">
      <div class="sb-brand-row">
        <div class="sb-icon">📊</div>
        <div>
          <div class="sb-title">BigData Stock</div>
          <div class="sb-subtitle">Banking Analytics</div>
        </div>
      </div>
      <div class="sb-meta-row" style="margin-top:8px;">
        <span class="sb-chip sb-chip-blue">Hadoop</span>
        <span class="sb-chip sb-chip-blue">Spark</span>
        <span class="sb-chip sb-chip-green">20 Mã</span>
        <span class="sb-chip sb-chip-amber">Apache airflow</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Section labels + nav radio
    st.markdown('<div class="sb-section">Chính</div>', unsafe_allow_html=True)

    page = st.radio(
        "nav",
        PAGE_KEYS,
        format_func=lambda k: next(
            f"{icon}  {label}" for icon, label, _ in NAV_ITEMS if label == k
        ),
        label_visibility="collapsed",
    )

    st.markdown("<div style='min-height:60px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sb-section">Hệ thống</div>', unsafe_allow_html=True)

    # Footer — khớp HTML mock-up: DB Mode / Kết nối / Ngân hàng / Nguồn
    dot_cls    = "dot-green" if connected else "dot-red"
    status_txt = "Online" if connected else "Offline"
    mode_label = {"dummy": "Demo Mode", "mysql": "MySQL · VM", "drill": "Apache Drill"}.get(db.mode, db.mode)

    st.markdown(f"""
    <div style="padding:0 10px;">
      <div class="sb-footer">
        <div class="sb-footer-row">
          <span>DB Mode</span>
          <span class="sb-footer-val">{mode_label}</span>
        </div>
        <div class="sb-footer-row">
          <span>Kết nối</span>
          <span class="sb-footer-val">
            <span class="dot {dot_cls} dot-pulse" style="margin-right:4px;"></span>{status_txt}
          </span>
        </div>
        <div class="sb-divider"></div>
        <div class="sb-footer-row">
          <span>Ngân hàng</span>
          <span class="sb-footer-val">20 mã</span>
        </div>
        <div class="sb-footer-row">
          <span>Nguồn</span>
          <span class="sb-footer-val">3 nguồn</span>
        </div>
        <div class="sb-footer-row">
          <span>Pipeline</span>
          <span class="sb-footer-val">Apache airflow</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Route ─────────────────────────────────────────────────────────────────────
handler = ROUTE_MAP.get(page, page_dashboard)
handler(db)