import inspect
import streamlit as st

from helper.tools import get_world_bank
from helper.viz_tools import gen_plot


def display_tool_call(result):
    tool_calls = result["tool_result"]["tool_call"]
    text = ""
    for i in range(len(tool_calls)):
        text += f"### Function call {i+1}\n\n"
        text += f'Name: `{tool_calls[i]["name"]}`\n\n'
        text += f'Arguments: `{tool_calls[i]["arguments"]}`\n\n'
        text += "Definition:\n\n"
        text += (
            "```py\n\n"
            + inspect.getsource(globals()[tool_calls[i]["name"]].func)
            + "\n\n```\n\n"
        )

    st.markdown(text)


def display_pd_code(result):
    text = "### Data description provided to the LLM\n\n"
    text += result["pd_code"]["data_desc"]

    text += "\n\n### Python code run by the LLM\n\n```py\n"

    text += result["pd_code"]["pd_code"]
    text += "\n```"

    st.markdown(text)


def display_dataset(result):
    st.dataframe(result["dataset"], hide_index=True)


def display_explanation(result):
    st.markdown(result["explanation"])


def display_commentary(result):
    st.markdown(
        f'### Analysis and commentary\n\n{result["commentary"]}'.replace("$", "\\$")
    )


def display_viz(result):
    st.markdown("### Visualization")
    st.pyplot(result["plots"]["invoked_result"][0])


def display_llm_output(result):
    # foldout for initial tool call
    with st.expander("Initial data call", expanded=False):
        display_tool_call(result)

    # foldout for pandas code
    with st.expander("Python data manipulation", expanded=False):
        display_pd_code(result)

    # foldout for actual dataset
    with st.expander("Final dataset", expanded=False):
        display_dataset(result)

    # foldout for explanation
    with st.expander("Data manipulation explanation", expanded=False):
        display_explanation(result)

    # analysis/commentary
    display_commentary(result)

    # visualization
    display_viz(result)


def user_question():
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    if prompt := st.chat_input("Enter question"):
        with st.chat_message(
            "user", avatar="https://www.svgrepo.com/show/524211/user.svg"
        ):
            st.markdown(prompt)

        with st.chat_message(
            "assistant", avatar="https://www.svgrepo.com/show/375527/ai-platform.svg"
        ):
            with st.spinner("Processing your query...", show_time=True):
                try:
                    st.session_state["prior_query_id"] = st.session_state["llm"].chat(
                        prompt=prompt,
                        tools=st.session_state["tools"],
                        plot_tools=st.session_state["viz_tools"],
                        validate=True,
                        use_free_plot=st.session_state["use_free_plot"],
                        prior_query_id=st.session_state["prior_query_id"],
                    )["tool_result"]["query_id"]
                except:
                    st.error(
                        "There was an error processing your request. Try reformulating your question."
                    )

            # LLM response
            display_llm_output(
                st.session_state["llm"]._query_results[
                    st.session_state["prior_query_id"]
                ]
            )

        # add prompt to chat history
        st.session_state["chat_history"].append({"role": "user", "content": prompt})

        # add response to chat history
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": st.session_state["prior_query_id"]}
        )


def populate_chat():
    st.session_state["message_box"] = st.empty()

    empty_chat = False
    if "chat_history" not in st.session_state:
        empty_chat = True
    elif len(st.session_state["chat_history"]) == 0:
        empty_chat = True
    elif len(st.session_state["llm"]._query_results) == 0:
        empty_chat = True

    if empty_chat:
        st.markdown(
            """<div class="icon_text"><img width=50 src='https://www.svgrepo.com/show/375527/ai-platform.svg'></div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="icon_text"<h4>What would you like to know?</h4></div>""",
            unsafe_allow_html=True,
        )
    else:
        with st.session_state["message_box"].container():
            for i in range(len(st.session_state["chat_history"])):
                # user
                if st.session_state["chat_history"][i]["role"] == "user":
                    with st.chat_message(
                        st.session_state["chat_history"][i]["role"],
                        avatar="https://www.svgrepo.com/show/524211/user.svg",
                    ):
                        st.markdown(st.session_state["chat_history"][i]["content"])
                else:  # assistant
                    with st.chat_message(
                        st.session_state["chat_history"][i]["role"],
                        avatar="https://www.svgrepo.com/show/375527/ai-platform.svg",
                    ):
                        display_llm_output(
                            st.session_state["llm"]._query_results[
                                st.session_state["chat_history"][i]["content"]
                            ]
                        )
