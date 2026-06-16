"""
pages/sources.py — Nguồn dữ liệu
Hiển thị 3 nguồn CafeF / TCBS / FireAnt với chip ngân hàng + bảng chi tiết.
Tương đương page-sources trong HTML mock-up.
"""

from __future__ import annotations

import streamlit as st

from database import DatabaseManager, BANK_META, SOURCE_GROUPS, SOURCE_BADGE
from utils import render_topbar, section_label, info_box, bank_chip_row, SOURCE_BADGE_CLS

# Dữ liệu demo giá — dùng khi chưa kết nối Drill
_DEMO_PRICE = {
    "VCB": (82400,  1.23, "3.2M"),  "BID": (54200, -0.18, "4.1M"),
    "CTG": (48700,  0.41, "3.8M"),  "MBB": (26900,  0.75, "7.2M"),
    "TCB": (45800,  1.11, "4.4M"),  "VPB": (21350, -0.23, "9.1M"),
    "ACB": (24150,  0.62, "5.8M"),  "STB": (33200, -0.30, "2.1M"),
    "SHB": (14800,  0.68, "8.3M"),  "HDB": (28600,  1.42, "2.6M"),
    "VIB": (18650, -0.27, "1.9M"),  "TPB": (16200,  0.93, "3.4M"),
    "EIB": (29100,  0.34, "1.2M"),  "MSB": (15400, -0.65, "4.7M"),
    "SSB": (19700,  0.51, "2.8M"),  "LPB": (19850,  0.76, "3.7M"),
    "OCB": (15300,  1.05, "1.3M"),  "NAB": (12400,  0.81, "0.9M"),
    "KLB": (11800, -0.42, "0.6M"),  "BVB": (10900,  0.18, "0.4M"),
}

_SOURCE_META = {
    "CafeF":   {
        "color":   "#3B82F6",
        "badge":   "badge-blue",
        "desc":    "8 mã lớn nhất — thu thập qua vnstock / CafeF scraper",
        "count":   8,
    },
    "TCBS":    {
        "color":   "#8B5CF6",
        "badge":   "badge-purple",
        "desc":    "8 mã trung bình — TCBS API",
        "count":   8,
    },
    "FireAnt": {
        "color":   "#06B6D4",
        "badge":   "badge-cyan",
        "desc":    "4 mã nhỏ — FireAnt API",
        "count":   4,
    },
}


def _source_table(source: str, symbols: list[str]) -> None:
    """Bảng chi tiết mã theo nguồn."""
    rows = ""
    for sym in symbols:
        meta      = BANK_META.get(sym, {})
        price, chg, vol = _DEMO_PRICE.get(sym, (0, 0, "—"))
        chg_cls   = "pos" if chg >= 0 else "neg"
        arrow     = "▲" if chg >= 0 else "▼"
        badge_cls = SOURCE_BADGE_CLS.get(source, "badge-blue")
        rows += f"""
        <tr>
          <td><span style="font-family:var(--font-mono);font-weight:700;
                           color:var(--accent-bright);letter-spacing:.05em">{sym}</span></td>
          <td style="font-size:.80rem;color:var(--text-secondary);
                     font-family:var(--font-body)">{meta.get('name','—')}</td>
          <td style="font-family:var(--font-mono);font-weight:600;
                     color:var(--text-primary)">{price:,}</td>
          <td class="{chg_cls}" style="font-size:.80rem;font-family:var(--font-mono)">
            {arrow} {abs(chg):.2f}%</td>
          <td style="color:var(--text-muted);font-size:.78rem">{vol}</td>
          <td><span class="badge {badge_cls}">{source}</span></td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:.82rem;">
      <thead>
        <tr style="border-bottom:1px solid var(--border-soft);">
          {"".join(f'<th style="padding:5px 6px;text-align:left;font-size:.60rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:var(--text-muted)">{h}</th>'
                   for h in ["Mã CP", "Tên ngân hàng", "Giá đóng cửa", "%Thay đổi", "KL", "Nguồn"])}
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render(db: DatabaseManager) -> None:
    render_topbar(
        "Nguồn dữ liệu",
        "CafeF · TCBS · FireAnt — 20 mã ngân hàng Việt Nam",
        breadcrumb="Nguồn dữ liệu",
    )

    info_box(
        "Dữ liệu cổ phiếu thu thập từ 3 nguồn: <b>CafeF</b> (8 mã lớn), "
        "<b>TCBS</b> (8 mã trung), <b>FireAnt</b> (4 mã nhỏ). "
        "Pipeline Oozie tự động import qua Sqoop vào HDFS."
    )

    for source, symbols in SOURCE_GROUPS.items():
        meta_s = _SOURCE_META[source]
        sym_str = " · ".join(symbols)

        section_label(f"{source} — {meta_s['count']} ngân hàng")

        st.markdown(f"""
        <div class="card" style="border-left:3px solid {meta_s['color']};margin-bottom:8px;">
          <div class="card-header">
            <span class="card-title">{source}</span>
            <span class="badge {meta_s['badge']}">{meta_s['count']} mã · {sym_str}</span>
          </div>
        """, unsafe_allow_html=True)

        # Chip row
        bank_chip_row(symbols, source)

        # Table
        _source_table(source, symbols)

        # Progress bar
        pct = int(meta_s["count"] / 20 * 100)
        st.markdown(f"""
          <div style="margin-top:10px;display:flex;align-items:center;gap:10px;">
            <div style="flex:1;height:3px;border-radius:99px;background:var(--bg-elevated);overflow:hidden;">
              <div style="height:100%;width:{pct}%;background:{meta_s['color']};
                          border-radius:99px;transition:width .3s;"></div>
            </div>
            <span style="font-size:.68rem;color:var(--text-muted);
                         font-family:var(--font-mono);white-space:nowrap;">{pct}% tổng danh mục</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)