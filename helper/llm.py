from llads.customLLM import customLLM
import pandas as pd
import streamlit as st


def create_llm(force=True):
    if (
        "system_prompts" not in st.session_state
        and "custom_system_prompt_df" not in st.session_state
    ):
        st.session_state["system_prompts"] = pd.read_csv(
            "https://raw.githubusercontent.com/dhopp1/llads/refs/heads/main/system_prompts.csv"
        )
    else:
        try:
            st.session_state["system_prompts"] = st.session_state[
                "custom_system_prompt_df"
            ]
        except:
            pass

    if "llm" not in st.session_state or force:
        st.session_state["llm"] = customLLM(
            api_key=st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "api_key"]
            .values[0],
            base_url=st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "llm_url"]
            .values[0],
            model_name=st.session_state["llm_info"]
            .loc[lambda x: x["name"] == st.session_state["selected_llm"], "model_name"]
            .values[0],
            temperature=0.0,
            max_tokens=4096,
            system_prompts=st.session_state["system_prompts"],
        )

        st.session_state["prior_query_id"] = None
