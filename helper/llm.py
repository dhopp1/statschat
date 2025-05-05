from llads.customLLM import customLLM
import pandas as pd
import streamlit as st


def create_llm(force=True):
    if (
        "system_prompts" not in st.session_state
        and "custom_system_prompt_df" not in st.session_state
    ):
        st.session_state["system_prompts"] = pd.read_csv("metadata/system_prompts.csv")
    else:
        try:
            st.session_state["system_prompts"] = st.session_state[
                "custom_system_prompt_df"
            ]
        except:
            pass

    if "llm" not in st.session_state or force:
        if "Gemini 2.5 Flash" in st.session_state["selected_llm"]:
            reasoning_effort = "none"
            if "Thinking" in st.session_state["selected_llm"]:
                reasoning_effort = "medium"
        else:
            reasoning_effort = None

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
            reasoning_effort=reasoning_effort,
            system_prompts=st.session_state["system_prompts"],
        )

        st.session_state["prior_query_id"] = None
