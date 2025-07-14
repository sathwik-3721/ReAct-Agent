from src.config.logging import logger
from src.utils.io import load_yaml
from typing import Tuple, Union, Dict, List, Any
import requests
import json
import certifi
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Static paths
CREDENTIALS_PATH = './credentials/key.yml'

class SerpAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    def __call__(self, query: str, engine: str = "google", location: str = "") -> Union[Dict[str, Any], Tuple[int, str]]:
        params = {
            "engine": engine,
            "q": query,
            "api_key": self.api_key,
            "location": location
        }
        try:
            response = requests.get(self.base_url, params=params, verify=certifi.where())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to SERP API failed: {e}")
            return 0, str(e)


def load_api_key(credentials_path: str) -> str:
    config = load_yaml(credentials_path)
    return config['serp']['key']


def format_top_search_results(results: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
    return [
        {
            "position": result.get('position'),
            "title": result.get('title'),
            "link": result.get('link'),
            "snippet": result.get('snippet')
        }
        for result in results.get('organic_results', [])[:top_n]
    ]


def search(search_query: str, location: str = "") -> str:
    api_key = load_api_key(CREDENTIALS_PATH)
    serp_client = SerpAPIClient(api_key)
    results = serp_client(search_query, location=location)

    if isinstance(results, dict):
        top_results = format_top_search_results(results)
        return json.dumps({"top_results": top_results}, indent=2)
    else:
        status_code, error_message = results
        error_json = json.dumps({"error": f"Search failed with status code {status_code}: {error_message}"})
        logger.error(error_json)
        return error_json


if __name__ == "__main__":
    search_query = "Best gyros in Barcelona, Spain"
    result_json = search(search_query, '')
    print(result_json)