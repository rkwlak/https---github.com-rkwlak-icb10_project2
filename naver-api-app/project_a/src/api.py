import requests
from typing import List, Optional
from utils import SHOP_CATEGORY_MAP
import pandas as pd

BASE_URL = "https://openapi.naver.com"

def _make_request(path: str, params: dict, client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """Naver API 호출 헬퍼 함수.
    성공 시 pandas DataFrame 반환, 실패 시 None 반환.
    """
    url = f"{BASE_URL}{path}"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # 대부분의 API는 "items" 리스트를 반환한다.
        items = data.get("items") or data.get("results") or []
        if not isinstance(items, list):
            items = []
        df = pd.DataFrame(items)
        return df
    except Exception as e:
        # 로그는 Streamlit UI에서 처리하도록 None 반환
        print(f"Naver API error ({path}): {e}")
        return None

def get_trend(keywords: List[str], start_date: str, end_date: str, client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """데이터랩 검색어 트렌드 API 호출.
    `keywords` 리스트를 전달하면 Naver DataLab 형식에 맞게 변환한다.
    """
    path = "/v1/datalab/search"
    # DataLab은 POST JSON 형태이지만 여기서는 GET 요청으로 간단히 구현한다.
    # 실제 사용 시 POST 로 교체 필요.
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",
        "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords],
    }
    # DataLab은 POST이므로 requests.post 사용.
    url = f"{BASE_URL}{path}"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        
        if not results:
            return pd.DataFrame()
            
        # API 결과를 날짜별 키워드 트렌드 테이블로 가공
        trend_dict = {}
        for group in results:
            title = group.get("title")
            for item in group.get("data", []):
                period = item.get("period")
                ratio = item.get("ratio")
                if period not in trend_dict:
                    trend_dict[period] = {}
                trend_dict[period][title] = ratio
                
        df = pd.DataFrame.from_dict(trend_dict, orient="index")
        df = df.sort_index()
        df.index.name = "날짜"
        df = df.reset_index()
        return df
    except Exception as e:
        print(f"Trend API error: {e}")
        return None

def _search_common(path: str, keywords: List[str], client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """공통 검색 API (날짜 파라미터 없이)."""
    query = ",".join(keywords)
    params = {
        "query": query,
        "display": 100,
        "start": 1,
        "sort": "sim",
    }
    return _make_request(path, params, client_id, client_secret)

def get_category_id(category_name: str) -> Optional[str]:
    """쇼핑 카테고리 이름을 ID로 변환."""
    return SHOP_CATEGORY_MAP.get(category_name)

def get_shopping(keywords: List[str], client_id: str, client_secret: str, category_id: Optional[str] = None) -> Optional[pd.DataFrame]:

    path = "/v1/search/shop"
    query = ",".join(keywords)
    params = {"query": query, "display": 100, "start": 1, "sort": "sim"}
    if category_id:
        params["categoryId"] = category_id
    return _make_request(path, params, client_id, client_secret)

def get_blog(keywords: List[str], client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """블로그 검색 API (날짜 파라미터 제외)"""
    path = "/v1/search/blog"
    query = ",".join(keywords)
    params = {"query": query, "display": 100, "start": 1, "sort": "sim"}
    return _make_request(path, params, client_id, client_secret)

def get_cafe(keywords: List[str], client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """카페글 검색 API (날짜 파라미터 제외)"""
    path = "/v1/search/cafearticle"
    query = ",".join(keywords)
    params = {"query": query, "display": 100, "start": 1, "sort": "sim"}
    return _make_request(path, params, client_id, client_secret)

def get_news(keywords: List[str], client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    """뉴스 검색 API (날짜 파라미터 제외)"""
    path = "/v1/search/news"
    query = ",".join(keywords)
    params = {"query": query, "display": 100, "start": 1, "sort": "sim"}
    return _make_request(path, params, client_id, client_secret)

def get_shopping_trend(keywords: List[str], start_date: str, end_date: str, client_id: str, client_secret: str) -> Optional[pd.DataFrame]:
    # 쇼핑 트렌드는 DataLab 과 동일한 형식이지만 쇼핑 카테고리 필터링을 가정한다.
    # 여기서는 get_trend 를 재사용한다.
    return get_trend(keywords, start_date, end_date, client_id, client_secret)
