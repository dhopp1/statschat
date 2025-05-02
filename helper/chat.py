import inspect
import pandas as pd
import streamlit as st
import sys

from helper.progress_bar import Logger
from helper.tools import (
    get_world_bank,
    get_unctadstat,
)  # need for the function definition displays
from helper.viz_tools import gen_plot  # need for the function definition displays


def df_to_string(df):
    """
    Converts a Pandas DataFrame to a single string using Row-by-Row Serialization.

    Args:
        df: The Pandas DataFrame to convert.

    Returns:
        A string representation of the DataFrame, with each row serialized
        and rows separated by a newline character.  NaN values are replaced
        with "NA".
    """

    def row_to_text(row):
        text = ""
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                value = "NA"
            text += f"{col}: {value}; "
        return text.strip()  # Remove trailing semicolon and space

    # Apply the function to each row and join the results with newlines
    return "\n\n".join(df.apply(row_to_text, axis=1).tolist())


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


def display_time_token(result):
    text = ""
    # initial tool call
    text += "### Initial data call\n"
    text += f"Seconds taken: `{round(result['tool_result']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['tool_result']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['tool_result']['n_tokens_output']}`\n\n"

    # pandas manipulation
    text += "### Python data manipulation\n"
    text += f"Seconds taken: `{round(result['pd_code']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['pd_code']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['pd_code']['n_tokens_output']}`\n\n"

    # explanation
    text += "### Data manipulation explanation\n"
    text += f"Seconds taken: `{round(result['explanation']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['explanation']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['explanation']['n_tokens_output']}`\n\n"

    # commentary
    text += "### Analysis/commentary\n"
    text += f"Seconds taken: `{round(result['commentary']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['commentary']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['commentary']['n_tokens_output']}`\n\n"

    # viz call
    text += "### Visualization call\n"
    text += f"Seconds taken: `{round(result['plots']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['plots']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['plots']['n_tokens_output']}`\n\n"

    # total
    text += "### Total process\n"
    text += f"Seconds taken: `{round(result['tool_result']['seconds_taken'] + result['pd_code']['seconds_taken'] + result['explanation']['seconds_taken'] + result['commentary']['seconds_taken'] + result['plots']['seconds_taken'], 2)}`\n\n"
    text += f"Input tokens: `{result['tool_result']['n_tokens_input'] + result['pd_code']['n_tokens_input'] + result['explanation']['n_tokens_input'] + result['commentary']['n_tokens_input'] + result['plots']['n_tokens_input']}`\n\n"
    text += f"Output tokens: `{result['tool_result']['n_tokens_output'] + result['pd_code']['n_tokens_output'] + result['explanation']['n_tokens_output'] + result['commentary']['n_tokens_output'] + result['plots']['n_tokens_output']}`\n\n"

    st.markdown(text)


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

    # foldout for time and tokens
    with st.expander("Time taken and token consumption", expanded=False):
        if True:  # try:
            display_time_token(result)
        else:  # except:
            st.error(
                "An error was encountered during the time and token step. Please try reformulating your query."
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
                    wb_context = (
                        "\n\n Here are some World Bank indicators that may be relevant to the user's question:\n\n"
                        + df_to_string(
                            st.session_state["selected_wb_series"]
                            .loc[lambda x: x["Make available to LLM"] == True, :]
                            .drop(columns=["Make available to LLM"])
                            .reset_index(drop=True)
                        )
                    )
                else:
                    wb_context = None
                # wb indicator list step
                # unctadstat indicator step
                if (
                    len(
                        st.session_state["selected_unctad_series"].loc[
                            lambda x: x["Make available to LLM"] == True, :
                        ]
                    )
                    > 0
                ):
                    unctad_context = (
                        "\n\n Here are some UNCTADstat indicators that may be relevant to the user's question:\n\n"
                        + df_to_string(
                            st.session_state["selected_unctad_series"]
                            .loc[lambda x: x["Make available to LLM"] == True, :]
                            .drop(columns=["Make available to LLM"])
                            .reset_index(drop=True)
                        )
                    )
                else:
                    unctad_context = None

                addt_context_gen_tool_call = (
                    f"{unctad_context}\n\n{wb_context}"
                    if unctad_context and wb_context
                    else unctad_context or wb_context or None
                )
                # unctadstat indicator step

                old_stdout = sys.stdout
                sys.stdout = Logger(st.progress(0), st.empty())

                st.session_state["prior_query_id"] = st.session_state["llm"].chat(
                    prompt=prompt,
                    tools=st.session_state["tools"],
                    plot_tools=st.session_state["viz_tools"],
                    validate=False,
                    use_free_plot=st.session_state["use_free_plot"],
                    prior_query_id=st.session_state["prior_query_id"],
                    addt_context_gen_tool_call=addt_context_gen_tool_call,
                )["tool_result"]["query_id"]

                try:
                    sys.stdout = sys.stdout.clear()
                    sys.stdout = old_stdout
                except:
                    pass

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
            """### UNCTADstat
For UNCTADstat indicators, select the ones you want available to the LLM in the `UNCTADstat indicators` table in the sidebar.

### World Bank
For World Bank indicators, either specify the indicator's code directly in your prompt (e.g., `SP.POP.TOTL`), or select them in the `WB indicators` table in the sidebar.
"""
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
