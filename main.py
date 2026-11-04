"""Streamlit entry point: python -m streamlit run main.py."""
import streamlit as st

from dashboard_windows import render


def main():
    st.set_page_config(page_title="Community Notes Explorer", page_icon="📊", layout="wide")
    render()


if __name__ == "__main__":
    main()
