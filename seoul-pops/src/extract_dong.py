"""분석 대상 행정동만 tidy parquet에서 뽑아 매핑 정보(시도/시군구/행정동명)를 붙인다.

전체 매핑 테이블을 전체 tidy parquet(850만 행)에 join하면 그 순간 전체 데이터가
메모리에 올라온다. 이를 피하기 위해:
  1) 작은 매핑 엑셀에서 분석하려는 행정동명 -> 행정동코드만 먼저 찾고,
  2) parquet을 읽을 때 그 코드로 필터(predicate pushdown)를 걸어 해당 행정동
     데이터만 읽어오고,
  3) 이미 작아진 결과에만 매핑 정보를 조인한다.
"""

import io

import pandas as pd

MAPPING_XLSX = "data/행정동코드_매핑정보_20241218.xlsx"
TIDY_PARQUET = "data/LOCAL_PEOPLE_DONG_202606_tidy.parquet"


def load_dong_mapping() -> pd.DataFrame:
    # 1행: 한글 컬럼명(헤더), 2행: 영문 필드코드(H_SDNG_CD 등, 실제 데이터가 아님)
    # -> header=0으로 1행을 컬럼명으로 쓰고 skiprows=[1]로 2행을 제거한다.
    mapping = pd.read_excel(MAPPING_XLSX, sheet_name="행정동코드", header=0, skiprows=[1])
    # tidy parquet의 행정동코드는 문자열 category이므로 형식을 맞춰준다.
    mapping["행자부행정동코드"] = mapping["행자부행정동코드"].astype("int64").astype(str)
    return mapping


def find_matching_dong_names(mapping: pd.DataFrame, queries: list[str]) -> list[str]:
    """'성수동'처럼 여러 행정동(성수1가1동 등)으로 나뉜 이름을 접두어 일치로 모두 찾는다.

    법정동 이름(예: 성수동)이 행정동으로 세분화되면 '성수1가1동'처럼 뒤에 숫자/글자가
    붙는 방식이라, 쿼리의 마지막 '동' 글자를 뗀 stem으로 접두어 매칭한다.
    """
    names = mapping["행정동명"]
    found: set[str] = set()
    missing = []
    for q in queries:
        stem = q[:-1] if q.endswith("동") else q
        hits = names[names.str.startswith(stem)]
        if hits.empty:
            missing.append(q)
        else:
            found.update(hits.tolist())
    if missing:
        raise ValueError(f"매핑 테이블에서 찾을 수 없는 행정동명 쿼리: {missing}")
    return sorted(found)


def resolve_dong_codes(mapping: pd.DataFrame, dong_names: list[str]) -> pd.DataFrame:
    subset = mapping[mapping["행정동명"].isin(dong_names)]
    missing = set(dong_names) - set(subset["행정동명"])
    if missing:
        raise ValueError(f"매핑 테이블에서 찾을 수 없는 행정동명: {missing}")
    return subset[["행자부행정동코드", "시도명", "시군구명", "행정동명"]]


def extract_dong(dong_names: list[str], parquet_path: str = TIDY_PARQUET) -> pd.DataFrame:
    mapping = load_dong_mapping()
    dong_subset = resolve_dong_codes(mapping, dong_names)
    codes = dong_subset["행자부행정동코드"].tolist()

    # parquet 필터 pushdown: 850만 행 전체를 메모리에 올리지 않고
    # 요청한 행정동 코드에 해당하는 row group/행만 읽어온다.
    filtered = pd.read_parquet(
        parquet_path,
        engine="pyarrow",
        filters=[("행정동코드", "in", codes)],
    )

    # 이미 필터링되어 작아진 결과에만 매핑 정보를 조인한다(전체 조인 금지).
    merged = filtered.merge(
        dong_subset, left_on="행정동코드", right_on="행자부행정동코드", how="left"
    )
    merged = merged.drop(columns="행자부행정동코드")

    # parquet 필터 pushdown 경로에서는 category dtype이 보존되지 않고 object로
    # 돌아오므로, 작아진 결과에 맞춰 다시 category로 지정한다.
    for col in ["행정동코드", "시도명", "시군구명", "행정동명"]:
        merged[col] = merged[col].astype("category")

    return merged


def capture_info(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.info(buf=buf, memory_usage="deep")
    return buf.getvalue()


if __name__ == "__main__":
    demo_dong_names = ["길동"]

    result = extract_dong(demo_dong_names)

    print(f"=== {demo_dong_names} 추출 결과 상위 5행 ===")
    print(result.head())

    print("\n=== 추출 결과 info() ===")
    print(capture_info(result))
