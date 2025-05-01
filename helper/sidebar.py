import pandas as pd
import streamlit as st
import time

from helper.llm import create_llm
from helper.wb import get_wb_indicator_list


def upload_system_prompt():
    st.session_state["custom_system_prompt_df"] = pd.read_csv(
        st.session_state["custom_system_prompt_file"]
    )
    st.info("Custom system prompts successfully uploaded!")
    time.sleep(3)
    create_llm(force=True)


def sidebar_system_prompt_uploader():
    st.session_state["custom_system_prompt_file"] = st.file_uploader(
        "Upload your own system prompts",
        type=[".csv"],
        help="You can start with the file available [here](https://github.com/dhopp1/llads/blob/main/system_prompts.csv) and tweak it then reupload.",
    )
    st.button("Upload system prompts", on_click=upload_system_prompt)


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


def sidebar_wb_selection():
    if "wb_indicator_key" not in st.session_state:
        st.session_state["wb_indicator_key"] = get_wb_indicator_list()

    st.session_state["wb_indicator_key"]["Make available to LLM"] = False

    st.session_state["selected_wb_series"] = st.data_editor(
        st.session_state["wb_indicator_key"],
        column_config={
            "Make available to LLM": st.column_config.CheckboxColumn(
                "Make available to LLM"
            )
        },
        disabled=[
            col
            for col in st.session_state["wb_indicator_key"].columns
            if col != "Make available to LLM"
        ],
        hide_index=True,
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
