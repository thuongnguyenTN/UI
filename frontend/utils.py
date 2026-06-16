"""
utils.py — Hàm tiện ích dùng chung toàn GUI
Cập nhật: align với BigData HTML mock-up (20 mã, 3 nguồn CafeF/TCBS/FireAnt)
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ── CSS loader ───────────────────────────────────────────────────────────────

def load_css(path: str = "style.css") -> None:
    p = Path(path)
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)
    else:
        st.warning(f"⚠ Không tìm thấy style.css tại {p.resolve()}")


# ── Plotly base layout ───────────────────────────────────────────────────────

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, Segoe UI, sans-serif",
              color="#7A92B8", size=11),
    margin=dict(l=8, r=8, t=40, b=8),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#0D1520", bordercolor="#2563EB",
                    font_size=12, font_color="#E8F0FE"),
    xaxis=dict(showgrid=False, showline=False, zeroline=False,
               gridcolor="rgba(59,130,246,0.04)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.035)",
               showline=False, zeroline=False),
    legend=dict(
        bgcolor="rgba(13,21,32,0.90)",
        bordercolor="rgba(255,255,255,0.05)",
        borderwidth=1,
        font=dict(size=11, color="#7A92B8"),
        orientation="h",
        yanchor="bottom", y=-0.24,
        xanchor="left", x=0,
    ),
)

PALETTE = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#F97316", "#EC4899", "#14B8A6",
]

# Màu theo nguồn — khớp với HTML mock-up
SOURCE_COLOR = {
    "CafeF":   "#3B82F6",
    "TCBS":    "#8B5CF6",
    "FireAnt": "#06B6D4",
}
SOURCE_BADGE_CLS = {
    "CafeF":   "badge-blue",
    "TCBS":    "badge-purple",
    "FireAnt": "badge-cyan",
}

def _color(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


# ── Chart builders ───────────────────────────────────────────────────────────

def build_line_chart(
    df: pd.DataFrame,
    symbols: list[str],
    title: str = "Giá đóng cửa",
    height: int = 380,
    normalize: bool = False,
) -> go.Figure:
    fig = go.Figure()
    col = "symbol" if "symbol" in df.columns else "ticker"
    for i, sym in enumerate(symbols):
        sub = df[df[col] == sym].copy().sort_values("date")
        if sub.empty:
            continue
        y = sub["close"].to_numpy(dtype=float)
        if normalize and y[0] > 0:
            y = y / y[0] * 100
        fig.add_trace(go.Scatter(
            x=sub["date"], y=y, name=sym, mode="lines",
            line=dict(color=_color(i), width=2.2),
            hovertemplate=(
                f"<b>{sym}</b><br>%{{x|%d/%m/%Y}}<br>"
                + ("Norm: %{y:.2f}<extra></extra>" if normalize
                   else "Giá: %{y:,.0f}₫<extra></extra>")
            ),
        ))
    fig.update_layout(**_PLOTLY, height=height,
                      title=dict(text=title, font=dict(size=13, color="#3D5478")))
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"))
    return fig


def build_volume_chart(
    df: pd.DataFrame,
    symbol: str,
    height: int = 200,
) -> go.Figure:
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy().sort_values("date")
    if sub.empty:
        return go.Figure()
    colors = np.where(sub["close"].diff().fillna(0) >= 0, "#10B981", "#EF4444")
    fig = go.Figure(go.Bar(
        x=sub["date"], y=sub["volume"],
        marker_color=colors, opacity=0.70,
        hovertemplate="%{x|%d/%m/%Y}<br>Vol: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**_PLOTLY, height=height, bargap=0.15,
                      title=dict(text="Khối lượng giao dịch",
                                 font=dict(size=13, color="#3D5478")))
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"))
    return fig


def build_sma_chart(
    df: pd.DataFrame,
    symbol: str,
    windows: tuple[int, ...] = (20, 50),
    height: int = 420,
) -> go.Figure:
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy().sort_values("date")
    if "avg_close_price" in sub.columns and "close" not in sub.columns:
        sub = sub.rename(columns={"avg_close_price": "close"})
    if sub.empty:
        return go.Figure()
    for w in windows:
        sub[f"sma{w}"] = sub["close"].rolling(w).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["close"], name="Close", mode="lines",
        line=dict(color="#3B82F6", width=2.2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.045)",
        hovertemplate="Giá: %{y:,.0f}₫<extra></extra>",
    ))
    sma_style = {
        20:  dict(color="#10B981", dash="solid", width=1.6),
        50:  dict(color="#F59E0B", dash="dot",   width=1.6),
        200: dict(color="#EF4444", dash="dash",  width=1.6),
    }
    for w in windows:
        if f"sma{w}" not in sub.columns:
            continue
        fig.add_trace(go.Scatter(
            x=sub["date"], y=sub[f"sma{w}"], name=f"SMA {w}", mode="lines",
            line=sma_style.get(w, dict(color="#8B5CF6", dash="dot", width=1.6)),
            hovertemplate=f"SMA{w}: %{{y:,.0f}}₫<extra></extra>",
        ))
    fig.update_layout(**_PLOTLY, height=height,
                      title=dict(text=f"{symbol} — Close & SMA",
                                 font=dict(size=13, color="#3D5478")))
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"))
    return fig


def build_analysis_bar(
    df: pd.DataFrame,
    symbol: str,
    height: int = 280,
) -> go.Figure:
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy().sort_values(
        "calc_date" if "calc_date" in df.columns else "date"
    )
    date_col  = "calc_date" if "calc_date" in sub.columns else "date"
    price_col = "avg_close_price" if "avg_close_price" in sub.columns else "close"
    fig = go.Figure(go.Bar(
        x=sub[date_col], y=sub[price_col],
        marker_color="#3B82F6", opacity=0.78,
        hovertemplate="%{x|%d/%m/%Y}<br>Avg Close: %{y:,.0f}₫<extra></extra>",
    ))
    fig.update_layout(**_PLOTLY, height=height,
                      title=dict(text=f"{symbol} — avg_close_price (Spark result)",
                                 font=dict(size=13, color="#3D5478")))
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"))
    return fig


def build_volatility_heatmap(df: pd.DataFrame, height: int = 260) -> go.Figure:
    col = "symbol" if "symbol" in df.columns else "ticker"
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["date"]).dt.to_period("M").astype(str)
    df2["pct"] = (
        df2.groupby(col)["close"].pct_change().abs() * 100
        if "close" in df2.columns else 0
    )
    pivot = (
        df2.groupby([col, "month"])["pct"]
        .mean().reset_index()
        .pivot(index=col, columns="month", values="pct")
        .iloc[:, -18:]
    )
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=[
            [0,   "#080D14"], [0.3, "#0F2C5A"],
            [0.6, "#1D4ED8"], [1,   "#60A5FA"],
        ],
        hovertemplate="<b>%{y}</b> | %{x}<br>Volatility: %{z:.3f}%<extra></extra>",
        showscale=True,
        colorbar=dict(len=0.85, thickness=10, outlinecolor="rgba(0,0,0,0)"),
    ))
    fig.update_layout(**_PLOTLY, height=height,
                      title=dict(text="Heatmap biến động trung bình hàng tháng (%)",
                                 font=dict(size=13, color="#3D5478")))
    fig.update_xaxes(tickangle=-40, tickfont=dict(size=9, color="#3D5478"),
                     rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=9, color="#3D5478"))
    return fig


# ── Formatters ───────────────────────────────────────────────────────────────

def fmt_price(v: float) -> str:
    return f"{v:,.0f}₫"

def fmt_volume(v: float) -> str:
    if v >= 1_000_000: return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:     return f"{v / 1_000:.0f}K"
    return str(int(v))

def fmt_pct(v: float) -> str:
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"


# ── SMA helper ───────────────────────────────────────────────────────────────

def add_sma(df: pd.DataFrame, windows: tuple[int, ...] = (20, 50)) -> pd.DataFrame:
    col = "symbol" if "symbol" in df.columns else "ticker"
    frames = []
    for sym in df[col].unique():
        sub = df[df[col] == sym].copy().sort_values("date")
        for w in windows:
            sub[f"sma{w}"] = sub["close"].rolling(w).mean()
        frames.append(sub)
    return pd.concat(frames, ignore_index=True) if frames else df


def compute_stats(df: pd.DataFrame, symbol: str) -> dict:
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy().sort_values("date")
    if sub.empty:
        return {}
    sub = add_sma(sub, (20, 50))
    last    = sub.iloc[-1]
    ret     = (sub["close"].iloc[-1] / sub["close"].iloc[0] - 1) * 100
    vol_ann = sub["close"].pct_change().std() * np.sqrt(252) * 100
    vol_idx = sub["volume"].idxmax() if "volume" in sub.columns else None
    var_idx = sub["close"].pct_change().abs().idxmax()
    return {
        "symbol":       symbol,
        "price":        last["close"],
        "sma20":        last.get("sma20", float("nan")),
        "sma50":        last.get("sma50", float("nan")),
        "return_pct":   ret,
        "volatility":   vol_ann,
        "max_close":    sub["close"].max(),
        "min_close":    sub["close"].min(),
        "max_volume":   sub["volume"].max() if "volume" in sub.columns else 0,
        "max_vol_date": (sub.loc[vol_idx, "date"].strftime("%d/%m/%Y")
                         if vol_idx is not None else "N/A"),
        "max_var_date": sub.loc[var_idx, "date"].strftime("%d/%m/%Y"),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  HTML COMPONENT BUILDERS — theo design language HTML mock-up
# ══════════════════════════════════════════════════════════════════════════════

def render_topbar(title: str, subtitle: str, breadcrumb: str = "") -> None:
    now = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
    bc  = breadcrumb or "Dashboard"
    st.markdown(f"""
    <div class="topbar">
      <div class="topbar-left">
        <div class="t-breadcrumb">📊 BigData Stock &nbsp;›&nbsp; {bc}</div>
        <div class="t-title">{title}</div>
        <div class="t-sub">{subtitle}</div>
      </div>
      <div class="topbar-right">
        <span class="live-pill">
          <span class="dot dot-green dot-pulse"></span>LIVE
        </span>
        <span class="timestamp">{now}</span>
      </div>
    </div>
    <div class="accent-line"></div>
    """, unsafe_allow_html=True)


def render_kpi_card(
    symbol:  str,
    name:    str,
    price:   float,
    pct_chg: float,
    volume:  float,
    source:  str = "",
) -> None:
    """KPI card khớp style HTML mock-up: ticker / name / price / delta / vol."""
    arrow = "▲" if pct_chg >= 0 else "▼"
    cls   = "pos" if pct_chg >= 0 else "neg"
    src_badge = ""
    if source:
        badge_cls = SOURCE_BADGE_CLS.get(source, "badge-blue")
        src_badge = f'<span class="badge {badge_cls}" style="font-size:0.60rem">{source}</span>'
    st.markdown(f"""
    <div class="kpi-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px">
        <div class="kpi-ticker">{symbol}</div>
        {src_badge}
      </div>
      <div class="kpi-name">{name}</div>
      <div class="kpi-price">{fmt_price(price)}</div>
      <div class="kpi-change {cls}">{arrow} {abs(pct_chg):.2f}%</div>
      <div class="kpi-vol">Vol &nbsp;{fmt_volume(volume)}</div>
    </div>
    """, unsafe_allow_html=True)


def source_overview_cards(bank_meta: dict) -> None:
    """
    3 source cards (CafeF / TCBS / FireAnt) — dịch từ .source-grid trong HTML mock-up.
    Hiển thị count, danh sách mã, progress bar.
    """
    groups = {
        "CafeF":   {"color": "#3B82F6", "badge": "badge-blue"},
        "TCBS":    {"color": "#8B5CF6", "badge": "badge-purple"},
        "FireAnt": {"color": "#06B6D4", "badge": "badge-cyan"},
    }
    totals = {src: 0 for src in groups}
    members = {src: [] for src in groups}
    for sym, meta in bank_meta.items():
        src = meta.get("source", "CafeF")
        if src in totals:
            totals[src] += 1
            members[src].append(sym)

    grand_total = sum(totals.values()) or 1
    cols = st.columns(3)
    labels = {"CafeF": "8 mã lớn", "TCBS": "8 mã trung", "FireAnt": "4 mã nhỏ"}

    for col, (src, cfg) in zip(cols, groups.items()):
        cnt  = totals[src]
        syms = " · ".join(members[src])
        pct  = int(cnt / grand_total * 100)
        with col:
            st.markdown(f"""
            <div class="card" style="border-left:3px solid {cfg['color']};padding:12px 14px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                <span class="card-title">{src}</span>
                <span class="badge {cfg['badge']}">{cnt} mã</span>
              </div>
              <div style="font-size:1.6rem;font-weight:700;color:var(--text-primary);
                          font-family:var(--font-mono);letter-spacing:-0.03em;">{cnt}</div>
              <div style="font-size:0.68rem;color:var(--text-muted);margin:3px 0 8px;
                          font-family:var(--font-body);">{labels[src]} · {syms}</div>
              <div style="height:3px;border-radius:99px;background:var(--bg-elevated);overflow:hidden;">
                <div style="height:100%;width:{pct}%;background:{cfg['color']};border-radius:99px;"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)


def bank_chip_row(symbols: list[str], source: str) -> None:
    """Hàng chip mã ngân hàng theo nguồn — khớp .bank-chips trong HTML."""
    color_map = {
        "CafeF":   ("rgba(59,130,246,0.12)", "#60A5FA"),
        "TCBS":    ("rgba(139,92,246,0.12)", "#A78BFA"),
        "FireAnt": ("rgba(6,182,212,0.12)",  "#22D3EE"),
    }
    bg, fg = color_map.get(source, ("rgba(59,130,246,0.12)", "#60A5FA"))
    chips  = "".join(
        f'<span style="font-size:0.72rem;font-weight:700;padding:3px 8px;'
        f'border-radius:99px;letter-spacing:0.06em;background:{bg};color:{fg};'
        f'border:1px solid {fg}44;font-family:var(--font-mono);">{s}</span>'
        for s in symbols
    )
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;">'
        f'{chips}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def info_box(text: str, color: str = "blue") -> None:
    border = {"blue": "var(--accent)", "red": "var(--red)", "amber": "var(--amber)"}.get(color, "var(--accent)")
    bg     = {"blue": "rgba(37,99,235,0.07)", "red": "rgba(239,68,68,0.07)", "amber": "rgba(245,158,11,0.07)"}.get(color, "rgba(37,99,235,0.07)")
    fg     = {"blue": "var(--accent-bright)", "red": "#F87171", "amber": "#FBBF24"}.get(color, "var(--accent-bright)")
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {border}33;border-left:3px solid {border};
                border-radius:var(--radius-sm);padding:9px 13px;font-size:0.78rem;
                color:{fg};margin-bottom:0.85rem;font-family:var(--font-body);line-height:1.55;">
      {text}
    </div>
    """, unsafe_allow_html=True)


def stat_row_html(label: str, value: str, cls: str = "") -> str:
    """Trả về HTML 1 dòng stat-row — dùng trong card."""
    val_style = ""
    if cls == "pos":
        val_style = "color:var(--green-light);"
    elif cls == "neg":
        val_style = "color:var(--red);"
    return (
        f'<div class="stat-row">'
        f'<span class="stat-label">{label}</span>'
        f'<span class="stat-value" style="{val_style}">{value}</span>'
        f'</div>'
    )


def render_sidebar_logo() -> None:
    st.markdown("""
    <div class="sb-brand">
      <div class="sb-brand-row">
        <div class="sb-icon">📊</div>
        <div>
          <div class="sb-title">BigData Stock<br>Dashboard</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_footer(db_mode: str, connected: bool) -> None:
    dot    = "dot-green" if connected else "dot-red"
    status = "Online" if connected else "Offline"
    source = {
        "dummy": "Demo / Dummy Data",
        "mysql": "MySQL · bigdata_stock",
        "drill": "Apache Drill",
    }.get(db_mode, db_mode)
    st.markdown(f"""
    <div class="sb-footer">
      <div class="sb-footer-row">
        <span>Data Source</span>
        <span class="sb-footer-val">{source}</span>
      </div>
      <div class="sb-footer-row">
        <span>Connection</span>
        <span class="sb-footer-val">
          <span class="dot {dot}"></span>&nbsp;{status}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def card_open(title: str, badge: str = "", badge_cls: str = "badge-blue") -> None:
    badge_html = f'<span class="badge {badge_cls}">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="card">
      <div class="card-header">
        <span class="card-title">{title}</span>
        {badge_html}
      </div>
    """, unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


"""
Các hàm chart builder mới — bổ sung vào utils.py
Tương ứng với 4 phương thức còn thiếu trong presentation.py:
  1. build_intraday_price_volume  → plot_intraday_price_volume
  2. build_daily_moving_average   → plot_daily_moving_average
  3. build_monthly_boxplot        → plot_monthly_volatility
  4. build_yearly_stacked_volume  → plot_yearly_stacked_volume
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Shared Plotly base (copy từ utils._PLOTLY) ────────────────────────────────
_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, Segoe UI, sans-serif",
              color="#7A92B8", size=11),
    margin=dict(l=8, r=8, t=40, b=8),
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#0D1520", bordercolor="#2563EB",
                    font_size=12, font_color="#E8F0FE"),
    xaxis=dict(showgrid=False, showline=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.035)",
               showline=False, zeroline=False),
    legend=dict(
        bgcolor="rgba(13,21,32,0.90)",
        bordercolor="rgba(255,255,255,0.05)",
        borderwidth=1,
        font=dict(size=11, color="#7A92B8"),
        orientation="h",
        yanchor="bottom", y=-0.28,
        xanchor="left", x=0,
    ),
)

PALETTE = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#F97316", "#EC4899",
]

MONTH_NAMES_VI = [
    "Th.1","Th.2","Th.3","Th.4","Th.5","Th.6",
    "Th.7","Th.8","Th.9","Th.10","Th.11","Th.12",
]


# ── 1. Intraday Price + Volume (dual-axis) ────────────────────────────────────

def build_intraday_price_volume(
    df: pd.DataFrame,
    symbol: str,
    target_date: str,
    height: int = 360,
) -> go.Figure:
    """
    Dual-axis: đường giá đóng cửa (trái) + cột khối lượng (phải)
    Lọc theo symbol & target_date (YYYY-MM-DD).
    Tương đương PresentationLayer.plot_intraday_price_volume.
    """
    col = "symbol" if "symbol" in df.columns else "ticker"
    date_col = "scrape_time" if "scrape_time" in df.columns else "date"

    mask = df[col] == symbol
    if "trading_date" in df.columns:
        mask &= df["trading_date"].astype(str).str.startswith(target_date)
    elif "date" in df.columns:
        mask &= df["date"].astype(str).str.startswith(target_date)

    sub = df[mask].copy().sort_values(date_col)
    if sub.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Giá đóng cửa — đường xanh
    fig.add_trace(go.Scatter(
        x=sub[date_col], y=sub["close"],
        name="Giá đóng cửa",
        mode="lines",
        line=dict(color="#3B82F6", width=2.2),
        hovertemplate="Giá: %{y:,.0f}₫<extra></extra>",
    ), secondary_y=False)

    # Volume — cột xám bán trong suốt
    fig.add_trace(go.Bar(
        x=sub[date_col], y=sub["volume"],
        name="Khối lượng",
        marker_color="rgba(122,146,184,0.25)",
        hovertemplate="Vol: %{y:,.0f}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        **_PLOTLY,
        height=height,
        title=dict(
            text=f"{symbol} — Giá & Khối lượng trong ngày ({target_date})",
            font=dict(size=13, color="#3D5478"),
        ),
        barmode="overlay",
    )
    fig.update_yaxes(
        title_text="Giá đóng cửa (₫)",
        title_font=dict(size=10, color="#3B82F6"),
        tickfont=dict(size=10, color="#3D5478"),
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Khối lượng",
        title_font=dict(size=10, color="#7A92B8"),
        tickfont=dict(size=10, color="#3D5478"),
        showgrid=False,
        secondary_y=True,
    )
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    return fig


# ── 2. Daily Moving Average (MA10 / MA20 hoặc tùy chọn) ──────────────────────

def build_daily_moving_average(
    df: pd.DataFrame,
    symbol: str,
    ma1: int = 10,
    ma2: int = 20,
    height: int = 380,
) -> go.Figure:
    """
    Giá đóng cửa + 2 đường MA tùy chọn (mặc định MA10 & MA20).
    Tương đương PresentationLayer.plot_daily_moving_average.
    """
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy().sort_values("date")
    if sub.empty:
        return go.Figure()

    sub[f"MA{ma1}"] = sub["close"].rolling(window=ma1).mean()
    sub[f"MA{ma2}"] = sub["close"].rolling(window=ma2).mean()

    fig = go.Figure()

    # Giá close — nền mờ
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["close"],
        name="Giá đóng cửa",
        mode="lines",
        line=dict(color="rgba(122,146,184,0.55)", width=1.4),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.035)",
        hovertemplate="Giá: %{y:,.0f}₫<extra></extra>",
    ))

    # MA ngắn hạn — xanh lá
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub[f"MA{ma1}"],
        name=f"MA {ma1} ngày",
        mode="lines",
        line=dict(color="#10B981", width=2.0, dash="solid"),
        hovertemplate=f"MA{ma1}: %{{y:,.0f}}₫<extra></extra>",
    ))

    # MA dài hạn — cam đứt
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub[f"MA{ma2}"],
        name=f"MA {ma2} ngày",
        mode="lines",
        line=dict(color="#F59E0B", width=2.0, dash="dot"),
        hovertemplate=f"MA{ma2}: %{{y:,.0f}}₫<extra></extra>",
    ))

    # Golden/Death cross highlight
    cross = sub[f"MA{ma1}"] - sub[f"MA{ma2}"]
    prev  = cross.shift(1)
    golden = sub[(cross > 0) & (prev <= 0)]["date"]
    death  = sub[(cross < 0) & (prev >= 0)]["date"]

    for d in golden:
        # 1. Chỉ vẽ đường vline
        fig.add_vline(x=d, line_width=1, line_dash="dot",
                      line_color="rgba(16,185,129,0.35)")
        # 2. Thêm chữ mũi tên chú thích thủ công (tương đương annotation_position="top")
        fig.add_annotation(x=d, y=1, yref="paper", text="↑",
                           font=dict(color="#10B981", size=14), 
                           showarrow=False, yanchor="bottom")
    for d in death:
        # 1. Chỉ vẽ đường vline
        fig.add_vline(x=d, line_width=1, line_dash="dot",
                      line_color="rgba(239,68,68,0.35)")
        # 2. Thêm chữ mũi tên chú thích thủ công
        fig.add_annotation(x=d, y=1, yref="paper", text="↓",
                           font=dict(color="#EF4444", size=14), 
                           showarrow=False, yanchor="bottom")

    fig.update_layout(
        **_PLOTLY,
        height=height,
        title=dict(
            text=f"{symbol} — Đường trung bình động MA{ma1} & MA{ma2}",
            font=dict(size=13, color="#3D5478"),
        ),
    )
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"), rangeslider_visible=False)
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"), tickformat=",.0f")
    return fig


# ── 3. Monthly Price Distribution (Box plot) ─────────────────────────────────

def build_monthly_boxplot(
    df: pd.DataFrame,
    symbol: str,
    target_year: int = None,
    height: int = 360,
) -> go.Figure:
    """
    Box plot phân phối giá đóng cửa theo từng tháng.
    Tương đương PresentationLayer.plot_monthly_volatility.
    """
    col = "symbol" if "symbol" in df.columns else "ticker"
    sub = df[df[col] == symbol].copy()
    if sub.empty:
        return go.Figure()

    date_col = "date" if "date" in sub.columns else "trading_date"
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")

    if target_year:
        sub = sub[sub[date_col].dt.year == int(target_year)]
    if sub.empty:
        return go.Figure()

    sub["month"] = sub[date_col].dt.month

    fig = go.Figure()
    months_present = sorted(sub["month"].unique())

    for i, m in enumerate(months_present):
        mdata = sub[sub["month"] == m]["close"].dropna()
        label = MONTH_NAMES_VI[m - 1]
        color = PALETTE[i % len(PALETTE)]

        fig.add_trace(go.Box(
            y=mdata,
            name=label,
            marker_color=color,
            line_color=color,
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.18)",
            boxmean= False,
            hovertemplate=f"<b>{label}</b><br>Giá: %{{y:,.0f}}₫<extra></extra>",
        ))

    year_label = str(target_year) if target_year else "Tất cả"
    fig.update_layout(
        **_PLOTLY,
        height=height,
        showlegend=False,
        title=dict(
            text=f"{symbol} — Phân phối biến động giá theo tháng ({year_label})",
            font=dict(size=13, color="#3D5478"),
        ),
    )
    fig.update_xaxes(tickfont=dict(size=10, color="#3D5478"))
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"),
                     tickformat=",.0f",
                     title_text="Giá đóng cửa (₫)",
                     title_font=dict(size=10, color="#7A92B8"))
    return fig


# ── 4. Yearly Stacked Volume ──────────────────────────────────────────────────

def build_yearly_stacked_volume(
    df: pd.DataFrame,
    target_years: list = None,
    height: int = 340,
) -> go.Figure:
    """
    Stacked bar: so sánh tổng khối lượng giao dịch theo năm, nhóm theo mã.
    Tương đương PresentationLayer.plot_yearly_stacked_volume.
    """
    if df.empty:
        return go.Figure()

    data = df.copy()
    date_col = "date" if "date" in data.columns else "trading_date"
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data["year"] = data[date_col].dt.year
    col = "symbol" if "symbol" in data.columns else "ticker"

    if target_years:
        data = data[data["year"].isin([int(y) for y in target_years])]
    if data.empty:
        return go.Figure()

    pivot = (
        data.groupby(["year", col])["volume"]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )

    years   = [str(y) for y in pivot.index.tolist()]
    symbols = pivot.columns.tolist()

    fig = go.Figure()
    for i, sym in enumerate(symbols):
        fig.add_trace(go.Bar(
            name=sym,
            x=years,
            y=pivot[sym].values,
            marker_color=PALETTE[i % len(PALETTE)],
            opacity=0.82,
            hovertemplate=f"<b>{sym}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>",
        ))

    # Tổng trên đỉnh mỗi cột
    totals = pivot.sum(axis=1)
    for yr, total in zip(years, totals):
        fig.add_annotation(
            x=yr, y=total,
            text=f"{total/1e6:.1f}M",
            showarrow=False,
            yshift=8,
            font=dict(size=10, color="#E8F0FE"),
        )

    year_label = (", ".join(map(str, target_years))
                  if target_years else "Tất cả các năm")
    fig.update_layout(
        **_PLOTLY,
        height=height,
        barmode="stack",
        title=dict(
            text=f"So sánh thanh khoản dài hạn theo năm ({year_label})",
            font=dict(size=13, color="#3D5478"),
        ),
        legend=dict(
            bgcolor="rgba(13,21,32,0.90)",
            bordercolor="rgba(255,255,255,0.05)",
            borderwidth=1,
            font=dict(size=9, color="#7A92B8"),
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.01,
        ),
    )
    fig.update_xaxes(tickfont=dict(size=11, color="#7A92B8"))
    fig.update_yaxes(tickfont=dict(size=10, color="#3D5478"),
                     tickformat=",.0f",
                     title_text="Tổng khối lượng",
                     title_font=dict(size=10, color="#7A92B8"))
    return fig