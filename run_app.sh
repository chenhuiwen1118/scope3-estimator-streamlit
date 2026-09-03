#!/bin/bash
# Launch Streamlit Web UI for Scope 3 Estimator

echo "🚀 Starting Scope 3 Estimator Web UI..."
echo "================================"
echo ""
echo "The app will open in your browser at:"
echo "http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

# 設定離線模式 - 不訪問 Hugging Face Hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

streamlit run app.py
