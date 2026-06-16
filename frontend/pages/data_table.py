"""
pages/data_table.py — Xem dữ liệu thô & kết quả phân tích
Bảng: tbl_raw_stock  (tab 1)
      tbl_stock_analysis  (tab 2 — Spark result)
Tính năng: Search, Filter, Pagination, Download CSV
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database import DatabaseManager, get_dynamic_bank_meta
from utils import (
    render_topbar, section_label, info_box,
    fmt_price, fmt_volume,
)

# Lấy danh sách mã động
BANK_META_DYNAMIC = get_dynamic_bank_meta()
PRIMARY = list(BANK_META_DYNAMIC.keys())

PAGE_SIZE = 25


def _paginate(df: pd.DataFrame, page: int, size: int = PAGE_SIZE
              ) -> tuple[pd.DataFrame, int]:
    total = len(df)
    n_pages = max(1, (total + size - 1) // size)
    page    = max(1, min(page, n_pages))
    start   = (page - 1) * size
    return df.iloc[start:start+size], n_pages


def _render_raw(db: DatabaseManager) -> None:
    """Tab 1: tbl_raw_stock."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Bộ lọc</span></div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        search = st.text_input("🔍  Tìm theo mã / nguồn",
                               placeholder="VD: ACB, CafeF...")
    with c2:
        syms = st.multiselect("Mã cổ phiếu",
                              options=PRIMARY, default=PRIMARY)
    with c3:
        period = st.selectbox("Khoảng thời gian",
                              ["1 tháng","3 tháng","6 tháng","1 năm","5 năm"],
                              index=2)
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        show_all = st.checkbox("Tất cả cột", value=False)

    st.markdown("</div>", unsafe_allow_html=True)

    days_map = {"1 tháng":30,"3 tháng":90,"6 tháng":180,"1 năm":365,"5 năm":1825}
    n = days_map.get(period, 180)
    end, start = date.today(), date.today() - timedelta(days=n)

    with st.spinner("Đang tải tbl_raw_stock..."):
        df = db.get_raw_data(syms or PRIMARY, start, end)

    if df.empty:
        st.warning("Không có dữ liệu.")
        return

    if "trading_date" in df.columns:
        df = df.rename(columns={"trading_date": "date"})

    # Search
    if search.strip():
        mask = df.astype(str).apply(
            lambda col: col.str.contains(search.strip(), case=False)
        ).any(axis=1)
        df = df[mask]

    # Cột hiển thị
    display_cols = (["symbol","date","open","high","low","close","volume","source"]
                    if show_all else ["symbol","date","close","volume"])
    display_cols = [c for c in display_cols if c in df.columns]

    st.markdown(
        f'<div class="info-box">📋 <b>tbl_raw_stock</b> — '
        f'{len(df):,} dòng </div>',
        unsafe_allow_html=True,
    )

    # Pagination
    if "raw_page" not in st.session_state:
        st.session_state.raw_page = 1

    page_df, n_pages = _paginate(df.sort_values("date", ascending=False),
                                 st.session_state.raw_page)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.dataframe(
        page_df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "date":   st.column_config.DateColumn("Ngày", format="DD/MM/YYYY"),
            "close":  st.column_config.NumberColumn("Giá đóng cửa", format="%,.0f ₫"),
            "open":   st.column_config.NumberColumn("Mở cửa",       format="%,.0f ₫"),
            "high":   st.column_config.NumberColumn("Cao nhất",     format="%,.0f ₫"),
            "low":    st.column_config.NumberColumn("Thấp nhất",    format="%,.0f ₫"),
            "volume": st.column_config.NumberColumn("Khối lượng",   format="%,d"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Pagination controls
    st.markdown(f'<div class="pag-info">Trang {st.session_state.raw_page} / {n_pages} '
                f'({len(df):,} dòng)</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns([1,3,1])
    with p1:
        if st.button("◀ Trước", key="raw_prev",
                     disabled=st.session_state.raw_page <= 1):
            st.session_state.raw_page -= 1
            st.rerun()
    with p3:
        if st.button("Sau ▶", key="raw_next",
                     disabled=st.session_state.raw_page >= n_pages):
            st.session_state.raw_page += 1
            st.rerun()

    # Download
    csv = df[display_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label    = "⬇ Download CSV — tbl_raw_stock",
        data     = csv,
        file_name= f"tbl_raw_stock_{date.today()}.csv",
        mime     = "text/csv",
    )


def _render_analysis(db: DatabaseManager) -> None:
    """Tab 2: tbl_stock_analysis (kết quả Spark)."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Bộ lọc</span></div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([2, 2])
    with c1:
        syms2  = st.multiselect("Mã cổ phiếu",
                                options=PRIMARY, default=PRIMARY,
                                key="anal_sym")
    with c2:
        period2 = st.selectbox("Khoảng thời gian",
                               ["1 tháng","3 tháng","6 tháng","1 năm","5 năm"],
                               index=2, key="anal_period")

    st.markdown("</div>", unsafe_allow_html=True)

    days_map = {"1 tháng":30,"3 tháng":90,"6 tháng":180,"1 năm":365,"5 năm":1825}
    n = days_map.get(period2, 180)
    end, start = date.today(), date.today() - timedelta(days=n)

    with st.spinner("Đang tải tbl_stock_analysis..."):
        df2 = db.get_analysis_data(syms2 or PRIMARY, start, end)

    if df2.empty:
        st.warning("Không có dữ liệu.")
        return

    if "calc_date" in df2.columns:
        df2 = df2.rename(columns={"calc_date": "date"})
    
    if "date" in df2.columns:
        # Ép kiểu mặc định (sẽ bị lỗi 1970 nếu Drill trả về milliseconds)
        df2["date"] = pd.to_datetime(df2["date"], errors="coerce")
        
        # --- BẮT ĐẦU SỬA LỖI 1970 ---
        # Lọc ra các dòng bị hiểu nhầm thành năm 1970
        mask_1970 = df2["date"].dt.year == 1970
        if mask_1970.any():
            # Lấy lại giá trị số nguyên gốc và ép kiểu lại với unit="ms" (mili-giây)
            df2.loc[mask_1970, "date"] = pd.to_datetime(
                df2.loc[mask_1970, "date"].astype("int64"), 
                unit="ms"
            )
        # -----------------------------
        
        # Xóa múi giờ (nếu có)
        if df2["date"].dt.tz is not None:
            df2["date"] = df2["date"].dt.tz_localize(None)
            
        # Chuyển hẳn thành đối tượng datetime.date của Python
        df2["date"] = df2["date"].dt.date

    st.markdown(
        '<div class="info-box">📊 <b>tbl_stock_daily_analysis</b> — '
        'Kết quả Spark (total_volume, max_close_price, liquidity_status,...). '
        'Được Sqoop Export đẩy vào sau khi pipeline chạy xong.</div>',
        unsafe_allow_html=True,
    )

    # Pagination
    if "anal_page" not in st.session_state:
        st.session_state.anal_page = 1

    page_df2, n_pages2 = _paginate(df2.sort_values("date", ascending=False),
                                   st.session_state.anal_page)

    # Lấy danh sách các cột theo đúng schema MySQL
    display_cols_2 = [
        "symbol", "date", "total_volume", "max_close_price", "min_close_price", 
        "up_days_count", "down_days_count", "max_volume_date", "max_volume_value", 
        "max_intraday_volatility", "liquidity_status", "max_intraday_drop"
    ]
    # Đảm bảo chỉ hiển thị những cột thực sự có trong dataframe
    display_cols_2 = [c for c in display_cols_2 if c in page_df2.columns]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.dataframe(
        page_df2[display_cols_2],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol":                  st.column_config.TextColumn("Mã CP"),
            "date":                    st.column_config.DateColumn("Ngày tính", format="DD/MM/YYYY"),
            "total_volume":            st.column_config.NumberColumn("Tổng KL", format="%,d"),
            "max_close_price":         st.column_config.NumberColumn("Giá đóng cao nhất", format="%,.2f"),
            "min_close_price":         st.column_config.NumberColumn("Giá đóng thấp nhất", format="%,.2f"),
            "up_days_count":           st.column_config.NumberColumn("Số ngày tăng"),
            "down_days_count":         st.column_config.NumberColumn("Số ngày giảm"),
            "max_volume_date":         st.column_config.TextColumn("Ngày KL Max"),
            "max_volume_value":        st.column_config.NumberColumn("Giá trị KL Max", format="%,d"),
            "max_intraday_volatility": st.column_config.NumberColumn("Biến động ngày", format="%.2f"),
            "liquidity_status":        st.column_config.TextColumn("Thanh khoản"),
            "max_intraday_drop":       st.column_config.NumberColumn("Giảm tối đa", format="%.2f"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

def _render_monthly(db: DatabaseManager) -> None:
    """Tab 3: tbl_stock_monthly_analysis (kết quả Spark tháng)."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Bộ lọc</span></div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([2, 2])
    with c1:
        syms3  = st.multiselect("Mã cổ phiếu",
                                options=PRIMARY, default=PRIMARY,
                                key="month_sym")
    with c2:
        # Thay đổi bộ lọc từ "Khoảng thời gian" sang "Chọn năm"
        current_year = date.today().year
        year_options = ["Tất cả"] + list(range(current_year, 2015, -1))
        selected_year = st.selectbox("Chọn năm", 
                                     options=year_options, 
                                     index=0, 
                                     key="month_year")

    st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Đang tải tbl_stock_monthly_analysis..."):
        df_month = db.get_monthly_analysis_data(syms3 or PRIMARY)

    if df_month.empty:
        st.warning("Không có dữ liệu phân tích tháng hoặc bảng đang trống.")
        return

    # Ép kiểu dữ liệu để đảm bảo Năm/Tháng/Khối lượng là số nguyên, Giá là số thực
    for col in ["calc_year", "calc_month", "monthly_total_volume"]:
        if col in df_month.columns:
            df_month[col] = pd.to_numeric(df_month[col], errors="coerce").fillna(0).astype(int)
            
    if "monthly_avg_close" in df_month.columns:
        df_month["monthly_avg_close"] = pd.to_numeric(df_month["monthly_avg_close"], errors="coerce")

    # Xử lý lọc dữ liệu theo Năm đã chọn
    if selected_year != "Tất cả":
        df_month = df_month[df_month["calc_year"] == int(selected_year)]

    if df_month.empty:
        st.warning(f"Không có dữ liệu cho năm {selected_year}.")
        return

    st.markdown(
        '<div class="info-box">📊 <b>tbl_stock_monthly_analysis</b> — '
        'Dữ liệu tổng hợp định kỳ hàng tháng từ kết quả Spark.</div>', 
        unsafe_allow_html=True
    )

    # Phân trang (Pagination)
    if "month_page" not in st.session_state:
        st.session_state.month_page = 1

    # Sắp xếp ưu tiên Năm giảm dần, sau đó đến Tháng giảm dần
    df_month = df_month.sort_values(["calc_year", "calc_month"], ascending=[False, False])
    
    page_df3, n_pages3 = _paginate(df_month, st.session_state.month_page)

    # Chọn đúng các cột cần hiển thị theo bảng SQL của bạn
    display_cols = ["symbol", "calc_year", "calc_month", "monthly_avg_close", "monthly_total_volume"]
    display_cols = [c for c in display_cols if c in page_df3.columns]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.dataframe(
        page_df3[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol":               st.column_config.TextColumn("Mã CP"),
            "calc_year":            st.column_config.NumberColumn("Năm", format="%d"),
            "calc_month":           st.column_config.NumberColumn("Tháng", format="%d"),
            "monthly_avg_close":    st.column_config.NumberColumn("Giá đóng TB", format="%,.2f ₫"),
            "monthly_total_volume": st.column_config.NumberColumn("Tổng KL", format="%,d"),
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # Nút chuyển trang
    st.markdown(f'<div class="pag-info">Trang {st.session_state.month_page} / {n_pages3} '
                f'({len(df_month):,} dòng)</div>', unsafe_allow_html=True)

    pm1, _, pm3 = st.columns([1,3,1])
    with pm1:
        if st.button("◀ Trước", key="month_prev",
                     disabled=st.session_state.month_page <= 1):
            st.session_state.month_page -= 1
            st.rerun()
    with pm3:
        if st.button("Sau ▶", key="month_next",
                     disabled=st.session_state.month_page >= n_pages3):
            st.session_state.month_page += 1
            st.rerun()

    # Nút Tải CSV
    csv3 = df_month[display_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label    = "⬇ Download CSV — tbl_stock_monthly_analysis",
        data     = csv3,
        file_name= f"tbl_stock_monthly_analysis_{date.today()}.csv",
        mime     = "text/csv",
    )

def render(db: DatabaseManager) -> None:
    render_topbar(
        "Data Table",
        "Xem và xuất dữ liệu từ MySQL · tbl_raw_stock & tbl_stock_daily_analysis",
    )

    # Sửa từ 2 tab thành 3 tab
    tab1, tab2, tab3 = st.tabs([
        "📋 tbl_raw_stock  (dữ liệu thô)",
        "📊 tbl_stock_daily_analysis  (Spark ngày)",
        "📈 tbl_stock_monthly_analysis  (Spark tháng)",
    ])

    with tab1:
        _render_raw(db)

    with tab2:
        _render_analysis(db)
        
    with tab3:
        _render_monthly(db)