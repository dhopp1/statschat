import pandas as pd
import streamlit as st


def sidebar_llm_dropdown():
    if "llm_info" not in st.session_state:
        st.session_state["llm_info"] = pd.read_csv("metadata/llm_list.csv")
        st.session_state["llm_dropdown_options"] = st.session_state["llm_info"]["name"]

    st.selectbox(
        "Select LLM",
        options=st.session_state["llm_dropdown_options"],
        index=2,
        help="Which LLM to use.",
        key="selected_llm",
    )
