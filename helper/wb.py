import os
import pandas as pd
import requests


def get_wb_indicator_list():
    "get metadata information of wb_indicators"

    if os.path.exists("metadata/wb_key.csv"):
        wb_info = pd.read_csv("metadata/wb_key.csv")
    else:
        base_url = "https://api.worldbank.org/v2/indicator"
        params = {
            "format": "json",
            "per_page": 30000,
        }

        response = requests.get(base_url, params=params)

        ids = [_["id"] for _ in response.json()[1]]
        names = [_["name"] for _ in response.json()[1]]
        wb_info = pd.DataFrame({"indicator": ids, "name": names})

        wb_info.to_csv("metadata/wb_key.csv", index=False)

    return wb_info
