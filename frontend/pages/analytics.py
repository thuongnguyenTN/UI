"""
pages/analytics.py — Phân tích chuyên sâu
Kết quả MapReduce từ tbl_stock_analysis: SMA · Risk vs Return
Cập nhật: Tự động lấy danh sách mã động từ session_state
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Lấy thêm hàm get_dynamic_bank_meta để danh sách cập nhật theo CRUD
from database import DatabaseManager, SOURCE_GROUPS, get_dynamic_bank_meta
from utils import (
    render_topbar, section_label, info_box,
    build_analysis_bar, build_sma_chart,
    compute_stats,
    fmt_price, fmt_volume, fmt_pct, stat_row_html,
    SOURCE_COLOR, SOURCE_BADGE_CLS,
    _PLOTLY,
)

# Lấy danh sách mã động
BANK_META_DYNAMIC = get_dynamic_bank_meta()
ALL_SYMBOLS = list(BANK_META_DYNAMIC.keys())

# 4 KPI tổng quan Analytics — khớp HTML mock-up
_ANALYTICS_KPI = [
    ("Tổng mã phân tích", str(len(ALL_SYMBOLS)), "var(--text-primary)"),
    ("Tổng bản ghi",      "4,800",               "var(--green-light)"),
    ("Avg Vol/mã",        "3.2M",                "var(--text-primary)"),
    ("Pipeline Runs",     "48",                  "var(--amber)"),
]


def render(db: DatabaseManager) -> None:
    # Lấy lại meta động mỗi lần render trang để đảm bảo dữ liệu mới nhất
    BANK_META_DYNAMIC = get_dynamic_bank_meta()
    ALL_SYMBOLS = list(BANK_META_DYNAMIC.keys())
    
    # Cập nhật số lượng mã vào KPI
    _ANALYTICS_KPI[0] = ("Tổng mã phân tích", str(len(ALL_SYMBOLS)), "var(--text-primary)")

    render_topbar(
        "Analytics",
        "Spark · tbl_stock_analysis · SMA",
        breadcrumb="Analytics",
    )

    # ── Info box pipeline ─────────────────────────────────────────────────────
    info_box(
        ""
    )

    # ── 4 KPI tổng quan — khớp HTML mock-up ──────────────────────────────────
    kpi_cols = st.columns(4)
    for col, (label, value, color) in zip(kpi_cols, _ANALYTICS_KPI):
        with col:
            st.markdown(f"""
            <div style="background:var(--bg-card);border:1px solid var(--border);
                        border-radius:var(--radius-md);padding:10px 11px;">
              <div style="font-size:.62rem;color:var(--text-muted);text-transform:uppercase;
                          letter-spacing:.08em;margin-bottom:3px;font-family:var(--font);">{label}</div>
              <div style="font-size:1.35rem;font-weight:700;color:{color};
                          font-family:var(--font-mono);letter-spacing:-0.02em;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Selector ──────────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Cấu hình phân tích</span></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([2, 2])
    with c1:
        # Cập nhật Dropdown lấy từ BANK_META_DYNAMIC
        symbol = st.selectbox(
            "Mã cổ phiếu",
            ALL_SYMBOLS,
            format_func=lambda s: f"{s} — {BANK_META_DYNAMIC.get(s,{}).get('name',s)} [{BANK_META_DYNAMIC.get(s,{}).get('source','')}]",
        )
    with c2:
        period = st.selectbox(
            "Khoảng thời gian",
            ["6 tháng", "1 năm", "2 năm", "5 năm"], index=1,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    days_map = {"6 tháng": 180, "1 năm": 365, "2 năm": 730, "5 năm": 1825}
    n_days   = days_map.get(period, 365)
    end      = date.today()
    start    = end - timedelta(days=n_days)

    with st.spinner("Đang tính toán..."):
        raw_df  = db.get_raw_data([symbol], start, end)
        anal_df = db.get_analysis_data([symbol], start, end)

    if raw_df.empty:
        st.warning("Không có dữ liệu.")
        return

    stats = compute_stats(raw_df, symbol)

    # ── 6 KPI chi tiết ────────────────────────────────────────────────────────
    section_label("Chỉ số tổng hợp")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("SMA 20",  fmt_price(stats.get("sma20", 0)) if stats.get("sma20") else "—")
    k2.metric("SMA 50",  fmt_price(stats.get("sma50", 0)) if stats.get("sma50") else "—")
    k3.metric("Ngày biến động", stats.get("max_var_date", "—"))
    k4.metric("KL lớn nhất", fmt_volume(stats.get("max_volume", 0)),
              delta=f"ngày {stats.get('max_vol_date','—')}")
    k5.metric("Giá cao nhất", fmt_price(stats.get("max_close", 0)))
    k6.metric("Giá thấp nhất", fmt_price(stats.get("min_close", 0)))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Stat card + SMA chart ─────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 2])
    ret_val = stats.get("return_pct", 0)

    with col_l:
        st.markdown(f"""
        <div class="card">
          <div class="card-header">
            <span class="card-title">Thống kê {symbol}</span>
            <span class="badge badge-blue">{period}</span>
          </div>
          {stat_row_html("Giá hiện tại",     fmt_price(stats.get("price", 0)))}
          {stat_row_html("SMA 20",            fmt_price(stats.get("sma20", 0)) if stats.get("sma20") else "—")}
          {stat_row_html("SMA 50",            fmt_price(stats.get("sma50", 0)) if stats.get("sma50") else "—")}
          {stat_row_html("Sinh lời",          fmt_pct(ret_val), cls="pos" if ret_val >= 0 else "neg")}
          {stat_row_html("Volatility (ann.)", f"{stats.get('volatility',0):.2f}%")}
          {stat_row_html("Giá cao nhất",      fmt_price(stats.get("max_close", 0)))}
          {stat_row_html("Giá thấp nhất",     fmt_price(stats.get("min_close", 0)))}
          {stat_row_html("KL lớn nhất",       fmt_volume(stats.get("max_volume", 0)))}
          {stat_row_html("Ngày KL lớn nhất",  stats.get("max_vol_date", "—"))}
          {stat_row_html("Ngày biến động",     stats.get("max_var_date", "—"))}
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-header"><span class="card-title">SMA 20 & SMA 50</span>'
            '<span class="badge badge-green">Moving Average</span></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            build_sma_chart(raw_df, symbol, windows=(20, 50), height=280),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── MapReduce avg_close_price bar ─────────────────────────────────────────
    if not anal_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-header"><span class="card-title">avg_close_price — Kết quả Spark</span>'
            '<span class="badge badge-amber">tbl_stock_analysis</span></div>',
            unsafe_allow_html=True,
        )
        info_box(
            ""
            
        )
        st.plotly_chart(
            build_analysis_bar(anal_df, symbol, height=240),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Top 10 avg_close_price bar + Source pie ───────────────────────────────
    section_label("avg_close_price — Top 10 mã")

    _demo_prices = {
        "VCB": 82400, "BID": 54200, "CTG": 48700, "TCB": 45800,
        "EIB": 29100, "HDB": 28600, "MBB": 26900, "ACB": 24150,
        "VPB": 21350, "SSB": 19700,
    }
    top10_syms   = sorted(_demo_prices, key=_demo_prices.get, reverse=True)[:10]
    top10_prices = [_demo_prices[s] for s in top10_syms]
    # Lấy màu theo BANK_META_DYNAMIC
    top10_colors = [SOURCE_COLOR.get(BANK_META_DYNAMIC.get(s, {}).get("source", "CafeF"), "#3B82F6")
                    for s in top10_syms]

    fig_anal = go.Figure(go.Bar(
        x=top10_syms, y=top10_prices,
        marker_color=top10_colors, opacity=0.78,
        hovertemplate="%{x}<br>avg: %{y:,.0f}₫<extra></extra>",
    ))
    fig_anal.update_layout(
        **_PLOTLY, height=200,
        title=dict(text="avg_close_price Top 10 (Spark output)",
                   font=dict(size=13, color="#3D5478")),
    )
    fig_anal.update_xaxes(tickfont=dict(size=10, color="#3D5478"))
    fig_anal.update_yaxes(tickfont=dict(size=10, color="#3D5478"), tickformat=",.0f")

    # Đếm số lượng mã theo nguồn hiện tại
    src_counts = {"CafeF": 0, "TCBS": 0, "FireAnt": 0, "vnstock": 0}
    for meta in BANK_META_DYNAMIC.values():
        src = meta.get("source", "CafeF")
        if src in src_counts:
            src_counts[src] += 1
        else:
            src_counts[src] = 1

    fig_src = go.Figure(go.Pie(
        labels=list(src_counts.keys()), 
        values=list(src_counts.values()),
        marker_colors=["#3B82F6", "#8B5CF6", "#06B6D4", "#10B981"],
        hole=0.6, textinfo="none",
        hovertemplate="%{label}: %{value} mã<extra></extra>",
    ))
    fig_src.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=160, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
    )

    col_bar, col_src_card = st.columns([2, 1])
    with col_bar:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><span class="card-title">avg_close_price — Top 10</span>'
                    '<span class="badge badge-amber">Spark</span></div>', unsafe_allow_html=True)
        st.plotly_chart(fig_anal, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_src_card:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><span class="card-title">Phân bổ nguồn</span>'
                    '<span class="badge badge-blue">Tổng hợp</span></div>', unsafe_allow_html=True)
        st.plotly_chart(fig_src, use_container_width=True, config={"displayModeBar": False})
        
        total_syms = len(ALL_SYMBOLS) if len(ALL_SYMBOLS) > 0 else 1
        for src, count in src_counts.items():
            if count > 0:
                pct = (count / total_syms) * 100
                st.markdown(stat_row_html(src, f"{count} mã ({pct:.0f}%)"), unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    