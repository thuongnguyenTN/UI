"""
pages/crud.py — Quản lý danh mục mã ngân hàng
CRUD: Thêm / Sửa / Xóa / Bật-Tắt mã cổ phiếu trong tbl_bank_list
Kết nối: MySQL trực tiếp (qua DatabaseManager) hoặc dummy mode
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import time

from database import DatabaseManager, get_dynamic_bank_meta
from utils import render_topbar, section_label, info_box


SOURCES = ["CafeF", "TCBS", "FireAnt", "vnstock"]
STATUS_MAP = {1: ("badge-green",  "● Đang cào"),
              0: ("badge-amber",  "○ Tạm ngưng")}

def _load_bank_list(db: DatabaseManager) -> pd.DataFrame:
    """Đọc toàn bộ tbl_bank_list. Fallback dummy nếu bảng chưa có."""
    if db.mode == "dummy":
        return _dummy_bank_list()

    from sqlalchemy import text
    try:
        with db._engine.connect() as conn:
            df = pd.read_sql(
                text("SELECT id, symbol, bank_name, source, status "
                     "FROM bigdata_stock.tbl_bank_list ORDER BY id"),
                conn,
            )
        return df
    except Exception as e:
        st.error(f"Lỗi kết nối DB chi tiết: {e}")
        st.warning("⚠ Không đọc được tbl_bank_list — hiển thị dữ liệu mẫu.")
        return _dummy_bank_list()

def _dummy_bank_list() -> pd.DataFrame:
    return pd.DataFrame([
        {"id": 1,  "symbol": "VCB", "bank_name": "Vietcombank",      "source": "CafeF",   "status": 1},
        {"id": 2,  "symbol": "ACB", "bank_name": "ACB",              "source": "CafeF",   "status": 1},
        {"id": 3,  "symbol": "STB", "bank_name": "Sacombank",        "source": "CafeF",   "status": 1},
    ])

def _exec(db: DatabaseManager, sql: str, params: dict) -> bool:
    """Thực thi INSERT / UPDATE / DELETE. Trả về True nếu thành công."""
    if db.mode == "dummy":
        return True
    from sqlalchemy import text
    try:
        with db._engine.begin() as conn:
            conn.execute(text(sql), params)
        return True
    except Exception as exc:
        st.error(f"❌ Lỗi DB: {exc}")
        return False

def _kpi_row(df: pd.DataFrame) -> None:
    total   = len(df)
    active  = int((df["status"] == 1).sum())
    paused  = total - active
    sources = df["source"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Tổng mã quản lý",  total)
    k2.metric("Đang kích hoạt",   active,  delta=f"+{active} mã")
    k3.metric("Tạm ngưng",        paused)
    k4.metric("Nguồn dữ liệu",    sources)

def _table_view(df: pd.DataFrame) -> None:
    rows_html = ""
    for _, r in df.iterrows():
        badge_cls, badge_lbl = STATUS_MAP.get(int(r["status"]), ("badge-amber", "—"))
        src_cls = {
            "CafeF": "badge-blue", "TCBS": "badge-purple",
            "FireAnt": "badge-cyan", "vnstock": "badge-green",
        }.get(r["source"], "badge-blue")

        rows_html += f"""
        <tr>
          <td style="font-family:var(--font-mono);font-size:.76rem;color:var(--text-muted);
                     padding:10px 14px;border-bottom:1px solid var(--border-soft);">
            #{int(r['id'])}</td>
          <td style="padding:10px 14px;border-bottom:1px solid var(--border-soft);">
            <span style="font-family:var(--font-mono);font-size:.88rem;font-weight:700;
                         color:var(--accent-bright);letter-spacing:.06em;">{r['symbol']}</span>
          </td>
          <td style="padding:10px 14px;border-bottom:1px solid var(--border-soft);
                     font-size:.80rem;color:var(--text-secondary);">{r['bank_name']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid var(--border-soft);">
            <span class="badge {src_cls}">{r['source']}</span></td>
          <td style="padding:10px 14px;border-bottom:1px solid var(--border-soft);">
            <span class="badge {badge_cls}">{badge_lbl}</span></td>
        </tr>"""

    table_html = f"""
    <div style="overflow-x:auto;border-radius:var(--radius-md);border:1px solid var(--border);box-shadow:var(--shadow-sm);">
      <table style="width:100%;border-collapse:collapse;background:var(--bg-card);">
        <thead>
          <tr style="border-bottom:1px solid rgba(59,130,246,.15);">
            <th style="padding:10px 14px;text-align:left;font-size:.62rem;font-weight:700;text-transform:uppercase;color:var(--text-muted);font-family:var(--font);">ID</th>
            <th style="padding:10px 14px;text-align:left;font-size:.62rem;font-weight:700;text-transform:uppercase;color:var(--text-muted);font-family:var(--font);">Mã CP</th>
            <th style="padding:10px 14px;text-align:left;font-size:.62rem;font-weight:700;text-transform:uppercase;color:var(--text-muted);font-family:var(--font);">Tên ngân hàng</th>
            <th style="padding:10px 14px;text-align:left;font-size:.62rem;font-weight:700;text-transform:uppercase;color:var(--text-muted);font-family:var(--font);">Nguồn cào</th>
            <th style="padding:10px 14px;text-align:left;font-size:.62rem;font-weight:700;text-transform:uppercase;color:var(--text-muted);font-family:var(--font);">Trạng thái</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>"""
    st.markdown(table_html, unsafe_allow_html=True)

def _form_add(db: DatabaseManager) -> None:
    st.markdown('<div class="card" style="border-left:3px solid var(--green);"><div class="card-header"><span class="card-title">Thêm mã ngân hàng mới</span><span class="badge badge-green">INSERT</span></div></div>', unsafe_allow_html=True)
    with st.form("form_add", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            new_sym  = st.text_input("Mã CP *", placeholder="VD: TCB", max_chars=10).strip().upper()
        with c2:
            new_name = st.text_input("Tên ngân hàng *", placeholder="VD: Techcombank").strip()
        with c3:
            new_src  = st.selectbox("Nguồn cào *", SOURCES)
        submitted = st.form_submit_button("➕  Thêm mã", use_container_width=True)

    if submitted:
        if not new_sym or not new_name:
            st.error("Vui lòng điền đủ Mã CP và Tên ngân hàng.")
            return

        existing = _load_bank_list(db)
        if new_sym in existing["symbol"].values:
            st.error(f"Mã **{new_sym}** đã tồn tại trong danh sách.")
            return

        ok = _exec(db,
                   "INSERT INTO bigdata_stock.tbl_bank_list (symbol, bank_name, source, status) "
                   "VALUES (:sym, :name, :src, 1)",
                   {"sym": new_sym, "name": new_name, "src": new_src})
        if ok:
            # ĐÃ SỬA: Cập nhật biến động để các trang khác thấy mã mới ngay lập tức
            dynamic_meta = get_dynamic_bank_meta()
            dynamic_meta[new_sym] = {"name": new_name, "source": new_src}
            
            st.success(f"✅ Đã thêm mã **{new_sym} — {new_name}** (nguồn: {new_src}).")
            st.cache_resource.clear()
            st.rerun()

def _form_edit(db: DatabaseManager, df: pd.DataFrame) -> None:
    st.markdown('<div class="card" style="border-left:3px solid var(--accent-light);"><div class="card-header"><span class="card-title">Cập nhật thông tin mã</span><span class="badge badge-blue">UPDATE</span></div></div>', unsafe_allow_html=True)
    sym_options = df["symbol"].tolist()
    if not sym_options:
        info_box("Chưa có mã nào trong danh sách.")
        return

    sel = st.selectbox("Chọn mã cần sửa", sym_options, key="edit_select")
    row = df[df["symbol"] == sel].iloc[0]

    with st.form("form_edit"):
        c1, c2 = st.columns([2, 1])
        with c1:
            upd_name = st.text_input("Tên ngân hàng", value=row["bank_name"])
        with c2:
            upd_src  = st.selectbox("Nguồn cào", SOURCES, index=SOURCES.index(row["source"]) if row["source"] in SOURCES else 0)

        upd_status = st.radio("Trạng thái", options=[1, 0], format_func=lambda x: "● Kích hoạt" if x == 1 else "○ Ngưng", index=0 if int(row["status"]) == 1 else 1, horizontal=True)
        submitted = st.form_submit_button("💾  Lưu thay đổi", use_container_width=True)

    if submitted:
        ok = _exec(db,
                   "UPDATE bigdata_stock.tbl_bank_list SET bank_name=:name, source=:src, status=:st "
                   "WHERE symbol=:sym",
                   {"name": upd_name.strip(), "src": upd_src, "st": upd_status, "sym": sel})
        if ok:
            # ĐÃ SỬA: Cập nhật biến động tên và nguồn nếu có sửa đổi
            dynamic_meta = get_dynamic_bank_meta()
            if sel in dynamic_meta:
                dynamic_meta[sel]["name"] = upd_name.strip()
                dynamic_meta[sel]["source"] = upd_src

            st.success(f"✅ Đã cập nhật mã **{sel}**.")
            st.rerun()

def _form_toggle(db: DatabaseManager, df: pd.DataFrame) -> None:
    st.markdown('<div class="card" style="border-left:3px solid var(--amber);"><div class="card-header"><span class="card-title">Bật / Tắt trạng thái</span><span class="badge badge-amber">TOGGLE</span></div></div>', unsafe_allow_html=True)
    col_on, col_off = st.columns(2)
    with col_on:
        paused_syms = df[df["status"] == 0]["symbol"].tolist()
        sel_on = st.multiselect("Kích hoạt lại", paused_syms)
        if st.button("▶ Kích hoạt", disabled=not sel_on, use_container_width=True):
            for s in sel_on:
                _exec(db, "UPDATE bigdata_stock.tbl_bank_list SET status=1 WHERE symbol=:sym", {"sym": s})
            st.rerun()

    with col_off:
        active_syms = df[df["status"] == 1]["symbol"].tolist()
        sel_off = st.multiselect("Tạm ngưng", active_syms)
        if st.button("⏸ Tạm ngưng", disabled=not sel_off, use_container_width=True):
            for s in sel_off:
                _exec(db, "UPDATE bigdata_stock.tbl_bank_list SET status=0 WHERE symbol=:sym", {"sym": s})
            st.rerun()

def _form_delete(db: DatabaseManager, df: pd.DataFrame) -> None:
    st.markdown('<div class="card" style="border-left:3px solid var(--red);"><div class="card-header"><span class="card-title">Xóa mã</span><span class="badge badge-red">DELETE</span></div></div>', unsafe_allow_html=True)
    sym_del = st.selectbox("Chọn mã cần xóa", df["symbol"].tolist())
    confirm = st.text_input(f'Gõ lại mã **{sym_del}** để xác nhận', placeholder=sym_del)
    
    if st.button("🗑  Xóa vĩnh viễn", type="primary", disabled=(confirm.strip().upper() != sym_del)):
        ok = _exec(db, "DELETE FROM bigdata_stock.tbl_bank_list WHERE symbol=:sym", {"sym": sym_del})
        if ok:
            # ĐÃ SỬA: Xóa khỏi danh sách biến động
            dynamic_meta = get_dynamic_bank_meta()
            if sym_del in dynamic_meta:
                del dynamic_meta[sym_del]

            st.success(f"🗑 Đã xóa mã **{sym_del}** khỏi danh sách.")
            st.rerun()

def render(db: DatabaseManager) -> None:
    render_topbar("Quản lý danh mục", "CRUD · tbl_bank_list", breadcrumb="Quản lý danh mục")
    df = _load_bank_list(db)
    
    section_label("Tổng quan danh mục")
    _kpi_row(df)
    st.markdown("<br>", unsafe_allow_html=True)
    
    section_label("Danh sách mã ngân hàng — tbl_bank_list")
    _table_view(df)
    st.markdown("<br>", unsafe_allow_html=True)
    
    section_label("Thao tác CRUD")
    tab_add, tab_edit, tab_toggle, tab_del = st.tabs(["➕ Thêm mã", "✏️ Sửa", "🔁 Bật/Tắt", "🗑 Xóa"])

    with tab_add: _form_add(db)
    with tab_edit: _form_edit(db, df)
    with tab_toggle: _form_toggle(db, df)
    with tab_del: _form_delete(db, df)