"""
pages/dashboard.py — Dashboard chính
Giao diện khớp HTML mock-up: source overview, KPI grid, line chart, recent table.
Cập nhật: Dữ liệu động, lấy toàn bộ mã ngân hàng từ session_state.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st
import pandas as pd

from database import DatabaseManager, SOURCE_GROUPS, get_dynamic_bank_meta
from utils import (
    render_topbar, render_kpi_card, section_label, info_box,
    source_overview_cards, bank_chip_row,
    build_line_chart, build_volume_chart, build_sma_chart,
    add_sma, fmt_price, fmt_volume, fmt_pct,
    SOURCE_BADGE_CLS,
)

# Dữ liệu demo (dùng dự phòng khi Drill chưa kết nối hoặc chưa cào đủ data)
_DEMO = {
    "VCB": {"price": 82400, "chg": 1.23,  "vol": 3_200_000},
    "BID": {"price": 54200, "chg": -0.18, "vol": 4_100_000},
    "CTG": {"price": 48700, "chg": 0.41,  "vol": 3_800_000},
    "MBB": {"price": 26900, "chg": 0.75,  "vol": 7_200_000},
    "ACB": {"price": 24150, "chg": 0.62,  "vol": 5_800_000},
    "STB": {"price": 33200, "chg": -0.30, "vol": 2_100_000},
    "TCB": {"price": 45800, "chg": 1.11,  "vol": 4_400_000},
    "SHB": {"price": 14800, "chg": 0.68,  "vol": 8_300_000},
    "HDB": {"price": 28600, "chg": 1.42,  "vol": 2_600_000},
    "VIB": {"price": 18650, "chg": -0.27, "vol": 1_900_000},
    "TPB": {"price": 16200, "chg": 0.93,  "vol": 3_400_000},
    "EIB": {"price": 29100, "chg": 0.34,  "vol": 1_200_000},
    "MSB": {"price": 15400, "chg": -0.65, "vol": 4_700_000},
    "SSB": {"price": 19700, "chg": 0.51,  "vol": 2_800_000},
    "LPB": {"price": 19850, "chg": 0.76,  "vol": 3_700_000},
    "VPB": {"price": 21350, "chg": -0.23, "vol": 9_100_000},
    "OCB": {"price": 15300, "chg": 1.05,  "vol": 1_300_000},
    "NAB": {"price": 12400, "chg": 0.81,  "vol":   900_000},
    "KLB": {"price": 11800, "chg": -0.42, "vol":   600_000},
    "BVB": {"price": 10900, "chg": 0.18,  "vol":   400_000},
}


def _render_recent_table(meta: dict, demo: dict) -> None:
    """Bảng phiên gần nhất hiển thị 6 mã đầu tiên của danh sách."""
    rows  = ""
    # Lấy 6 mã đầu tiên từ danh sách meta hiện tại
    recent_syms = list(meta.keys())[:6]
    
    for sym in recent_syms:
        # Nếu là mã mới chưa có trong DEMO, cho giá trị mặc định để không bị lỗi
        d   = demo.get(sym, {"price": 15000, "chg": 0.0, "vol": 1000000})
        src = meta.get(sym, {}).get("source", "CafeF")
        badge_cls = SOURCE_BADGE_CLS.get(src, "badge-blue")
        chg_cls   = "pos" if d["chg"] >= 0 else "neg"
        arrow     = "▲" if d["chg"] >= 0 else "▼"
        
        rows += f"""
        <tr>
          <td><span style="font-family:var(--font-mono);font-weight:700;
                           color:var(--accent-bright);letter-spacing:.05em">{sym}</span></td>
          <td style="font-family:var(--font-mono);font-weight:600;
                     color:var(--text-primary)">{d['price']:,}</td>
          <td style="color:var(--text-muted);font-size:.78rem">{fmt_volume(d['vol'])}</td>
          <td><span class="badge {badge_cls}" style="font-size:.60rem">{src}</span></td>
          <td class="{chg_cls}" style="font-size:.78rem;font-family:var(--font-mono)">{arrow} {abs(d['chg'])}%</td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:.82rem;">
      <thead>
        <tr style="border-bottom:1px solid var(--border-soft);">
          <th style="padding:5px 6px;text-align:left;font-size:.62rem;font-weight:700;
                     text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted)">Mã</th>
          <th style="padding:5px 6px;text-align:left;font-size:.62rem;font-weight:700;
                     text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted)">Đóng cửa</th>
          <th style="padding:5px 6px;text-align:left;font-size:.62rem;font-weight:700;
                     text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted)">KL</th>
          <th style="padding:5px 6px;text-align:left;font-size:.62rem;font-weight:700;
                     text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted)">Nguồn</th>
          <th style="padding:5px 6px;"></th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render(db: DatabaseManager) -> None:
    # Lấy danh sách meta động (có chứa mã mới thêm)
    BANK_META_DYNAMIC = get_dynamic_bank_meta()
    ALL_SYMBOLS = list(BANK_META_DYNAMIC.keys())
    
    # Đặt KPI_SYMBOLS động (lấy 4 mã đầu)
    KPI_SYMBOLS = ALL_SYMBOLS[:4] if len(ALL_SYMBOLS) >= 4 else ALL_SYMBOLS

    render_topbar(
        "Market Overview",
        f"{len(ALL_SYMBOLS)} ngân hàng Việt Nam · CafeF · TCBS · FireAnt",
        breadcrumb="Dashboard",
    )

    # ── 1. Source overview — 3 cards ───────────────
    section_label("Tổng quan nguồn dữ liệu")
    source_overview_cards(BANK_META_DYNAMIC)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 2. KPI Grid — Top 4 mã ────────────────────────────────────────
    section_label("Top 4 mã quan tâm")
    kpi_cols = st.columns(4)
    for col, sym in zip(kpi_cols, KPI_SYMBOLS):
        d   = _DEMO.get(sym, {"price": 0, "chg": 0.0, "vol": 0})
        src = BANK_META_DYNAMIC.get(sym, {}).get("source", "CafeF")
        with col:
            render_kpi_card(
                symbol  = sym,
                name    = BANK_META_DYNAMIC.get(sym, {}).get("name", sym),
                price   = d.get("price", 0),
                pct_chg = d.get("chg", 0.0),
                volume  = d.get("vol", 0),
                source  = src,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 3. Bộ lọc ────────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Bộ lọc biểu đồ</span></div>',
                unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        # Sử dụng ALL_SYMBOLS cho multiselect
        sel_syms = st.multiselect(
            "Ngân hàng", options=ALL_SYMBOLS, default=ALL_SYMBOLS[:3] if len(ALL_SYMBOLS) >= 3 else ALL_SYMBOLS,
        )
    with fc2:
        period = st.selectbox(
            "Khoảng thời gian",
            ["3 tháng", "6 tháng", "1 năm", "2 năm", "5 năm"], index=2,
        )
    with fc3:
        chart_type = st.selectbox("Loại biểu đồ", ["Line Chart", "SMA Chart"])
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 4. Load data ─────────────────────────────────────────────────────────
    days_map = {"3 tháng": 90, "6 tháng": 180, "1 năm": 365, "2 năm": 730, "5 năm": 1825}
    n_days = days_map.get(period, 365)
    end    = date.today()
    start  = end - timedelta(days=n_days)

    if not sel_syms:
        info_box("⬆ Chọn ít nhất 1 ngân hàng để hiển thị biểu đồ.")
        return

    with st.spinner("Đang tải dữ liệu..."):
        raw_df = db.get_raw_data(sel_syms, start, end)

    # ── 5. Main chart (left) + VCB summary (right) ───────────────────────────
    col_chart, col_vcb = st.columns([2, 1])

    with col_chart:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-header">'
            f'<span class="card-title">Giá đóng cửa — {len(sel_syms)} mã</span>'
            f'<div style="display:flex;gap:5px;">'
            f'<span class="badge badge-blue">{chart_type}</span>'
            f'<span class="badge badge-green">{period}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        if raw_df.empty:
            st.warning("Không có dữ liệu.")
        else:
            if chart_type == "Line Chart":
                fig = build_line_chart(raw_df, sel_syms,
                                       title=f"Giá đóng cửa — {period}", height=200)
            else:
                fig = build_sma_chart(raw_df, sel_syms[0], windows=(20, 50), height=200)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_vcb:
        vcb = _DEMO.get("VCB", {"price": 82400})
        sma20 = int(vcb.get("price", 0) * 0.985)
        sma50 = int(vcb.get("price", 0) * 0.969)
        st.markdown(f"""
        <div class="card" style="height:100%;">
          <div class="card-header">
            <span class="card-title">Tóm tắt VCB</span>
            <span class="badge badge-blue">CafeF</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Giá hiện tại</span>
            <span class="stat-value">{vcb.get('price',0):,}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">SMA 20</span>
            <span class="stat-value">{sma20:,}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">SMA 50</span>
            <span class="stat-value">{sma50:,}</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Sinh lời 1N</span>
            <span class="stat-value pos">+8.70%</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Volatility</span>
            <span class="stat-value">18.4%</span>
          </div>
          <div class="stat-row">
            <span class="stat-label">Vol cao nhất</span>
            <span class="stat-value">6.2M</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── 6. Pie chart + Recent table ───────────────────────────────────────────
    col_pie, col_recent = st.columns([1, 1])

    with col_pie:
        # Tự động đếm số lượng mã theo nguồn
        src_counts = {"CafeF": 0, "TCBS": 0, "FireAnt": 0, "vnstock": 0}
        for meta in BANK_META_DYNAMIC.values():
            src = meta.get("source", "CafeF")
            if src in src_counts:
                src_counts[src] += 1
            else:
                src_counts[src] = 1
                
        labels_pie = [k for k, v in src_counts.items() if v > 0]
        values_pie = [v for k, v in src_counts.items() if v > 0]
        
        import plotly.graph_objects as go
        fig_pie = go.Figure(go.Pie(
            labels=labels_pie,
            values=values_pie,
            marker_colors=["#3B82F6", "#8B5CF6", "#06B6D4", "#10B981"],
            hole=0.55,
            textinfo="none",
            hovertemplate="%{label}: %{value} mã (%{percent})<extra></extra>",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=30, b=0), height=140,
            showlegend=True,
            legend=dict(
                bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#7A92B8"),
                orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5,
            ),
            title=dict(text="Phân bổ theo nguồn", font=dict(size=11, color="#3D5478")),
        )
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header"><span class="card-title">Phân bổ theo nguồn</span>'
                    f'<span class="badge badge-amber">{len(ALL_SYMBOLS)} mã</span></div>', unsafe_allow_html=True)
        st.plotly_chart(fig_pie, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_recent:
        today_str = date.today().strftime("%d/%m/%Y")
        st.markdown(f"""
        <div class="card">
          <div class="card-header">
            <span class="card-title">Phiên gần nhất</span>
            <span class="badge badge-blue">{today_str}</span>
          </div>
        """, unsafe_allow_html=True)
        _render_recent_table(BANK_META_DYNAMIC, _DEMO)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 7. Quick stats ────────────────────────────────────────────────────────
    if not raw_df.empty:
        section_label("Tóm tắt nhanh")
        stat_cols = st.columns(len(sel_syms))
        for i, sym in enumerate(sel_syms):
            sub = raw_df[raw_df["symbol"] == sym] if "symbol" in raw_df.columns else pd.DataFrame()
            if sub.empty:
                d = _DEMO.get(sym, {"price": 0, "chg": 0.0})
                stat_cols[i].metric(sym, fmt_price(d.get("price", 0)),
                                    delta=f"{d.get('chg', 0):+.2f}%")
            else:
                ret = (sub["close"].iloc[-1] / sub["close"].iloc[0] - 1) * 100
                stat_cols[i].metric(sym, fmt_price(sub["close"].iloc[-1]),
                                    delta=f"{ret:+.2f}%")