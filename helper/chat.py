import inspect
import streamlit as st

from helper.tools import get_world_bank  # need for the function definition displays
from helper.viz_tools import gen_plot  # need for the function definition displays


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
    st.markdown(result["explanation"]["explanation"])


def display_commentary(result):
    st.markdown(
        f'### Analysis and commentary\n\n{result["commentary"]["commentary"]}'.replace(
            "$", "\\$"
        )
    )


def display_viz(result):
    st.markdown("### Visualization")
    try:
        st.pyplot(result["plots"]["invoked_result"][0])
    except:
        st.markdown("There was an error generating the plot.")


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
                if (
                    len(
                        st.session_state["selected_wb_series"].loc[
                            lambda x: x["Make available to LLM"] == True, :
                        ]
                    )
                    > 0
                ):
                    wb_context = "\n\n Here are some World Bank indicators that may be relevant to the user's question:\n\n" + st.session_state[
                        "selected_wb_series"
                    ].loc[
                        lambda x: x["Make available to LLM"] == True, :
                    ].reset_index(
                        drop=True
                    ).to_markdown(
                        index=False
                    )
                else:
                    wb_context = None

                # wb indicator list step
                st.session_state["prior_query_id"] = st.session_state["llm"].chat(
                    prompt=prompt,
                    tools=st.session_state["tools"],
                    plot_tools=st.session_state["viz_tools"],
                    validate=True,
                    use_free_plot=st.session_state["use_free_plot"],
                    prior_query_id=st.session_state["prior_query_id"],
                    addt_context_gen_tool_call=wb_context,
                )["tool_result"]["query_id"]

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
        st.info(
            "**Note**, you must either specificy the code of the World Bank indicator(s) you would like to query directly in your prompt (e.g., `SP.POP.TOTL`), or select them in the `WB indicators` table in the sidebar."
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
