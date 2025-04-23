import streamlit as st
import pandas as pd

from helper.chat import populate_chat, user_question
from helper.llm import create_llm
from helper.sidebar import (
    sidebar_llm_dropdown,
    sidebar_tools_selection,
    sidebar_viz_tools_selection,
)
from helper.ui import check_password
from helper.tools import get_world_bank
from helper.viz_tools import gen_plot


st.set_page_config(
    page_title="Statschat",
    page_icon="https://www.svgrepo.com/show/273699/stats-chart.svg",
)


system_prompts = pd.read_csv(
    "https://raw.githubusercontent.com/dhopp1/llads/refs/heads/main/system_prompts.csv"
)

# App title
st.title("UNCTAD Statschat")

if not check_password():
    st.stop()

# sidebar
with st.sidebar:
    st.markdown("### Select LLM")
    sidebar_llm_dropdown()

    st.markdown("### Data available to LLM")
    sidebar_tools_selection()

    st.markdown("### Visualizations available to LLM")
    sidebar_viz_tools_selection()

    # setting tools and viz tools available to the LLM
    st.session_state["tools"] = [
        eval(_)
        for _ in list(
            st.session_state["selected_tools"]
            .loc[lambda x: x["Make available to LLM"] == True, "function_name"]
            .values
        )
    ]
    st.session_state["viz_tools"] = [
        eval(_)
        for _ in list(
            st.session_state["selected_viz_tools"]
            .loc[lambda x: x["Make available to LLM"] == True, "function_name"]
            .values
        )
    ]
    if len(st.session_state["viz_tools"]) == 0:
        st.session_state["use_free_plot"] = True
    else:
        st.session_state["use_free_plot"] = False

# create the LLM initially
create_llm(force=False)

# populate chat
populate_chat()

# User input
user_question()
