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


### UNCTADstat helpers
def get_country_key():
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

        try:
            country_key.to_csv("metadata/country_key.csv", index=False)
        except:
            pass
    else:
        country_key = pd.read_csv("metadata/country_key.csv")

    return country_key


def get_country_group_key():
    if not (os.path.exists("metadata/country_group_key.csv")):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(
            "https://unctadstat.unctad.org/EN/Classifications/Dim_Countries_Hierarchy_UnctadStat_All_Flat.csv",
            headers=headers,
        )
        csv_file = io.BytesIO(response.content)
        country_group_key = pd.read_csv(csv_file)
        country_group_key.columns = [
            "parent_code",
            "parent_label",
            "child_code",
            "child_label",
        ]

        try:
            country_group_key.to_csv("metadata/country_group_key.csv", index=False)
        except:
            pass
    else:
        country_group_key = pd.read_csv("metadata/country_group_key.csv")

    return country_group_key


def filter_unctadstat_key(unctadstat_key, report_code, indicator_code):
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

    return tmp


def gen_country_filter(country_key, country_group_key, geography, group_or_countries):
    if geography == "all":
        country_codes = list(country_key.loc[:, "UNCTAD_code"].values)
    else:
        if isinstance(geography, str):
            if len(geography) == 3:  # iso3
                country_codes = [
                    country_key.loc[
                        lambda x: x["ISO3"] == geography, "UNCTAD_code"
                    ].values[0]
                ]
            else:  # non-iso3, country group
                if group_or_countries == "group":
                    country_codes = [
                        str(
                            country_group_key.loc[
                                lambda x: x["parent_label"] == geography,
                                "parent_code",
                            ].values[0]
                        )
                    ]
                else:
                    country_codes = list(
                        country_group_key.loc[
                            lambda x: x["parent_label"] == geography,
                            "child_code",
                        ].values
                    )
        else:
            if len(geography[0]) == 3:  # iso3
                country_codes = [
                    str(_)
                    for _ in list(
                        country_key.loc[
                            lambda x: x["ISO3"].isin(geography), "UNCTAD_code"
                        ].values
                    )
                ]
            else:  # non-iso3, country group
                if group_or_countries == "group":
                    country_codes = [
                        str(_)
                        for _ in list(
                            country_group_key.loc[
                                lambda x: x["parent_label"].isin(geography),
                                "parent_code",
                            ].values
                        )
                    ]
                else:
                    country_codes = [
                        str(_)
                        for _ in list(
                            country_group_key.loc[
                                lambda x: x["parent_label"].isin(geography),
                                "child_code",
                            ].values
                        )
                    ]

    # world should be '0000' not '0'
    if len(country_codes) == 1 and country_codes[0] == "0":
        country_codes = ["0000"]

    return country_codes


@tool
def get_unctadstat(
    report_code: str,
    indicator_code: str,
    geography: Union[str, List[str]],
    group_or_countries: str = "group",
    start_date: Optional[Union[int, str]] = None,
    end_date: Optional[Union[int, str]] = None,
) -> pd.DataFrame:
    """
    Fetch data from UNCTADstat.

    Parameters:
        report_code: the code of the desired dataset.
        indicator_code: the desired indicator code or name of the dataset.
        geography (str or list[str]): either a single ISO 3-letter country code, a list of ISO 3-letter country codes, 'all' for all countries, a single one of the following country group names, or a list of the following country group names. ISO3 and country group names cannot be passed in the same list. Individual country names cannot be passed to this parameter, use ISO3 codes if you want figures for individual countries. If 'report_code' = 'US.PLSCI', can also input the port name or list of port names directly in the format 'country_name, port_name':
            'Africa'
            'Americas'
            'Asia'
            'Asia and Oceania'
            'Australia and New Zealand'
            'BioTrade countries'
            'BRICS'
            'Caribbean'
            'CBD (Convention on Biological Diversity)'
            'Central America'
            'Central and Southern Asia'
            'Central Asia'
            'CITES (Convention on International Trade in Endangered Species of Wild Fauna and Flora)'
            'Developed economies'
            'Developed economies: Americas'
            'Developed economies: Asia'
            'Developed economies: Asia and Oceania'
            'Developed economies: Europe'
            'Developed economies: Oceania'
            'Developing economies'
            'Developing economies excluding China'
            'Developing economies excluding LDCs'
            'Developing economies: Africa'
            'Developing economies: Americas'
            'Developing economies: Asia'
            'Developing economies: Asia and Oceania'
            'Developing economies: Central Asia'
            'Developing economies: Eastern Asia'
            'Developing economies: Northern Africa'
            'Developing economies: Oceania'
            'Developing economies: South-eastern Asia'
            'Developing economies: Southern Asia'
            'Developing economies: Sub-Saharan Africa'
            'Developing economies: Western Asia'
            'Eastern Africa'
            'Eastern and South-Eastern Asia'
            'Eastern Asia'
            'Eastern Europe'
            'Europe'
            'Europe, Northern America, Australia and New Zealand'
            'European Union (2020 ‚Ä¶)'
            'G-77 (Group of 77)'
            'G20 (Group of Twenty)'
            'Latin America and the Caribbean'
            'LDCs (Least developed countries)'
            'LDCs: Africa'
            'LDCs: Asia'
            'LDCs: Islands and Haiti'
            'LLDCs (Landlocked developing countries)'
            'LMMC (Like-Minded Megadiverse Countries)'
            'Middle Africa'
            'Nagoya Protocol on Access and Benefit Sharing'
            'Northern Africa'
            'Northern America'
            'Northern America and Europe'
            'Northern Europe'
            'Oceania'
            'Oceania excluding Australia and New Zealand'
            'OECD (Organisation for Economic Cooperation and Development)'
            'Other territories'
            'SIDS (Small island developing States) (UN-OHRLLS)'
            'SIDS: Atlantic and Indian Ocean'
            'SIDS: Caribbean'
            'SIDS: Pacific'
            'South America'
            'South-eastern Asia'
            'Southern Africa'
            'Southern Asia'
            'Southern Europe'
            'Sub-Saharan Africa'
            'Western Africa'
            'Western Asia'
            'Western Asia and Northern Africa'
            'Western Europe'
            'World'
        group_or_countries (str): either 'group' or 'countries'. Only relevant if the 'geography' parameter is a country group. 'group' to return only the aggregate figure for that group, 'countries' to return the individual figures for each country that constitutes that group.
        start_date (int or str): int start year of the data. If None, it will return from the earliest available date. For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc. For quarterly data, pass a string like '2023Q01', '2023Q04', etc. For monthly data, pass a string like '2023M01', '2023M10', etc.
        end_date (int or str): int end year of the data. If None, it will return until the present year.  For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc For quarterly data, pass a string like '2023Q01', '2023Q04', etc. For monthly data, pass a string like '2023M01', '2023M10', etc.

    Returns:
        pandas.DataFrame: DataFrame containing the data
    """

    # country key
    country_key = get_country_key()

    # country group key
    country_group_key = get_country_group_key()

    # unctadstat key
    try:
        unctadstat_key = pd.read_csv("metadata/unctadstat_key.csv")
    except:
        unctadstat_key = pd.read_csv(
            "https://raw.githubusercontent.com/dhopp1/statschat/refs/heads/main/metadata/unctadstat_key.csv"
        )

    # make robust to the LLM calling the indicator_name instead
    unctadstat_key = filter_unctadstat_key(unctadstat_key, report_code, indicator_code)
    column_name = unctadstat_key["indicator_code"].values[0]
    return_columns = unctadstat_key["return_columns"].values[0]

    # if passed a S01 for start or end_date, change report to US.PortCalls_S for semi-annual data
    semi_annual_port = report_code in ["US.PortCalls", "US.PortCallsArrivals"] and (
        isinstance(start_date, str) or isinstance(end_date, str)
    )
    if semi_annual_port:
        report_code += "_S"

    # if passed a M01 for start or end_date, change report to US.PortCalls_M for monthly data
    monthly = False
    if report_code in ["US.CommodityPriceIndices_M", "US.CommodityPrice_M"]:
        monthly = True

    monthly_liner = report_code in ["US.LSCI"] and (
        "M" in str(start_date) or "M" in str(end_date)
    )
    if monthly_liner:
        report_code += "_M"

    # url construction
    base_url = "https://unctadstat-user-api.unctad.org"
    version = "cur"

    call_url = f"{base_url}/{report_code}/{version}/Facts"

    headers = {
        "clientid": os.environ.get("UNCTADSTAT_CLIENTID"),
        "clientsecret": os.environ.get("UNCTADSTAT_CLIENTSECRET"),
    }

    # date filter
    if start_date is None:
        if semi_annual_port:
            start_date = "1950S01"
        elif report_code in [
            "US.LSCI",
            "US.LSCI_M",
            "US.MerchVolumeQuarterly",
            "US.PLSCI",
            "US.TotAndComServicesQuarterly",
        ]:
            if monthly_liner or monthly:
                start_date = "1950M01"
            else:
                start_date = "1950Q01"
        elif report_code == "US.TradeMerchGR":
            start_date = "19801981"
        else:
            start_date = 1950
    if end_date is None:
        if semi_annual_port:
            end_date = str(datetime.datetime.now().year) + "S02"
        elif report_code in [
            "US.LSCI",
            "US.LSCI_M",
            "US.MerchVolumeQuarterly",
            "US.PLSCI",
            "US.TotAndComServicesQuarterly",
        ]:
            if monthly_liner or monthly:
                end_date = f"{datetime.datetime.now().year}M12"
            else:
                end_date = f"{datetime.datetime.now().year}Q04"
        elif report_code == "US.TradeMerchGR":
            end_date = f"{datetime.datetime.now().year-1}{datetime.datetime.now().year}"
        else:
            end_date = datetime.datetime.now().year

    if report_code in [
        "US.LSCI",
        "US.MerchVolumeQuarterly",
        "US.PLSCI",
        "US.TotAndComServicesQuarterly",
    ]:
        if isinstance(start_date, int):
            start_date = f"{start_date}Q01"
        if isinstance(end_date, int):
            end_date = f"{end_date}Q04"

    if report_code in ["US.CommodityPriceIndices_M", "US.CommodityPrice_M"]:
        if isinstance(start_date, int):
            start_date = f"{start_date}M01"
        if isinstance(end_date, int):
            end_date = f"{end_date}M12"

    # different date filter for population growth report
    if report_code in ["US.PopGR"]:
        date_filter = f"""Period/Label in ({",".join(["'" + str(_) + "'" for _ in range(start_date, end_date + 1)])})"""
    elif semi_annual_port:
        date_filter = f"""Period/Code in ({",".join([f"'{year}S{season:02}'" for year in list(range(int(start_date[:4]), int(end_date[:4])+1)) for season in range(1, 3) if f"{year}S{season:02}" >= start_date and f"{year}S{season:02}" <= end_date])})"""
    elif report_code in [
        "US.LSCI",
        "US.LSCI_M",
        "US.MerchVolumeQuarterly",
        "US.PLSCI",
        "US.CommodityPriceIndices_M",
        "US.CommodityPrice_M",
        "US.TotAndComServicesQuarterly",
    ]:
        if monthly_liner:
            date_filter = f"""Month/Code in ({",".join([f"'{year}M{month:02}'" for year in list(range(int(start_date[:4]), int(end_date[:4])+1)) for month in range(1, 13) if f"{year}M{month:02}" >= start_date and f"{year}M{month:02}" <= end_date])})"""
        elif report_code in ["US.CommodityPriceIndices_M", "US.CommodityPrice_M"]:
            date_filter = f"""Period/Code in ({",".join([f"'{year}M{month:02}'" for year in list(range(int(start_date[:4]), int(end_date[:4])+1)) for month in range(1, 13) if f"{year}M{month:02}" >= start_date and f"{year}M{month:02}" <= end_date])})"""
        else:
            period_label = (
                "Quarter"
                if report_code not in ["US.TotAndComServicesQuarterly"]
                else "Period"
            )
            date_filter = f"""{period_label}/Code in ({",".join([f"'{year}Q{quarter:02}'" for year in list(range(int(start_date[:4]), int(end_date[:4])+1)) for quarter in range(1, 5) if f"{year}Q{quarter:02}" >= start_date and f"{year}Q{quarter:02}" <= end_date])})"""
    elif report_code in ["US.TradeMerchGR"]:
        date_filter = f"""Year/Code in ({",".join([f"'{year}{year+1}'" for year in range(start_date - 1, end_date)])})"""
    else:
        date_filter = (
            f"""Year in ({",".join([str(_) for _ in range(start_date, end_date+1)])})"""
        )

    # country filter
    if geography == "all":
        country_codes = list(country_key.loc[:, "UNCTAD_code"].values)
    else:
        if report_code in ["US.PLSCI"]:
            if isinstance(geography, str):
                country_codes = [geography]
            else:
                country_codes = geography
        else:
            try:
                country_codes = gen_country_filter(
                    country_key, country_group_key, geography, group_or_countries
                )
            except:
                country_codes = ""

    # different country filter for vessel value report
    if report_code in ["US.VesselValueByOwnership"]:
        country_filter = f"""BeneficialOwnership/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
    elif report_code in ["US.VesselValueByRegistration"]:
        country_filter = f"""FlagOfRegistration/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
    elif report_code in ["US.PLSCI"]:
        country_filter = (
            f"""Port/Label in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
        )
    else:
        country_filter = (
            f"""Economy/Code in ({','.join(["'" + _ + "'" for _ in country_codes])})"""
        )

    if report_code in ["US.Tariff"]:
        country_filter = country_filter.replace("Economy", "Market")

    if report_code in ["US.PLSCI"] and (geography == "all" or geography == "World"):
        country_filter = ""
    if report_code in [
        "US.CommodityPriceIndices_A",
        "US.CommodityPriceIndices_M",
        "US.CommodityPrice_A",
        "US.CommodityPrice_M",
        "US.CreativeGoodsIndex",
    ]:  # no country/economy dimension
        country_filter = ""

    # combined filter
    combined_filter = (
        f"{date_filter} and {country_filter}"
        if date_filter and country_filter
        else date_filter or country_filter or ""
    )

    if semi_annual_port:
        return_columns = return_columns.replace("Year", "Period/Code")
    if monthly_liner:
        return_columns = return_columns.replace("Quarter/Code", "Month/Code").replace(
            "M6047/Value", "M6048/Value"
        )

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

    # converting semester, quarterly, and monthly to date format
    if semi_annual_port:
        df["Period_Code"] = [
            (
                lambda d: (
                    datetime.date(int(d[:4]), 6 if d[4:] == "S01" else 12, 1)
                    if isinstance(d, str)
                    and len(d) == 7
                    and d[4] == "S"
                    and d[5:7].isdigit()
                    and (d[5:7] == "01" or d[5:7] == "02")
                    else None
                )
            )(d)
            for d in df["Period_Code"]
        ]

    if report_code in [
        "US.LSCI",
        "US.LSCI_M",
        "US.MerchVolumeQuarterly",
        "US.PLSCI",
        "US.CommodityPriceIndices_M",
        "US.CommodityPrice_M",
        "US.TotAndComServicesQuarterly",
    ]:
        if monthly_liner:
            df["Month_Code"] = [
                datetime.datetime.strptime(d, "%YM%m").date() for d in df["Month_Code"]
            ]
        elif report_code in ["US.CommodityPriceIndices_M", "US.CommodityPrice_M"]:
            df["Period_Code"] = [
                datetime.datetime.strptime(d, "%YM%m").date() for d in df["Period_Code"]
            ]
        else:
            df[f"{period_label}_Code"] = [
                (
                    lambda d: (
                        datetime.date(int(d[:4]), (int(d[5:]) - 1) * 3 + 3, 1)
                        if isinstance(d, str)
                        and len(d) == 7
                        and d[4] == "Q"
                        and d[5:].isdigit()
                        and 1 <= int(d[5:]) <= 4
                        else None
                    )
                )(d)
                for d in df[f"{period_label}_Code"]
            ]

    # naming date column
    df = df.rename(
        columns={
            col: "date"
            for col in [
                "Period_Label",
                "Period_Code",
                "Year",
                "Month_Code",
                "Quarter_Code",
            ]
            if col in df.columns
        }
    )

    return df


@tool
def get_unctadstat_tradelike(
    report_code: str,
    indicator_code: str,
    geography_a: Union[str, List[str]] = "World",
    geography_b: Union[str, List[str]] = "World",
    group_or_countries_a: str = "group",
    group_or_countries_b: str = "group",
    start_date: Optional[Union[int, str]] = None,
    end_date: Optional[Union[int, str]] = None,
    flow: Union[str, List[str]] = "Exports",
    products: Union[str, List[str]] = "total",
) -> pd.DataFrame:
    """
    Fetch data from UNCTADstat.

    Parameters:
        report_code: the code of the desired dataset.
        indicator_code: the desired indicator code or name of the dataset.
        geography_a (str or list[str]): either a single ISO 3-letter country code, a list of ISO 3-letter country codes, 'all' for all countries, a single one of the following country group names, or a list of the following country group names. ISO3 and country group names cannot be passed in the same list. Individual country names cannot be passed to this parameter, use ISO3 codes if you want figures for individual countries:
            'Africa'
            'Americas'
            'Asia'
            'Asia and Oceania'
            'Australia and New Zealand'
            'BioTrade countries'
            'BRICS'
            'Caribbean'
            'CBD (Convention on Biological Diversity)'
            'Central America'
            'Central and Southern Asia'
            'Central Asia'
            'CITES (Convention on International Trade in Endangered Species of Wild Fauna and Flora)'
            'Developed economies'
            'Developed economies: Americas'
            'Developed economies: Asia'
            'Developed economies: Asia and Oceania'
            'Developed economies: Europe'
            'Developed economies: Oceania'
            'Developing economies'
            'Developing economies excluding China'
            'Developing economies excluding LDCs'
            'Developing economies: Africa'
            'Developing economies: Americas'
            'Developing economies: Asia'
            'Developing economies: Asia and Oceania'
            'Developing economies: Central Asia'
            'Developing economies: Eastern Asia'
            'Developing economies: Northern Africa'
            'Developing economies: Oceania'
            'Developing economies: South-eastern Asia'
            'Developing economies: Southern Asia'
            'Developing economies: Sub-Saharan Africa'
            'Developing economies: Western Asia'
            'Eastern Africa'
            'Eastern and South-Eastern Asia'
            'Eastern Asia'
            'Eastern Europe'
            'Europe'
            'Europe, Northern America, Australia and New Zealand'
            'European Union (2020 ‚Ä¶)'
            'G-77 (Group of 77)'
            'G20 (Group of Twenty)'
            'Latin America and the Caribbean'
            'LDCs (Least developed countries)'
            'LDCs: Africa'
            'LDCs: Asia'
            'LDCs: Islands and Haiti'
            'LLDCs (Landlocked developing countries)'
            'LMMC (Like-Minded Megadiverse Countries)'
            'Middle Africa'
            'Nagoya Protocol on Access and Benefit Sharing'
            'Northern Africa'
            'Northern America'
            'Northern America and Europe'
            'Northern Europe'
            'Oceania'
            'Oceania excluding Australia and New Zealand'
            'OECD (Organisation for Economic Cooperation and Development)'
            'Other territories'
            'SIDS (Small island developing States) (UN-OHRLLS)'
            'SIDS: Atlantic and Indian Ocean'
            'SIDS: Caribbean'
            'SIDS: Pacific'
            'South America'
            'South-eastern Asia'
            'Southern Africa'
            'Southern Asia'
            'Southern Europe'
            'Sub-Saharan Africa'
            'Western Africa'
            'Western Asia'
            'Western Asia and Northern Africa'
            'Western Europe'
            'World'
        geography_b (str or list[str]):same as 'geography_b', with the same options, but for the second geography of interest, e.g., partner geography for trade, second country for bilateral connectivity, etc.
        group_or_countries_a (str): either 'group' or 'countries'. Only relevant if the 'geography_a' parameter is a country group. 'group' to return only the aggregate figure for that group, 'countries' to return the individual figures for each country that constitutes that group.
        group_or_countries_b (str): same as 'group_or_countries_a' but for the second geography
        start_date (int or str): int start year of the data. If None, it will return from the earliest available date. For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc. For quarterly data, pass a string like '2023Q01', '2023Q04', etc. For monthly data, pass a string like '2023M01', '2023M10', etc.
        end_date (int or str): int end year of the data. If None, it will return until the present year.  For semi-annual/semester data, pass string like '2023S01' for first half of 2023, '2023S02' for second half, etc For quarterly data, pass a string like '2023Q01', '2023Q04', etc. For monthly data, pass a string like '2023M01', '2023M10', etc.
        flow (str or list[str]): if relevant, either a string of the desired trade flow, or a list of strings of desired trade flows. Options are: 'Exports', 'Imports', 'Re-exports', 'Re-imports', 'Balance'. Defaults to 'Exports'.
        products (str or list[str]): if relevant, either a string of the desired product code, or a list of strings of the desired product codes. 'total' to return only the aggregate metric for all products. 'all' to return all products.

    Returns:
        pandas.DataFrame: DataFrame containing the data
    """

    # country key
    country_key = get_country_key()

    # country group key
    country_group_key = get_country_group_key()

    # unctadstat key
    unctadstat_key = pd.read_csv("metadata/unctadstat_key.csv")

    # make robust to the LLM calling the indicator_name instead
    unctadstat_key = filter_unctadstat_key(unctadstat_key, report_code, indicator_code)
    column_name = unctadstat_key["indicator_code"].values[0]
    return_columns = unctadstat_key["return_columns"].values[0]

    # url construction
    base_url = "https://unctadstat-user-api.unctad.org"
    version = "cur"

    call_url = f"{base_url}/{report_code}/{version}/Facts"

    headers = {
        "clientid": os.environ.get("UNCTADSTAT_CLIENTID"),
        "clientsecret": os.environ.get("UNCTADSTAT_CLIENTSECRET"),
    }

    # date filter
    quarterly = False
    if report_code in ["US.LSBCI"]:
        quarterly = True
        if isinstance(start_date, int):
            start_date = f"{start_date}Q01"
        if isinstance(end_date, int):
            end_date = f"{end_date}Q04"

    if start_date is None:
        if quarterly:
            start_date = "1950Q01"
        else:
            start_date = 1950
    if end_date is None:
        if quarterly:
            end_date = f"{datetime.datetime.now().year}Q04"
        else:
            end_date = datetime.datetime.now().year

    if quarterly:
        date_filter = f"""Quarter/Code in ({",".join([f"'{year}Q{quarter:02}'" for year in list(range(int(start_date[:4]), int(end_date[:4])+1)) for quarter in range(1, 5) if f"{year}Q{quarter:02}" >= start_date and f"{year}Q{quarter:02}" <= end_date])})"""
    elif report_code in ["US.CreativeGoodsGR"]:
        date_filter = f"""Period/Code in ({",".join([f"'{year}{year+1}'" for year in range(start_date - 1, end_date)])})"""
    else:
        date_filter = (
            f"""Year in ({",".join([str(_) for _ in range(start_date, end_date+1)])})"""
        )

    # geography filters
    geography_a_country_codes = gen_country_filter(
        country_key, country_group_key, geography_a, group_or_countries_a
    )
    geography_b_country_codes = gen_country_filter(
        country_key, country_group_key, geography_b, group_or_countries_b
    )

    # final country filter
    economy_label = "Economy"
    partner_label = "Partner"
    if report_code in ["US.FleetBeneficialOwners"]:
        economy_label = "BeneficialOwnership"
        partner_label = "FlagOfRegistration"
        flow = "all"
    elif report_code in ["US.TransportCosts"]:
        economy_label = "Origin"
        partner_label = "Destination"
        flow = "all"
    elif report_code in ["US.ExchangeRateCrosstab"]:
        partner_label = "ForeignEconomy"
        flow = "all"
        products = "all"

    if report_code in ["US.LSBCI", "US.RCA"]:
        flow = "all"

    if report_code in [
        "US.BioTradeMerchMarketConcent",
        "US.BioTradeMerchStructChange",
        "US.ConcentStructIndices",
    ]:  # no geography element
        country_filter = ""
    else:
        country_filter = f"""{economy_label}/Code in ({','.join(["'" + _ + "'" for _ in geography_a_country_codes])})"""

        if report_code not in [
            "US.BiotradeMerchRCA",
            "US.OceanRCAIndividualEconomies",
            "US.OceanRCARegionalAggregates",
            "US.OceanTheilIndicesIndividualEconomies",
            "US.IntraTrade",
            "US.RCA",
            "US.TradeFoodProcCat_Cat_RCA",
            "US.TradeFoodProcCat_Proc_RCA",
        ]:  # no partner for these tables
            country_filter += f""" and {partner_label}/Code in ({','.join(["'" + _ + "'" for _ in geography_b_country_codes])})"""

    # product filter
    product_colname = "Product"

    # total product name
    if report_code in ["US.IctGoodsValue"]:
        total_product = "ICT00"
        product_colname = "IctGoodsCategory"
    elif report_code in ["US.TradeServCatByPartner"]:
        total_product = "S"
        product_colname = "Category"
    elif report_code in [
        "US.BiotradeMerch",
        "US.BiotradeMerchGR",
        "US.BioTradeMerchMarketConcent",
        "US.BioTradeMerchStructChange",
        "US.BiotradeMerchRCA",
    ]:
        total_product = "B_TOT"
    elif report_code in [
        "US.OceanTradeIndividualEconomies",
        "US.OceanTradeRegionalAggregates",
        "US.OceanRCAIndividualEconomies",
        "US.OceanRCARegionalAggregates",
        "US.OceanTheilIndicesIndividualEconomies",
    ]:
        total_product = "O_TOT"
    elif report_code in ["US.PlasticsTradebyPartner"]:
        total_product = "P_00"
    elif report_code in ["US.AssociatedPlasticsTradebyPartner"]:
        total_product = "P_11"
    elif report_code in ["US.HiddenPlasticsTradebyPartner"]:
        total_product = "P_12"
    elif report_code in ["US.NonPlasticSubstsTradeByPartner"]:
        total_product = "NPS000"
    elif report_code in [
        "US.TradeFoodCatByProc",
        "US.TradeFoodProcCat_Cat_RCA",
        "US.TradeFoodProcByCat",
        "US.TradeFoodProcCat_Proc_RCA",
    ]:
        total_product = "T00"
        product_colname = "ProcessFoodCategory"
    elif report_code in [
        "US.ConcentStructIndices",
        "US.TradeMatrix",
        "US.IntraTrade",
        "US.RCA",
        "US.TransportCosts",
    ]:
        total_product = "TOTAL"
    else:  # table doesn't have a product field
        total_product = "NA"
        products = "all"

    if isinstance(products, str):
        if products == "all":
            product_filter = ""
        elif products == "total":
            products = [total_product]
        else:
            products = [products]

    if not (isinstance(products, str)):
        product_filter = f""" and {product_colname}/Code in ({','.join("'" + _ + "'" for _ in products)})"""

    # add flow filter
    if isinstance(flow, str):
        if flow != "all":
            flow = [flow]

    if flow != "all":
        flow_filter = (
            f""" and Flow/Label in ({','.join("'" + _ + "'" for _ in flow)})"""
        )
    else:
        flow_filter = ""

    # combined filter
    combined_filter = (
        f"{date_filter} and {country_filter}"
        if date_filter and country_filter
        else date_filter or country_filter or ""
    )

    combined_filter += product_filter
    combined_filter += flow_filter

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

    # converting to date
    if quarterly:
        df["Quarter_Code"] = [
            (
                lambda d: (
                    datetime.date(int(d[:4]), (int(d[5:]) - 1) * 3 + 3, 1)
                    if isinstance(d, str)
                    and len(d) == 7
                    and d[4] == "Q"
                    and d[5:].isdigit()
                    and 1 <= int(d[5:]) <= 4
                    else None
                )
            )(d)
            for d in df["Quarter_Code"]
        ]

    # naming date column
    df = df.rename(
        columns={
            col: "date"
            for col in [
                "Period_Label",
                "Period_Code",
                "Year",
                "Month_Code",
                "Quarter_Code",
            ]
            if col in df.columns
        }
    )

    return df
