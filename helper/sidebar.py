import pandas as pd
import streamlit as st

from helper.llm import create_llm


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
        on_change=create_llm,
        label_visibility="collapsed",
    )


def sidebar_tools_selection():
    if "tools_info" not in st.session_state:
        st.session_state["tools_info"] = pd.read_csv("metadata/tools_list.csv")
        st.session_state["tools_info"]["Make available to LLM"] = True

    st.session_state["selected_tools"] = st.data_editor(
        st.session_state["tools_info"],
        column_config={
            "Make available to LLM": st.column_config.CheckboxColumn(
                "Make available to LLM"
            )
        },
        disabled=[
            col
            for col in st.session_state["tools_info"].columns
            if col != "Make available to LLM"
        ],
        hide_index=True,
    )


def sidebar_viz_tools_selection():
    if "viz_tools_info" not in st.session_state:
        st.session_state["viz_tools_info"] = pd.read_csv(
            "metadata/visualization_tools_list.csv"
        )
        st.session_state["viz_tools_info"]["Make available to LLM"] = True

    st.session_state["selected_viz_tools"] = st.data_editor(
        st.session_state["viz_tools_info"],
        column_config={
            "Make available to LLM": st.column_config.CheckboxColumn(
                "Make available to LLM"
            )
        },
        disabled=[
            col
            for col in st.session_state["viz_tools_info"].columns
            if col != "Make available to LLM"
        ],
        hide_index=True,
    )
