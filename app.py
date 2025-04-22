import streamlit as st
import pandas as pd

from helper.ui import check_password
from helper.tools import get_world_bank

from llads.customLLM import customLLM
from llads.visualizations import gen_plot

st.set_page_config(
    page_title="Statschat",
    page_icon="https://www.svgrepo.com/show/273699/stats-chart.svg",
)


system_prompts = pd.read_csv(
    "https://raw.githubusercontent.com/dhopp1/llads/refs/heads/main/system_prompts.csv"
)

# creating LLM
st.session_state["llm"] = customLLM(
    api_key="",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    model_name="gemini-2.0-flash",
    temperature=0.0,
    max_tokens=4096,
    system_prompts=system_prompts,
)

tools = [get_world_bank]
plot_tools = [gen_plot]

# App title
st.title("UNCTAD Statschat")

if not check_password():
    st.stop()

# User input
title = st.text_input("What would you like to know?")

st.markdown("")

if title:
    try:
        with st.spinner("Processing your query..."):
            if "prior_query_id" not in st.session_state:
                st.session_state["prior_query_id"] = None
            st.session_state["prior_query_id"] = st.session_state["llm"].chat(
                prompt=title,
                tools=tools,
                plot_tools=plot_tools,
                validate=True,
                use_free_plot=True,
                prior_query_id=st.session_state["prior_query_id"],
            )["tool_result"]["query_id"]

            # explanation of data processing
            st.markdown("### Explanation of data processing")
            st.markdown(
                st.session_state["llm"]._query_results[
                    st.session_state["prior_query_id"]
                ]["explanation"]
            )

            ### show dataframe
            st.markdown("### Dataset")
            st.dataframe(
                st.session_state["llm"]._query_results[
                    st.session_state["prior_query_id"]
                ]["dataset"],
                hide_index=True,
            )

            # commentary
            st.markdown("### Commentary")
            st.markdown(
                st.session_state["llm"]
                ._query_results[st.session_state["prior_query_id"]]["commentary"]
                .replace("$", "\\$")
            )

            # plot
            st.markdown("### Visualization")
            st.pyplot(
                st.session_state["llm"]._query_results[
                    st.session_state["prior_query_id"]
                ]["plots"]["invoked_result"][0]
            )

            st.session_state["answer_up"] = True

    except Exception:
        st.error(
            "There was an error processing your request. Try reformulating your question."
        )
