"""
pages/stock_detail.py — Phân tích chi tiết 1 mã
Biểu đồ: Candlestick / Line / VWAP · Volume · SMA · MA · Intraday
Dữ liệu: tbl_raw_stock — 20 mã theo 3 nguồn
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import DatabaseManager, SOURCE_GROUPS, get_dynamic_bank_meta
from utils import (
    render_topbar, section_label, info_box,
    build_volume_chart, build_sma_chart,
    fmt_price, fmt_volume, fmt_pct, add_sma,
    _PLOTLY,
)

# ── NEW: import 4 chart builders mới ─────────────────────────────────────────
# Paste nội dung new_chart_builders.py vào utils.py rồi import tại đây:
from utils import (
    build_intraday_price_volume,
    build_daily_moving_average,
    build_monthly_boxplot,
    # build_yearly_stacked_volume dùng ở analytics.py
)


def _candlestick(df: pd.DataFrame, symbol: str, height: int = 420) -> go.Figure:
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy()
    if "date" not in sub.columns and "trading_date" in sub.columns:
        sub = sub.rename(columns={"trading_date": "date"})
    sub = sub.sort_values("date")

    fig = go.Figure(go.Candlestick(
        x=sub["date"],
        open=sub["open"], high=sub["high"], low=sub["low"], close=sub["close"],
        increasing_line_color="#10B981", decreasing_line_color="#EF4444",
        increasing_fillcolor="#10B981",  decreasing_fillcolor="#EF4444",
        hovertext=pd.to_datetime(sub["date"]).dt.strftime("%d/%m/%Y"),
    ))
    fig.update_layout(
        **_PLOTLY, height=height,
        title=dict(text=f"{symbol} — Candlestick", font=dict(size=13, color="#3D5478")),
    )
    fig.layout.xaxis.rangeslider.visible = False
    fig.layout.xaxis.tickfont = dict(size=10, color="#3D5478")
    fig.layout.yaxis.tickfont = dict(size=10, color="#3D5478")
    return fig


def _mini_stat_card(label: str, value: str, delta: str = "", delta_cls: str = "") -> str:
    delta_html = ""
    if delta:
        delta_html = (
            f'<div class="{delta_cls}" style="font-size:.78rem;margin-top:2px;'
            f'font-family:var(--font-mono);font-weight:700;">{delta}</div>'
        )
    return (
        f'<div style="background:var(--bg-card);border:1px solid var(--border);'
        f'border-radius:var(--radius-md);padding:9px 10px;">'
        f'<div style="font-size:.62rem;color:var(--text-muted);text-transform:uppercase;'
        f'letter-spacing:.08em;margin-bottom:3px;font-family:var(--font);">{label}</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);'
        f'font-family:var(--font-mono);letter-spacing:-0.02em;">{value}</div>'
        f'{delta_html}</div>'
    )


def render(db: DatabaseManager) -> None:
    render_topbar(
        "Stock Detail",
        "Phân tích chi tiết từng mã — Candlestick · VWAP · SMA · MA · Intraday",
        breadcrumb="Stock Detail",
    )

    # ── Selector card ─────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><span class="card-title">Chọn cổ phiếu</span></div>',
                unsafe_allow_html=True)

    BANK_META_DYNAMIC = get_dynamic_bank_meta()
    all_options = list(BANK_META_DYNAMIC.keys())
    option_labels = {
        sym: f"{sym} — {BANK_META_DYNAMIC[sym].get('name', '')} [{BANK_META_DYNAMIC[sym].get('source', '')}]"
        for sym in all_options
    }

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        symbol = st.selectbox(
            "Mã cổ phiếu (20 mã)",
            options=all_options,
            format_func=lambda s: option_labels.get(s, s),
        )
    with c2:
        period = st.selectbox(
            "Khoảng thời gian",
            ["1 tháng", "3 tháng", "6 tháng", "1 năm", "2 năm", "5 năm"],
            index=3,
        )
    with c3:
        chart_mode = st.selectbox(
            "Loại biểu đồ",
            ["Candlestick", "Line Chart", "VWAP"],
        )
    with c4:
        sma_windows = st.multiselect(
            "SMA", options=[20, 50, 200], default=[20, 50],
        )
    st.markdown("</div>", unsafe_allow_html=True)

    sym_source = BANK_META_DYNAMIC.get(symbol, {}).get("source", "CafeF")
    from utils import SOURCE_BADGE_CLS
    src_badge_cls = SOURCE_BADGE_CLS.get(sym_source, "badge-blue")

    days_map = {
        "1 tháng": 30, "3 tháng": 90, "6 tháng": 180,
        "1 năm": 365, "2 năm": 730, "5 năm": 1825,
    }
    n_days = days_map.get(period, 365)
    end    = date.today()
    start  = end - timedelta(days=n_days)

    with st.spinner(f"Đang tải dữ liệu {symbol}..."):
        df = db.get_raw_data([symbol], start, end)

    if df.empty:
        info_box(f"⚠ Không có dữ liệu cho mã <b>{symbol}</b> trong khoảng thời gian đã chọn.")
        return

    if "trading_date" in df.columns:
        df = df.rename(columns={"trading_date": "date"})

    last    = df.iloc[-1]
    first   = df.iloc[0]
    ret     = (last["close"] / first["close"] - 1) * 100
    vol_ann = df["close"].pct_change().std() * np.sqrt(252) * 100

    # ── 5 metric mini cards ───────────────────────────────────────────────────
    section_label("Chỉ số chính")
    arrow_ret = "▲" if ret >= 0 else "▼"
    cls_ret   = "pos" if ret >= 0 else "neg"
    cards_html = "".join([
        _mini_stat_card("Giá hiện tại", fmt_price(last["close"]),
                        f"{arrow_ret} {fmt_pct(ret)}", cls_ret),
        _mini_stat_card("Cao nhất",     fmt_price(df["close"].max())),
        _mini_stat_card("Thấp nhất",    fmt_price(df["close"].min())),
        _mini_stat_card("Vol cao nhất",
                        fmt_volume(df["volume"].max()) if "volume" in df.columns else "N/A"),
        _mini_stat_card("Volatility",   f"{vol_ann:.2f}%"),
    ])
    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:12px;">'
        f'{cards_html}</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # TABS CHÍNH — thêm 2 tab mới: Intraday và MA
    # ══════════════════════════════════════════════════════════════════════════
    tab_main, tab_intraday, tab_ma, tab_monthly = st.tabs([
        "📈 Biểu đồ chính",
        "⏱ Intraday",
        "〰 Moving Average",
        "📦 Phân phối tháng",
    ])

    # ── TAB 1: Main chart (Candlestick / Line / VWAP) ─────────────────────────
    with tab_main:
        sym_name = BANK_META_DYNAMIC.get(symbol, {}).get("name", "")
        st.markdown(f"""
        <div class="card">
          <div class="card-header">
            <span class="card-title">{symbol} — {sym_name} | {chart_mode}</span>
            <div style="display:flex;gap:5px;">
              <span class="badge badge-blue">{period}</span>
              <span class="badge {src_badge_cls}">{sym_source}</span>
            </div>
          </div>
        """, unsafe_allow_html=True)

        if chart_mode == "Candlestick":
            fig_main = _candlestick(df, symbol, height=380)

        elif chart_mode == "Line Chart":
            from utils import build_line_chart
            fig_main = build_line_chart(df, [symbol], height=380)

        else:  # VWAP
            dv = df.sort_values("date").copy()
            dv["vwap"] = (dv["volume"] * dv["close"]).cumsum() / dv["volume"].cumsum()
            fig_main = go.Figure()
            fig_main.add_trace(go.Scatter(
                x=dv["date"], y=dv["close"], name="Giá đóng cửa", mode="lines",
                line=dict(color="#3B82F6", width=1.5),
                hovertemplate="Giá: %{y:,.0f}₫<extra></extra>",
            ))
            fig_main.add_trace(go.Scatter(
                x=dv["date"], y=dv["vwap"], name="VWAP", mode="lines",
                line=dict(color="#EF4444", width=2.2, dash="dot"),
                hovertemplate="VWAP: %{y:,.0f}₫<extra></extra>",
            ))
            fig_main.update_layout(
                **_PLOTLY, height=380,
                title=dict(text=f"{symbol} — VWAP & Close Price",
                           font=dict(size=13, color="#3D5478")),
            )
            fig_main.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
            fig_main.update_yaxes(tickfont=dict(size=10, color="#3D5478"))

        st.plotly_chart(fig_main, use_container_width=True,
                        config={"displayModeBar": True, "scrollZoom": True})
        st.markdown("</div>", unsafe_allow_html=True)

        # Volume + SMA
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header"><span class="card-title">Khối lượng</span>'
                        '<span class="badge badge-amber">Volume</span></div>', unsafe_allow_html=True)
            st.plotly_chart(build_volume_chart(df, symbol, height=200),
                            use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header"><span class="card-title">SMA 20 & 50</span>'
                        '<span class="badge badge-green">Moving Avg</span></div>', unsafe_allow_html=True)
            if sma_windows:
                st.plotly_chart(
                    build_sma_chart(df, symbol, windows=tuple(sma_windows), height=200),
                    use_container_width=True, config={"displayModeBar": False},
                )
            else:
                info_box("Chọn ít nhất 1 SMA để hiển thị.")
            st.markdown("</div>", unsafe_allow_html=True)

        # Bảng 20 phiên gần nhất
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><span class="card-title">Dữ liệu gần nhất (20 phiên)</span></div>',
                    unsafe_allow_html=True)
        preview = df.tail(20).sort_values("date", ascending=False).copy()
        if "date" in preview.columns:
            preview["date"] = pd.to_datetime(preview["date"]).dt.strftime("%d/%m/%Y")
        preview["close"] = preview["close"].map(lambda x: f"{x:,.0f}")
        if "volume" in preview.columns:
            preview["volume"] = preview["volume"].map(fmt_volume)
        cols_show = (["date", "open", "high", "low", "close", "volume"]
                     if all(c in preview.columns for c in ["open", "high", "low"])
                     else ["date", "close", "volume"])
        st.dataframe(preview[cols_show], use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── TAB 2: Intraday Price + Volume (MỚI) ──────────────────────────────────
    with tab_intraday:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-header">'
            '<span class="card-title">Giá & Khối lượng trong ngày</span>'
            '<span class="badge badge-cyan">Intraday</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        info_box(
            "📌 Biểu đồ dual-axis: <b>đường giá đóng cửa</b> (trục trái, xanh) "
            "và <b>cột khối lượng</b> (trục phải, xám). "
            "Dữ liệu lấy từ <code>scrape_time</code> trong <code>tbl_raw_stock</code>."
        )

        # Chọn ngày intraday
        has_scrape = "scrape_time" in df.columns

        if not has_scrape:
            st.warning("⚠ Cột scrape_time chưa có trong dữ liệu. "
                       "Hiển thị intraday theo ngày giao dịch gần nhất.")

        # Lấy danh sách ngày có dữ liệu
        date_col_intra = "scrape_time" if has_scrape else "date"
        available_dates = sorted(
            df["date"].dt.date.unique() if "date" in df.columns else [],
            reverse=True,
        )[:30]  # 30 ngày gần nhất

        col_i1, col_i2 = st.columns([2, 1])
        with col_i1:
            intraday_date = st.selectbox(
                "Chọn ngày giao dịch",
                options=available_dates,
                format_func=lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d),
                key="intraday_date_sel",
            )
        with col_i2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f'<span class="badge badge-blue" style="font-size:.75rem;">'
                f'{symbol} · {intraday_date}</span>',
                unsafe_allow_html=True,
            )

        target_date_str = str(intraday_date)

        fig_intra = build_intraday_price_volume(df, symbol, target_date_str, height=360)

        if fig_intra.data:
            st.plotly_chart(fig_intra, use_container_width=True,
                            config={"displayModeBar": True, "scrollZoom": True})
        else:
            st.warning(f"Không có dữ liệu intraday cho ngày {intraday_date}. "
                       "Thử chọn ngày khác hoặc mở rộng khoảng thời gian.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Mini table intraday
        if not df.empty and "date" in df.columns:
            day_df = df[df["date"].dt.date == intraday_date].sort_values(
                "scrape_time" if has_scrape else "date"
            )
            if not day_df.empty:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="card-header">'
                    f'<span class="card-title">Chi tiết tick ngày {intraday_date}</span>'
                    f'<span class="badge badge-amber">{len(day_df)} bản ghi</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                show_cols = [c for c in ["scrape_time", "open", "high", "low", "close", "volume"]
                             if c in day_df.columns]
                st.dataframe(
                    day_df[show_cols].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "close":  st.column_config.NumberColumn("Giá đóng cửa", format="%,.0f ₫"),
                        "open":   st.column_config.NumberColumn("Mở cửa",       format="%,.0f ₫"),
                        "high":   st.column_config.NumberColumn("Cao nhất",      format="%,.0f ₫"),
                        "low":    st.column_config.NumberColumn("Thấp nhất",     format="%,.0f ₫"),
                        "volume": st.column_config.NumberColumn("Khối lượng",    format="%,d"),
                    },
                )
                st.markdown("</div>", unsafe_allow_html=True)

    # ── TAB 3: Moving Average MA10 / MA20 (MỚI) ───────────────────────────────
    with tab_ma:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-header">'
            '<span class="card-title">Đường trung bình động (MA)</span>'
            '<span class="badge badge-green">Moving Average</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        info_box(
            "📌 MA ngắn hạn (xanh) & MA dài hạn (cam). "
            "Vạch đứt <b style='color:#10B981'>xanh ↑</b> = Golden Cross, "
            "<b style='color:#EF4444'>đỏ ↓</b> = Death Cross."
        )

        ma_c1, ma_c2 = st.columns([1, 1])
        with ma_c1:
            ma1_val = st.number_input("MA ngắn hạn (ngày)", min_value=3,
                                      max_value=50, value=10, step=1, key="ma1_input")
        with ma_c2:
            ma2_val = st.number_input("MA dài hạn (ngày)", min_value=5,
                                      max_value=200, value=20, step=5, key="ma2_input")

        if ma1_val >= ma2_val:
            st.error("MA ngắn hạn phải nhỏ hơn MA dài hạn.")
        else:
            fig_ma = build_daily_moving_average(df, symbol,
                                                ma1=int(ma1_val),
                                                ma2=int(ma2_val),
                                                height=380)
            if fig_ma.data:
                st.plotly_chart(fig_ma, use_container_width=True,
                                config={"displayModeBar": True, "scrollZoom": True})
            else:
                st.warning("Không đủ dữ liệu để vẽ MA. Thử mở rộng khoảng thời gian.")

        st.markdown("</div>", unsafe_allow_html=True)

        # MA stat summary
        if df["close"].notna().sum() >= int(ma2_val):
            sub_ma = df.sort_values("date").copy()
            sub_ma[f"MA{ma1_val}"] = sub_ma["close"].rolling(int(ma1_val)).mean()
            sub_ma[f"MA{ma2_val}"] = sub_ma["close"].rolling(int(ma2_val)).mean()
            last_row = sub_ma.dropna().iloc[-1]

            cross_val = last_row[f"MA{ma1_val}"] - last_row[f"MA{ma2_val}"]
            signal = "🟢 Bullish (MA ngắn > MA dài)" if cross_val > 0 else "🔴 Bearish (MA ngắn < MA dài)"

            st.markdown(f"""
            <div class="card">
              <div class="card-header">
                <span class="card-title">Tín hiệu hiện tại</span>
                <span class="badge {'badge-green' if cross_val > 0 else 'badge-red'}">
                  {'BULLISH' if cross_val > 0 else 'BEARISH'}
                </span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Giá hiện tại</span>
                <span class="stat-value">{fmt_price(last_row['close'])}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">MA {ma1_val} ngày</span>
                <span class="stat-value">{fmt_price(last_row[f'MA{ma1_val}'])}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">MA {ma2_val} ngày</span>
                <span class="stat-value">{fmt_price(last_row[f'MA{ma2_val}'])}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Chênh lệch</span>
                <span class="stat-value {'pos' if cross_val > 0 else 'neg'}">{fmt_price(abs(cross_val))}</span>
              </div>
              <div style="margin-top:10px;font-size:.80rem;color:var(--text-secondary);
                          font-family:var(--font-body);">{signal}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 4: Monthly Boxplot (MỚI) ─────────────────────────────────────────
    with tab_monthly:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-header">'
            '<span class="card-title">Phân phối biến động giá theo tháng</span>'
            '<span class="badge badge-purple">Boxplot</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        info_box(
            "📌 Box plot hiển thị <b>phân phối giá đóng cửa</b> từng tháng: "
            "đường giữa = median, hộp = IQR (25%–75%), râu = min/max, "
            "chấm = trung bình ± độ lệch chuẩn."
        )

        # Chọn năm
        if "date" in df.columns:
            years_avail = sorted(df["date"].dt.year.dropna().unique().astype(int), reverse=True)
        else:
            years_avail = [date.today().year]

        box_c1, _ = st.columns([1, 2])
        with box_c1:
            selected_year = st.selectbox(
                "Chọn năm",
                options=["Tất cả"] + [str(y) for y in years_avail],
                key="boxplot_year",
            )

        target_yr = None if selected_year == "Tất cả" else int(selected_year)
        fig_box = build_monthly_boxplot(df, symbol, target_year=target_yr, height=360)

        if fig_box.data:
            st.plotly_chart(fig_box, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.warning("Không đủ dữ liệu để vẽ boxplot. Thử chọn năm khác.")

        st.markdown("</div>", unsafe_allow_html=True)