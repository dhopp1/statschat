import streamlit as st
import pandas as pd
import requests
import json

from helper.ui import check_password

# App title
st.title("UNCTAD Statschat")

if not check_password():
    st.stop()

llm_url = "https://generativelanguage.googleapis.com/v1beta/openai"
llm_api_key = "API_KEY"
llm_model_name = "gemini-2.0-flash"

# User input
title = st.text_input("What would you like to know?")
data = pd.read_csv("US_GDPTotal.csv")

if title:
    try:

        llm_api_url = llm_url + "/chat/completions"

        llm_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_api_key}",
        }

        ### data transformation question
        system_prompt = """
        The user will ask a question that can be answered by the data in a pandas dataframe called "data". The data contains various countries and economy groups, here is an example row:
        Year	Economy	Economy Label	US$ at current prices in millions	US$ at current prices in millions Footnote	US$ at current prices in millions Missing value	US$ at current prices per capita	US$ at current prices per capita Footnote	US$ at current prices per capita Missing value	US$ at constant prices (2015) in millions	US$ at constant prices (2015) in millions Footnote	US$ at constant prices (2015) in millions Missing value	US$ at constant prices (2015) per capita	US$ at constant prices (2015) per capita Footnote	US$ at constant prices (2015) per capita Missing value
        1970	0000	World	3681664.529			996.834	
        
        Write python code that will generate the data the user is interested in, the output should always be a dataframe, not a single number. Return only the data manipulation code, no printing of results. Don't output your answer in ```python``` tags. Put the new data in a variable called 'plot_data'.
        
        When they mention GDP, they are referring to the column 'US$ at constant prices (2015) in millions'. Put "Year" in the index, not as a column called "Year".
        
        If you make any calculations or transformations to the data, change the column name(s) to reflect what the new data is showing.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title},
        ]

        llm_data = {
            "model": llm_model_name,
            "temperature": 0.0,
            "max_tokens": 512,
            "messages": messages,
        }

        llm_response = requests.post(
            llm_api_url, headers=llm_headers, data=json.dumps(llm_data)
        )
        llm_answer = llm_response.json()["choices"][0]["message"]["content"]

        try:
            llm_answer = llm_answer.split("```python")[1].replace("```", "")
        except:
            pass

        exec(llm_answer)

        ### explanation of code question
        system_prompt = f"""
    Given this code, explain what it is doing very generally, not line by line, making note of original and new column names. The original question it is manipulating the data to answer is '{title}'. Here is the code: {llm_answer}
    """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title},
        ]

        llm_data = {
            "model": llm_model_name,
            "temperature": 0.0,
            "max_tokens": 512,
            "messages": messages,
        }

        llm_response = requests.post(
            llm_api_url, headers=llm_headers, data=json.dumps(llm_data)
        )
        code_explanation = llm_response.json()["choices"][0]["message"]["content"]
        st.markdown("### Explanation of data processing")
        st.markdown(code_explanation)

        ### download button
        st.download_button(
            "Download the data",
            plot_data.to_csv().encode("utf-8"),
            "data.csv",
            "text/csv",
            key="download-csv",
        )

        ### plot question
        system_prompt = f"""
    Create a matplotlib plot with fig, ax syntax that visualizes the data in the already existing dataframe 'plot_data' in a way that answers the question '{title}'. Here is an example of how the data looks:
        
    {str(plot_data.tail())}
    
    Include only the code, no introdudction or conclusion. Don't output your answer in ```python``` tags. Don't include plot.show(), just generate the fig, and ax objects. Assume the 'plot_data' dataframe already exists, don't create any sample data.
    """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title},
        ]

        llm_data = {
            "model": llm_model_name,
            "temperature": 0.0,
            "max_tokens": 512,
            "messages": messages,
        }

        llm_response = requests.post(
            llm_api_url, headers=llm_headers, data=json.dumps(llm_data)
        )
        llm_answer = llm_response.json()["choices"][0]["message"]["content"]

        try:
            llm_answer = llm_answer.split("```python")[1].replace("```", "")
        except:
            pass

        exec(llm_answer)

        ### commentary question
        system_prompt = f"""
    Provide some brief but useful commentary on the following dataset that answers this question: {title}:
        
    {str(plot_data)}
    """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": title},
        ]

        llm_data = {
            "model": llm_model_name,
            "temperature": 0.0,
            "max_tokens": 512,
            "messages": messages,
        }

        llm_response = requests.post(
            llm_api_url, headers=llm_headers, data=json.dumps(llm_data)
        )
        llm_answer = llm_response.json()["choices"][0]["message"]["content"]
        st.markdown("### Commentary")
        st.markdown(llm_answer)

        # plot
        st.pyplot(fig)

        st.session_state["answer_up"] = True

    except:
        st.error(
            "There was an error processing your request. Try reformulating your question."
        )
