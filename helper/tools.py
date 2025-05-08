import datetime
import io
from langchain_core.tools import tool
import os
import pandas as pd
import requests
from typing import Union, List, Optional


@tool
def get_world_bank(
    country_code: str, indicator: str, start_year: int, end_year: int
) -> pd.DataFrame:
    """
    Fetch data from World Bank API

    Parameters:
        country_code (str): ISO 3-letter country code, or 'all' for all countries
        indicator (str): String of the indicator requested.
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


@tool
def get_unctadstat(
    report_code: str,
    indicator_code: str,
    country_code: Union[str, List[str]],
    start_year: Optional[Union[int, str]] = None,
    end_year: Optional[Union[int, str]] = None,
) -> pd.DataFrame:
    """
    Fetch data from UNCTADstat.

    Parameters:
        report_code: the code of the desired dataset.
        indicator_code: the desired indicator code or name of the dataset.
        country_code (str or list[str]): either a single ISO 3-letter country code, a list of ISO 3-letter country codes, or 'all' for all countries and groups.
        start_year (int or str): int start year of the data. If start_year and end_year are None, it will return all available years. For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc.
        end_year (int or str): int end year of the data.  For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc.

    Returns:
        pandas.DataFrame: DataFrame containing the data
    """

    # country key
    if not (os.path.exists("metadata/country_key.csv")):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(
            "https://unctadstat.unctad.org/EN/Classifications/DimCountries_Transcode_Iso3166-1_UnctadStat.xls",
            headers=headers,
        )
        excel_file = io.BytesIO(response.content)
        country_key = pd.read_excel(excel_file)

        # file cleanup
        country_key = country_key.iloc[3:, [1, 4, 5]]
        country_key.columns = ["ISO3", "UNCTAD_code", "UNCTAD_name"]
        country_key = country_key.loc[
            lambda x: pd.Series([len(str(_)) == 3 for _ in x["ISO3"]])
            & (~pd.isna(x["ISO3"])),
            :,
        ].reset_index(
            drop=True
        )  # drop non ISO3 countries

        country_key.to_csv("metadata/country_key.csv", index=False)
    else:
        country_key = pd.read_csv("metadata/country_key.csv")

    # unctadstat key
    unctadstat_key = pd.read_csv("metadata/unctadstat_key.csv")

    # make robust to the LLM calling the indicator_name instead
    tmp = unctadstat_key.loc[
        lambda x: (x["report_code"] == report_code)
        & ((x["indicator_code"] == indicator_code)),
        :,
    ].reset_index(drop=True)
    if len(tmp) == 0:
        tmp = unctadstat_key.loc[
            lambda x: (x["report_code"] == report_code)
            & ((x["indicator_name"] == indicator_code)),
            :,
        ].reset_index(drop=True)
    unctadstat_key = tmp
    column_name = unctadstat_key["indicator_code"].values[0]
    return_columns = unctadstat_key["return_columns"].values[0]

    # if passed a S01 for start or end_year, change report to US.PortCalls_S for semi-annual data
    semi_annual_port = report_code in ["US.PortCalls", "US.PortCallsArrivals"] and (
        isinstance(start_year, str) or isinstance(end_year, str)
    )
    if semi_annual_port:
        report_code += "_S"

    # url construction
    base_url = "https://unctadstat-user-api.unctad.org"
    version = "cur"

    call_url = f"{base_url}/{report_code}/{version}/Facts"

    headers = {
        "clientid": os.environ.get("UNCTADSTAT_CLIENTID"),
        "clientsecret": os.environ.get("UNCTADSTAT_CLIENTSECRET"),
    }

    # year filter
    if start_year is None:
        if semi_annual_port:
            start_year = "1950S01"
        else:
            start_year = 1950
    if end_year is None:
        if semi_annual_port:
            end_year = str(datetime.datetime.now().year) + "S02"
        else:
            end_year = datetime.datetime.now().year

    # different date filter for population growth report
    if report_code in ["US.PopGR"]:
        year_filter = f"""Period/Label in ({",".join(["'" + str(_) + "'" for _ in range(start_year, end_year + 1)])})"""
    elif semi_annual_port:
        year_filter = f"""Period/Code in ({",".join([f"'{year}S{season:02}'" for year in list(range(int(start_year[:4]), int(end_year[:4])+1)) for season in range(1, 3)])})"""
    else:
        year_filter = f"""Year in ({",".join([str(_) for _ in range(start_year, end_year + 1)])})"""

    # country filter
    if country_code == "all":
        country_filter = ""
    else:
        if isinstance(country_code, str):
            country_codes = [
                country_key.loc[
                    lambda x: x["ISO3"] == country_code, "UNCTAD_code"
                ].values[0]
            ]
        else:
            country_codes = list(
                country_key.loc[
                    lambda x: x["ISO3"].isin(country_code), "UNCTAD_code"
                ].values
            )

        # different country filter for vessel value report
        if report_code in ["US.VesselValueByOwnership"]:
            country_filter = f"""BeneficialOwnership/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
        elif report_code in ["US.VesselValueByRegistration"]:
            country_filter = f"""FlagOfRegistration/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
        else:
            country_filter = f"""Economy/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""

    # combined filter
    combined_filter = (
        f"{year_filter} and {country_filter}"
        if year_filter and country_filter
        else year_filter or country_filter or ""
    )

    if semi_annual_port:
        return_columns = return_columns.replace("Year", "Period/Label")

    params = {
        "$filter": combined_filter,
        "$select": return_columns,
        "$format": "csv",
    }

    response = requests.post(call_url, headers=headers, data=params)

    df = pd.read_csv(io.StringIO(response.text))
    df = df.rename(
        columns={
            column_name.replace("/", "_"): unctadstat_key["indicator_name"].values[0]
        }
    )  # replacing code name with readable name

    return df
