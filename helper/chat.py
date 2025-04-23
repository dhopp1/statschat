import streamlit as st


def display_tool_call(result):
    tool_calls = result["tool_result"]["tool_call"]
    text = ""
    for i in range(len(tool_calls)):
        text += f"Function call {i+1}\n\n"
        text += f'Name: `{tool_calls[i]["name"]}`\n\n'
        text += f'Arguments: `{tool_calls[i]["arguments"]}`\n\n'

    st.markdown(text)


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

            # organizing model output
            # foldout for initial tool call
            with st.expander("Initial data call", expanded=False):
                display_tool_call(
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
                        with st.expander("Initial data call", expanded=False):
                            display_tool_call(
                                st.session_state["llm"]._query_results[
                                    st.session_state["chat_history"][i]["content"]
                                ]
                            )
