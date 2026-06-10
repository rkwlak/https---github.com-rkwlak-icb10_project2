import re
import datetime
import pandas as pd

# ---------------------------------------------------------------------------
# 쇼핑 카테고리 매핑 (Naver 쇼핑 API에서 사용되는 카테고리 ID)
# ---------------------------------------------------------------------------
# HTML 리스트에 포함된 카테고리를 딕셔너리 형태로 관리합니다. UI에서 선택한
# 카테고리 ID를 API 파라미터에 전달하여 해당 카테고리 상품만 검색하도록 합니다.
SHOP_CATEGORY_MAP: dict[str, str] = {
    "패션의류": "50000000",
    "패션잡화": "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어": "50000004",
    "출산/육아": "50000005",
    "식품": "50000006",
    "스포츠/레저": "50000007",
    "생활/건강": "50000008",
    "여가/생활편의": "50000009",
    "면세점": "50000010",
    "도서": "50005542",
}



def parse_api_key(key_str: str):
    """클라이언트 ID와 시크릿을 "ID:SECRET" 형태로 입력받아 튜플 반환.
    입력이 비어 있거나 형식이 맞지 않으면 (None, None) 반환.
    """
    if not key_str:
        return None, None
    parts = key_str.strip().split(":")
    if len(parts) != 2:
        return None, None
    client_id, client_secret = parts[0].strip(), parts[1].strip()
    return client_id, client_secret


def split_keywords(raw: str):
    """쉼표(,) 혹은 줄바꿈으로 구분된 검색어 문자열을 리스트로 변환."""
    if not raw:
        return []
    # 콤마와 줄바꿈을 모두 구분자로 사용
    keywords = re.split(r"[\n,]+", raw)
    # 빈 문자열 제거 및 앞뒤 공백 정리
    return [kw.strip() for kw in keywords if kw.strip()]


def enforce_limit(keywords: list[str], max_count: int = 500) -> list[str]:
    """키워드 개수가 제한을 초과하면 앞쪽 `max_count` 개만 남긴다."""
    return keywords[:max_count]


def format_date(dt: datetime.date) -> str:
    """날짜 객체를 Naver API에서 요구하는 YYYYMMDD 문자열로 변환."""
    return dt.strftime("%Y%m%d")


def download_df_as_csv(df: pd.DataFrame) -> bytes:
    """DataFrame을 UTF‑8 CSV 바이너리로 변환해 Streamlit 다운로드에 사용."""
    return df.to_csv(index=False).encode("utf-8")
