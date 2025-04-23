import pandas as pd
from langchain_core.tools import tool
import requests


@tool
def get_world_bank(
    country_code: str, indicator: str, start_year: int, end_year: int
) -> pd.DataFrame:
    """
    Fetch data from World Bank API for a specific country

    Parameters:
        country_code (str): ISO 3-letter country code, or 'all' for all countries
        indicator (str): String of the indicator requested. Options are:
            'NY.GDP.MKTP.CD' for GDP
            'SP.POP.TOTL' for population
        start_year (int): start year of the data
        end_year (int): end year of the data

    Returns:
        pandas.DataFrame: DataFrame containing the data
    """
    # Build the API URL
    base_url = (
        f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
    )
    params = {
        "format": "json",
        "per_page": 30000,  # Maximum number of results per page
        "date": f"{str(start_year)}:{str(end_year)}",  # Data range from 1960 to most recent available
    }

    # Make the API request
    response = requests.get(base_url, params=params)

    # Check if request was successful
    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        return None

    # Parse JSON response
    data = response.json()

    # The actual data is in the second element of the returned list
    if len(data) < 2:
        print("Error: No data returned from API")
        return None

    records = data[1]

    # Create a list to store the data
    return_data = []

    for record in records:
        if record["value"] is not None:  # Some years might not have data
            return_data.append(
                {
                    "Year": record["date"],
                    record["indicator"]["value"]: record["value"],
                    "Country": record["country"]["value"],
                    "ISO3": record["countryiso3code"],
                }
            )

    # Convert to DataFrame
    df = pd.DataFrame(return_data)

    # Convert Year to integer and sort by year
    df["Year"] = df["Year"].astype(int)
    df = df.sort_values("Year")

    # Reset index
    df = df.reset_index(drop=True)

    # add a column that says whether it's a country or not
    country_iso3s = [
        country["cca3"]
        for country in requests.get(
            "https://restcountries.com/v3.1/all?fields=cca3"
        ).json()
    ]
    df["country_or_group"] = [
        "country" if _ in country_iso3s else "group" for _ in df["ISO3"]
    ]

    return df
