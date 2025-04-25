import inspect
import streamlit as st

from helper.tools import get_world_bank
from helper.viz_tools import gen_plot
from helper.wb import get_wb_indicator_list


def display_tool_call(result):
    tool_calls = result["tool_result"]["tool_call"]
    for i in range(len(tool_calls)):
        text = ""
        text += f"### Function call {i+1}\n\n"
        text += f'Name: `{tool_calls[i]["name"]}`\n\n'
        text += f'Arguments: `{tool_calls[i]["arguments"]}`\n\n'
        st.markdown(text)

        text = "Definition:"
        hover_text = (
            "```py\n\n"
            + inspect.getsource(globals()[tool_calls[i]["name"]].func)
            + "\n\n```\n\n"
        )
        st.markdown(text, help=hover_text)


def display_pd_code(result):
    st.markdown(
        "### Description of data given to LLM:", help=result["pd_code"]["data_desc"]
    )
    text = "\n\n### Python code run by the LLM\n\n```py\n"

    text += result["pd_code"]["pd_code"]
    text += "\n```"

    st.markdown(text)


def display_dataset(result):
    st.dataframe(result["dataset"], hide_index=True)


def display_viz_call(result):
    if st.session_state["use_free_plot"]:
        st.markdown(f'```py\n\n{result["plots"]["visualization_call"][0]}\n\n```')
    else:
        text = f'Name: `{result["plots"]["visualization_call"][0]["name"]}`\n\n'
        text += (
            f'Arguments: `{result["plots"]["visualization_call"][0]["arguments"]}`\n\n'
        )
        st.markdown(text)

        hover_text = (
            "```py\n\n"
            + inspect.getsource(
                globals()[result["plots"]["visualization_call"][0]["name"]].func
            )
            + "\n\n```\n\n"
        )

        st.markdown("Definition:", help=hover_text)


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
    # analysis/commentary
    display_commentary(result)

    # visualization
    display_viz(result)

    # foldout for initial tool call
    with st.expander("Initial data call", expanded=False):
        try:
            display_tool_call(result)
        except:
            st.error(
                "An error was encountered during the initial data call step. Please try reformulating your query."
            )

    # foldout for pandas code
    with st.expander("Python data manipulation", expanded=False):
        try:
            display_pd_code(result)
        except:
            st.error(
                "An error was encountered during the code manipulation step. Please try reformulating your query."
            )

    # foldout for actual dataset
    with st.expander("Final dataset", expanded=False):
        try:
            display_dataset(result)
        except:
            st.error(
                "An error was encountered during the final dataset step. Please try reformulating your query."
            )

    # foldout for viz call
    with st.expander("Visualization call", expanded=False):
        try:
            display_viz_call(result)
        except:
            st.error(
                "An error was encountered during the visualization step. Please try reformulating your query."
            )

    # foldout for explanation
    with st.expander("Data manipulation explanation", expanded=False):
        try:
            display_explanation(result)
        except:
            st.error(
                "An error was encountered during the data explanation step. Please try reformulating your query."
            )


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
                # wb indicator list step
                try:
                    if "wb_indicator_key" not in st.session_state:
                        st.session_state["wb_indicator_key"] = get_wb_indicator_list()

                    if st.session_state["prior_query_id"] is not None:
                        prior_query_ids = [
                            st.session_state["prior_query_id"]
                        ] + st.session_state["llm"]._query_results[
                            st.session_state["prior_query_id"]
                        ][
                            "context_query_ids"
                        ]
                        complete_responses = [
                            st.session_state["llm"]._query_results[_]
                            for _ in prior_query_ids
                        ]

                        condense_query = f"Given this new question: '{prompt}'\n\nAnd these prior exchanges:\n\n"
                        for i in range(len(complete_responses)):
                            condense_query += f"""Question: '{complete_responses[i]["initial_prompt"]}'\n\n"""
                            condense_query += f"""Answer: '{complete_responses[i]["commentary"]}'\n\n"""

                        condense_query += "Output a query that can stand alone without further context."

                        condensed_prompt = st.session_state["llm"](condense_query)
                    else:
                        condensed_prompt = prompt

                    wb_prompt = f"Given this question:\n\n'{condensed_prompt}'\n\n return a list of one or more keywords that could be relevant to it in a search of the World Bank database for relevant indicators. Include different formulations as well as words in isolation as well as in phrases. Rather include too many keywords than too few. Return your answer in the form of a comma-separated list of keywords."
                    substrings = st.session_state["llm"](wb_prompt)
                    substrings = [_.lower().strip() for _ in substrings.split(",")]

                    wb_context = (
                        f"\n\n Here are some World Bank indicators that may be relevant to the user's question:\n\n"
                        + (
                            st.session_state["wb_indicator_key"]
                            .loc[
                                lambda x: x["name"]
                                .str.lower()
                                .str.contains(
                                    "|".join(substrings), na=False, regex=True
                                ),
                                :,
                            ]
                            .reset_index(drop=True)
                            .to_markdown(index=False)
                        )
                    )
                except:
                    wb_context = None
                # wb indicator list step

                try:
                    st.session_state["prior_query_id"] = st.session_state["llm"].chat(
                        prompt=prompt,
                        tools=st.session_state["tools"],
                        plot_tools=st.session_state["viz_tools"],
                        validate=True,
                        use_free_plot=st.session_state["use_free_plot"],
                        prior_query_id=st.session_state["prior_query_id"],
                        addt_context_gen_tool_call=wb_context,
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
