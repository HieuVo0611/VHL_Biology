"""
Module: app.py
Purpose: Expert Demo Summary Dashboard — 1-click pipeline with Excel export.
Version: 2.0.0 (Summary Dashboard)
"""
import os
import tempfile

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.utils import (
    extract_peaks_from_txt,
    catboost_inference_from_csv,
    calculate_toxicity,
)
from src.phase_detector import update_phase_tags
from src.export_excel import generate_excel_report

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="VHL Biology Analysis", layout="wide", page_icon="🔬")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f0f2f5; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
    }
    .header-bar {
        background: linear-gradient(135deg, #1a365d, #2d5d8a);
        padding: 20px 32px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .header-title { color: white; font-size: 24px; font-weight: 700; margin: 0; }
    .header-sub { color: rgba(255,255,255,0.7); font-size: 14px; margin-top: 4px; }
    .success-msg { color: #16a34a; font-weight: 600; }
    .error-msg { color: #dc2626; font-weight: 600; }
    .warn-msg { color: #ca8a04; font-weight: 600; }
    .stage-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
    }
    .tox-result {
        background: linear-gradient(135deg, #fefce8, #fef9c3);
        border: 2px solid #fbbf24;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <p class="header-title">🔬 VHL Biology Analysis</p>
            <p class="header-sub">Phân tích DO & Phân loại mẫu sinh học</p>
        </div>
        <div style="background:rgba(255,255,255,0.15);padding:6px 14px;border-radius:8px;color:white;font-size:13px;">
            v1.1.0
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Session state defaults ───────────────────────────────────────────────────
for key in ("peaks_df", "classification", "toxicity_df", "do_array",
            "sample_name", "signal_points", "do_min", "do_max",
            "cls_name", "cls_pred", "cls_prob", "cls_error", "phase_error", "ran"):
    if key not in st.session_state:
        st.session_state[key] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  UPLOAD + RUN
# ═══════════════════════════════════════════════════════════════════════════════
upload_col, btn_col = st.columns([5, 1])
with upload_col:
    txt_file = st.file_uploader(
        "Upload file .txt (UTF-16, cột Time/DO)",
        type=["txt"],
        label_visibility="collapsed",
    )
with btn_col:
    run_clicked = st.button("▶ Phân tích", type="primary",
                            disabled=(txt_file is None), use_container_width=True)

# ── Pipeline execution ───────────────────────────────────────────────────────
if run_clicked and txt_file is not None:
    # Reset previous results
    for key in ("peaks_df", "classification", "toxicity_df", "do_array",
                "cls_name", "cls_pred", "cls_prob"):
        st.session_state[key] = None
    st.session_state.cls_error = None  # classification error detail

    # Write to temp file (spec Decision #7)
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    try:
        txt_file.seek(0)
        tmp.write(txt_file.read())
        tmp.close()
        tmp_path = tmp.name

        with st.spinner("Đang phân tích..."):
            # 1. Parse raw signal for chart
            try:
                raw = pd.read_csv(tmp_path, sep="\t", header=None,
                                  usecols=[0, 1], names=["Time", "DO"],
                                  encoding="utf-16")
            except UnicodeError:
                time_list, do_list = [], []
                with open(tmp_path, "r") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                time_list.append(float(parts[0].replace("\x00", "")))
                                do_list.append(float(parts[1].replace("\x00", "")))
                            except ValueError:
                                continue
                raw = pd.DataFrame({"Time": time_list, "DO": do_list})

            if raw.empty or len(raw) < 2:
                st.error("File không đọc được. Kiểm tra định dạng UTF-16.")
                st.stop()

            st.session_state.do_array = raw["DO"].values
            st.session_state.signal_points = len(raw)
            st.session_state.do_min = float(raw["DO"].min())
            st.session_state.do_max = float(raw["DO"].max())
            st.session_state.sample_name = os.path.basename(txt_file.name).replace(".txt", "").strip()

            # 2. Peak extraction
            peaks_df = extract_peaks_from_txt(tmp_path)
            for col in ("Doin (mV)", "No.peak", "DOmin (mV)", "DDO (mV)"):
                peaks_df[col] = pd.to_numeric(peaks_df[col], errors="coerce")
            st.session_state.peaks_df = peaks_df

            # 3. Classification
            if len(peaks_df) > 0:
                try:
                    results = catboost_inference_from_csv(
                        peaks_df,
                        model_path="model/catboost_model.cbm",
                        label_encoder_path="model/label_encoder_classes.npy",
                    )
                    name, pred, prob = results[0]
                    st.session_state.cls_name = name
                    st.session_state.cls_pred = str(pred)
                    st.session_state.cls_prob = float(prob.max())
                except Exception as e:
                    st.session_state.cls_pred = "Lỗi phân loại"
                    st.session_state.cls_prob = 0.0
                    st.session_state.cls_name = st.session_state.sample_name
                    st.session_state.cls_error = str(e)

            # 3.5 Phase boundary detection (rewrite Tag column)
            if len(peaks_df) > 0:
                try:
                    peaks_df = update_phase_tags(
                        peaks_df,
                        st.session_state.cls_pred or 'GGA'
                    )
                    st.session_state.peaks_df = peaks_df  # refresh stored df
                except Exception as e:
                    # Non-fatal: keep peaks_df as-is, toxicity will fallback to BOD10/BOD5
                    st.session_state.phase_error = str(e)

            # 4. Toxicity
            if len(peaks_df) > 0:
                st.session_state.toxicity_df = calculate_toxicity(peaks_df)

        st.session_state.ran = True

    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  RESULTS DISPLAY (only after pipeline has run)
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.ran and st.session_state.peaks_df is not None:
    peaks_df = st.session_state.peaks_df

    # ── Handle 0 peaks ───────────────────────────────────────────────────
    if len(peaks_df) == 0:
        st.markdown('<p class="warn-msg">⚠️ Không phát hiện peak. Kiểm tra dữ liệu đầu vào.</p>',
                    unsafe_allow_html=True)
        # Still show signal chart
        if st.session_state.do_array is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=st.session_state.do_array, mode="lines",
                                     line=dict(color="#3b82f6", width=1.5),
                                     name="DO Signal"))
            fig.update_layout(title="DO Signal / Tín hiệu DO",
                              yaxis_title="DO (mV)", xaxis_title="Data Point",
                              template="plotly_white", height=350)
            st.plotly_chart(fig, use_container_width=True)
        st.stop()

    # ── Summary cards ────────────────────────────────────────────────────
    tag_counts = peaks_df["Tag"].value_counts()
    bod_str = " · ".join(f"{count} {tag}" for tag, count in tag_counts.items())

    tox_row = st.session_state.toxicity_df.iloc[0] if st.session_state.toxicity_df is not None and len(st.session_state.toxicity_df) > 0 else None
    tox_val = tox_row["Toxicity (%)"] if tox_row is not None and tox_row["Toxicity (%)"] is not None and pd.notna(tox_row["Toxicity (%)"]) else None
    stage1_tag = tox_row["Stage 1"] if tox_row is not None else None
    stage2_tag = tox_row["Stage 2"] if tox_row is not None else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Số Peak", len(peaks_df), help=bod_str)
        st.caption(bod_str)
    with c2:
        pred_label = st.session_state.cls_pred or "—"
        prob_pct = f"{st.session_state.cls_prob * 100:.1f}%" if st.session_state.cls_prob else "—"
        st.metric("Phân loại", pred_label, help=f"Xác suất: {prob_pct}")
        st.caption(f"Xác suất: {prob_pct}")
        if st.session_state.cls_error:
            with st.expander("Chi tiết lỗi"):
                st.code(st.session_state.cls_error)
    with c3:
        tox_display = f"{tox_val}%" if tox_val is not None else "N/A"
        st.metric("Độ độc / Toxicity", tox_display)
        if stage1_tag and stage2_tag:
            st.caption(f"Stage 1: {stage1_tag} · Stage 2: {stage2_tag}")
        elif tox_val is None:
            st.caption("Cần ít nhất 2 loại Tag (BOD5 + BOD10)")
    with c4:
        st.metric("Tín hiệu DO", f"{st.session_state.signal_points:,} pts")
        st.caption(f"{st.session_state.do_min:.2f} – {st.session_state.do_max:.2f} mV")

    # DDO range text
    ddo_min = peaks_df["DDO (mV)"].min()
    ddo_max = peaks_df["DDO (mV)"].max()
    st.markdown(f"**DDO Range:** {ddo_min:.2f} – {ddo_max:.2f} mV")
    st.markdown("---")

    # Phase detection confidence warning
    if "phase_confidence" in peaks_df.columns:
        non_t = peaks_df[peaks_df["Tag"].isin(["phase1", "phase2"])]
        if not non_t.empty:
            mean_conf = float(non_t["phase_confidence"].mean())
            if mean_conf < 0.6:
                st.markdown(
                    f'<p class="warn-msg">⚠️ Phase detection confidence thấp '
                    f'({mean_conf:.2f}). Kết quả toxicity có thể không chính xác.</p>',
                    unsafe_allow_html=True,
                )

    # ── Signal chart ─────────────────────────────────────────────────────
    if st.session_state.do_array is not None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=st.session_state.do_array, mode="lines",
            line=dict(color="#3b82f6", width=1.5), name="DO Signal",
        ))
        fig.update_layout(
            title="📈 DO Signal / Tín hiệu DO",
            yaxis_title="DO (mV)",
            xaxis_title="Data Point",
            template="plotly_white",
            height=380,
            margin=dict(l=60, r=20, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Detail: Peaks Table (2/3) + Toxicity Panel (1/3) ────────────────
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("📋 Bảng chi tiết Peak")
        display_df = peaks_df[["No.peak", "Tag", "Doin (mV)", "DOmin (mV)", "DDO (mV)"]].copy()

        def _color_tag(row):
            tag = str(row.get("Tag", "")).strip().lower()
            if tag == "phase1" or "bod10" in tag:
                return ["background-color: #FEF9C3"] * len(row)  # yellow
            if tag == "transition":
                return ["background-color: #FECACA"] * len(row)  # light red
            if tag == "phase2" or "bod5" in tag:
                return ["background-color: #DBEAFE"] * len(row)  # blue
            return [""] * len(row)

        styled = (
            display_df.style
            .apply(_color_tag, axis=1)
            .format({"Doin (mV)": "{:.2f}", "DOmin (mV)": "{:.2f}", "DDO (mV)": "{:.2f}"})
        )
        st.dataframe(styled, use_container_width=True, height=400)

    with right_col:
        st.subheader("🧪 Chi tiết độ độc")

        # Stage 1
        if stage1_tag:
            s1_peaks = peaks_df[peaks_df["Tag"].str.strip() == stage1_tag.strip()]
            s1_ddo = s1_peaks["DDO (mV)"].mean() if not s1_peaks.empty else None
            s1_ddo_str = f"{s1_ddo:.2f}" if s1_ddo is not None else "N/A"
            st.markdown(f"""<div class="stage-card">
                <div style="color:#166534;font-size:12px;font-weight:600;">STAGE 1 ({stage1_tag})</div>
                <div style="font-size:20px;font-weight:700;color:#15803d;">DDO = {s1_ddo_str} mV</div>
                <div style="color:#64748b;font-size:12px;">{len(s1_peaks)} peak(s) trung bình</div>
            </div>""", unsafe_allow_html=True)
        else:
            s1_ddo = None
            st.markdown('<div class="stage-card"><em>Không có Stage 1</em></div>', unsafe_allow_html=True)

        # Stage 2
        if stage2_tag:
            s2_peaks = peaks_df[peaks_df["Tag"].str.strip() == stage2_tag.strip()]
            s2_ddo = s2_peaks["DDO (mV)"].mean() if not s2_peaks.empty else None
            s2_ddo_str = f"{s2_ddo:.2f}" if s2_ddo is not None else "N/A"
            st.markdown(f"""<div class="stage-card">
                <div style="color:#1e40af;font-size:12px;font-weight:600;">STAGE 2 ({stage2_tag})</div>
                <div style="font-size:20px;font-weight:700;color:#1d4ed8;">DDO = {s2_ddo_str} mV</div>
                <div style="color:#64748b;font-size:12px;">{len(s2_peaks)} peak(s) trung bình</div>
            </div>""", unsafe_allow_html=True)
        else:
            s2_ddo = None
            st.markdown('<div class="stage-card"><em>Không có Stage 2</em></div>', unsafe_allow_html=True)

        # Toxicity result
        st.markdown(f"""<div class="tox-result">
            <div style="color:#92400e;font-size:12px;font-weight:600;">TOXICITY</div>
            <div style="font-size:28px;font-weight:800;color:#a16207;">
                {f'{tox_val}%' if tox_val is not None else 'N/A'}
            </div>
            <div style="color:#78350f;font-size:11px;">(DDO₁ - DDO₂) / DDO₁ × 100</div>
        </div>""", unsafe_allow_html=True)

        # ── Excel export ─────────────────────────────────────────────────
        st.markdown("---")
        excel_buf = generate_excel_report(
            sample_name=st.session_state.sample_name or "Unknown",
            peaks_df=peaks_df,
            classification=st.session_state.cls_pred or "N/A",
            probability=st.session_state.cls_prob or 0.0,
            toxicity_pct=tox_val,
            stage1_tag=stage1_tag,
            stage1_ddo_avg=s1_ddo,
            stage2_tag=stage2_tag,
            stage2_ddo_avg=s2_ddo,
            signal_points=st.session_state.signal_points or 0,
            do_min=st.session_state.do_min or 0.0,
            do_max=st.session_state.do_max or 0.0,
        )
        st.download_button(
            label="📥 Xuất Excel Report",
            data=excel_buf,
            file_name=f"VHL_Report_{st.session_state.sample_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

elif st.session_state.ran is None:
    st.info("📁 Upload file .txt rồi nhấn **▶ Phân tích** để bắt đầu.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("VHL Biology Analysis · Powered by Streamlit · v1.1.0")
