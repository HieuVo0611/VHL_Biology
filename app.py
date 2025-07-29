import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from src.utils import process_and_predict_lstm, catboost_inference_from_csv, calculate_toxicity, extract_metadata_single_sample

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
st.markdown('<div class="subtitle">Upload .txt and .excel files to perform LSTM prediction, classification, and toxicity calculation.</div>', unsafe_allow_html=True)
st.markdown("---")

# Initialize session state for file storage
if 'txt_file' not in st.session_state:
    st.session_state.txt_file = None
if 'excel_file' not in st.session_state:
    st.session_state.excel_file = None
if 'sample_name' not in st.session_state:
    st.session_state.sample_name = None

# Button 1: File Upload Section
st.subheader("1. Upload Sample Files")
col1, col2 = st.columns(2)

with col1:
    txt_file = st.file_uploader("Upload .txt file", type=["txt"])
    if txt_file:
        st.session_state.txt_file = txt_file
        st.markdown('<div class="success">.txt file uploaded successfully!</div>', unsafe_allow_html=True)

with col2:
    excel_file = st.file_uploader("Upload .excel file", type=["xlsx"])
    if excel_file:
        st.session_state.excel_file = excel_file
        st.markdown('<div class="success">.excel file uploaded successfully!</div>', unsafe_allow_html=True)

# Save uploaded files temporarily
if st.session_state.txt_file:
    with open("temp.txt", "wb") as f:
        f.write(st.session_state.txt_file.read())
    st.session_state.sample_name = st.session_state.txt_file.name
if st.session_state.excel_file:
    with open("temp.xlsx", "wb") as f:
        f.write(st.session_state.excel_file.read())

# Check if both files are uploaded
if st.session_state.txt_file and st.session_state.excel_file:
    st.markdown('<div class="success">Both files uploaded. Ready to proceed!</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="error">Please upload both .txt and .excel files to proceed.</div>', unsafe_allow_html=True)

st.markdown("---")

# Button 2: LSTM Prediction
st.subheader("2. LSTM Prediction (DO Values)")
if st.button("Run LSTM Prediction", disabled=not st.session_state.txt_file):
    try:
        # Run LSTM prediction
        fig = process_and_predict_lstm(
            txt_file_path="temp.txt",
            model_path="model/LSTM Model/28_07_2025/enc-dec_lstm_model.h5",
            lookback=7,
            train_size=0.6,
            val_size=0.2
        )
        # Customize plot colors
        fig.update_traces(line_color="#388E3C", selector=dict(name="Actual"))  # Green for Actual
        fig.update_traces(line_color="#0288D1", selector=dict(name="Predicted"))  # Blue for Predicted
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('<div class="success">LSTM Prediction completed!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in LSTM Prediction: {str(e)}</div>', unsafe_allow_html=True)

st.markdown("---")

# Button 3: Classification (GGA or GGA-metal)
st.subheader("3. Classification (GGA or GGA-metal)")
if st.button("Run Classification", disabled=not st.session_state.excel_file):
    try:
        # Extract metadata from Excel
        metadata_df = extract_metadata_single_sample("temp.xlsx")
        for col in ['Doin (mV)', 'No.peak', 'DOmin (mV)', 'DDO (mV)']:
            metadata_df[col] = pd.to_numeric(metadata_df[col], errors='coerce')
        
        # Run CatBoost inference
        results = catboost_inference_from_csv(
            metadata_df,
            model_path="model/catboost_model.cbm",
            label_encoder_path="model/label_encoder_classes.npy"
        )
        
        # Display results
        for name, pred, prob in results:
            st.markdown(f"**Sample**: {name} | **Prediction**: {pred} | **Probability**: {prob.max():.3f}")
        st.markdown('<div class="success">Classification completed!</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="error">Error in Classification: {str(e)}</div>', unsafe_allow_html=True)

st.markdown("---")

# Button 4: Toxicity Calculation
st.subheader("4. Toxicity Calculation")
if st.button("Calculate Toxicity", disabled=not st.session_state.excel_file):
    try:
        # Extract metadata from Excel
        metadata_df = extract_metadata_single_sample("temp.xlsx")
        
        # Calculate toxicity
        toxicity_df = calculate_toxicity(metadata_df)
        
        # Display results
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