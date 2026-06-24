import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from src.utils import (
    process_and_predict_lstm,
    catboost_inference_from_csv,
    calculate_toxicity,
    extract_peaks_from_txt,
)

# Streamlit page configuration
st.set_page_config(page_title="Bio Data Analysis", layout="wide", page_icon="📊")

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .title { color: #2E4053; font-size: 2.5em; font-weight: bold; }
    .subtitle { color: #566573; font-size: 1.5em; }
    .error { color: #D32F2F; font-weight: bold; }
    .success { color: #388E3C; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.markdown('<div class="title">Bio Data Analysis Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Upload a .txt file to perform LSTM prediction, classification, and toxicity calculation.</div>', unsafe_allow_html=True)
st.markdown("---")

# Initialize session state
if 'txt_file' not in st.session_state:
    st.session_state.txt_file = None
if 'sample_name' not in st.session_state:
    st.session_state.sample_name = None
if 'peaks_df' not in st.session_state:
    st.session_state.peaks_df = None

# ── Step 1: File Upload ──────────────────────────────────────────────────────
st.subheader("1. Upload Sample File")

txt_file = st.file_uploader("Upload .txt file (UTF-16, Time/DO columns)", type=["txt"])
if txt_file:
    st.session_state.txt_file = txt_file
    st.session_state.sample_name = txt_file.name
    # Reset extracted peaks when new file uploaded
    st.session_state.peaks_df = None
    st.markdown('<div class="success">.txt file uploaded successfully!</div>', unsafe_allow_html=True)

# Save uploaded file temporarily
if st.session_state.txt_file:
    with open("temp.txt", "wb") as f:
        st.session_state.txt_file.seek(0)
        f.write(st.session_state.txt_file.read())
    st.markdown('<div class="success">File ready. Proceed with analysis.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="error">Please upload a .txt file to proceed.</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Step 2: Peak Extraction (from TXT) ──────────────────────────────────────
st.subheader("2. DO Peak Extraction")
if st.button("Extract Peaks", disabled=not st.session_state.txt_file):
    try:
        with st.spinner("Extracting DO peaks from signal..."):
            peaks_df = extract_peaks_from_txt("temp.txt")

        if len(peaks_df) == 0:
            st.markdown('<div class="error">No peaks detected in the signal. Check data quality.</div>', unsafe_allow_html=True)
        else:
            # Ensure numeric types for downstream
            for col in ['Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)']:
                peaks_df[col] = pd.to_numeric(peaks_df[col], errors='coerce')

            st.session_state.peaks_df = peaks_df
            st.markdown(f'<div class="success">Extracted {len(peaks_df)} peaks!</div>', unsafe_allow_html=True)
            st.dataframe(peaks_df, use_container_width=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in Peak Extraction: {str(e)}</div>', unsafe_allow_html=True)

# Show previously extracted peaks if available
if st.session_state.peaks_df is not None and not st.button("_hidden", disabled=True, key="noop"):
    pass  # peaks_df persists in session state for downstream steps

st.markdown("---")

# ── Step 3: LSTM Prediction ─────────────────────────────────────────────────
st.subheader("3. LSTM Prediction (DO Values)")
if st.button("Run LSTM Prediction", disabled=not st.session_state.txt_file):
    try:
        fig = process_and_predict_lstm(
            txt_file_path="temp.txt",
            model_path="model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5",
            lookback=7,
            train_size=0.6,
            val_size=0.2
        )
        fig.update_traces(line_color="#388E3C", selector=dict(name="Actual"))
        fig.update_traces(line_color="#0288D1", selector=dict(name="Predicted"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('<div class="success">LSTM Prediction completed!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in LSTM Prediction: {str(e)}</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Step 4: Classification ──────────────────────────────────────────────────
st.subheader("4. Classification (GGA or GGA-metal)")
if st.button("Run Classification", disabled=st.session_state.peaks_df is None):
    try:
        results = catboost_inference_from_csv(
            st.session_state.peaks_df,
            model_path="model/catboost_model.cbm",
            label_encoder_path="model/label_encoder_classes.npy"
        )
        for name, pred, prob in results:
            st.markdown(f"**Sample**: {name} | **Prediction**: {pred} | **Probability**: {prob.max():.3f}")
        st.markdown('<div class="success">Classification completed!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in Classification: {str(e)}</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Step 5: Toxicity Calculation ─────────────────────────────────────────────
st.subheader("5. Toxicity Calculation")
if st.button("Calculate Toxicity", disabled=st.session_state.peaks_df is None):
    try:
        toxicity_df = calculate_toxicity(st.session_state.peaks_df)
        for _, row in toxicity_df.iterrows():
            if row['Toxicity (%)'] is not None:
                st.markdown(f"**Sample**: {row['Sample Name']} | **Toxicity**: {row['Toxicity (%)']}%")
            else:
                st.markdown(f"**Sample**: {row['Sample Name']} | **Toxicity**: Not available (insufficient stage data)")
        st.markdown('<div class="success">Toxicity calculation completed!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in Toxicity Calculation: {str(e)}</div>', unsafe_allow_html=True)

st.markdown("---")

# Footer
st.markdown('<div class="subtitle">Developed for Bio Data Analysis | Powered by Streamlit</div>', unsafe_allow_html=True)
