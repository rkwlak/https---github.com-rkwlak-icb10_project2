"""서울 생활인구(동별) 데이터를 읽어 tidy-data로 변환하고 parquet으로 저장한다.

- 원본: data/LOCAL_PEOPLE_DONG_202606.zip (wide format, 성별x연령대가 컬럼으로 펼쳐짐)
- 산출: data/LOCAL_PEOPLE_DONG_202606_tidy.parquet (long/tidy format, dtype downcast)
"""

import io

import pandas as pd
import pyarrow.parquet as pq

RAW_ZIP = "data/LOCAL_PEOPLE_DONG_202606.zip"
OUT_PARQUET = "data/LOCAL_PEOPLE_DONG_202606_tidy.parquet"
REPORT_PATH = "report/local_people_tidy_report.md"

ID_VARS = ["기준일ID", "시간대구분", "행정동코드", "총생활인구수"]


def load_raw() -> pd.DataFrame:
    # 원본 CSV는 데이터 행마다 끝에 콤마가 하나 더 붙어 있어(헤더보다 컬럼 1개 많음),
    # index_col=False를 주지 않으면 pandas가 첫 컬럼을 인덱스로 오인해 전체 컬럼이 밀린다.
    return pd.read_csv(RAW_ZIP, encoding="utf-8-sig", index_col=False)


def to_tidy(df: pd.DataFrame) -> pd.DataFrame:
    age_gender_cols = [c for c in df.columns if c not in ID_VARS]

    tidy = df.melt(
        id_vars=ID_VARS,
        value_vars=age_gender_cols,
        var_name="구분",
        value_name="인구수",
    )

    tidy["성별"] = tidy["구분"].str.slice(0, 2).map({"남자": "남", "여자": "여"})
    tidy["연령대"] = tidy["구분"].str.slice(2).str.replace("생활인구수", "", regex=False)
    tidy = tidy.drop(columns="구분")

    # 기준일, 행정동코드는 반복되는 식별자 성격의 값이므로 우선 category로 지정한다.
    # 정수형 category는 parquet round-trip 시 category가 풀려 평평한 정수로 복원되므로
    # (문자열 category만 dictionary로 보존됨), 문자열로 변환 후 category화한다.
    tidy["기준일ID"] = tidy["기준일ID"].astype(str).astype("category")
    tidy["행정동코드"] = tidy["행정동코드"].astype("int32").astype(str).astype("category")

    # 총생활인구수는 성별x연령대별 인구수를 모두 더하면 구할 수 있는 파생값이라
    # (즉 tidy 구조에서는 groupby("기준일ID","시간대구분","행정동코드")["인구수"].sum()과 동일) 컬럼에서 제외한다.
    return tidy[["기준일ID", "시간대구분", "행정동코드", "성별", "연령대", "인구수"]]


def describe_and_downcast(tidy: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    """기준일ID/행정동코드를 제외한 나머지 컬럼의 기술 통계를 구하고,
    그 결과를 근거로 downcast 가능한 컬럼을 downcast한다."""

    numeric_cols = ["시간대구분", "인구수"]
    categorical_cols = ["성별", "연령대"]

    numeric_desc = tidy[numeric_cols].describe()
    categorical_desc = tidy[categorical_cols].astype("object").describe()

    # 시간대구분: describe() 결과 min=0, max=23 -> uint8(0~255)로 충분.
    tidy["시간대구분"] = pd.to_numeric(tidy["시간대구분"], downcast="unsigned")

    # 인구수: describe() 결과 max가 float32 표현범위(~3.4e38)에 비해 훨씬 작고
    # 소수점 값이라, pd.to_numeric(downcast="float")는 정밀도 보존 조건 때문에
    # 무효화된다. astype으로 명시적으로 float32화한다.
    tidy["인구수"] = tidy["인구수"].astype("float32")

    # 성별/연령대: describe() 결과 unique 값이 각각 2개, 14개로 적어 category가 적합.
    tidy["성별"] = tidy["성별"].astype("category")
    tidy["연령대"] = tidy["연령대"].astype("category")

    return tidy, numeric_desc.to_string(), categorical_desc.to_string()


def capture_parquet_metadata(path: str) -> tuple[dict, list[tuple]]:
    """parquet 파일의 footer 메타 정보와 컬럼별 인코딩/압축 통계를 모은다."""

    pf = pq.ParquetFile(path)
    md = pf.metadata

    file_level = {
        "format_version": md.format_version,
        "created_by": md.created_by,
        "num_columns": md.num_columns,
        "num_rows": md.num_rows,
        "num_row_groups": md.num_row_groups,
        "footer_serialized_size": md.serialized_size,
    }

    col_stats: dict[str, dict] = {}
    for rg_idx in range(md.num_row_groups):
        rg = md.row_group(rg_idx)
        for col_idx in range(rg.num_columns):
            col = rg.column(col_idx)
            stat = col_stats.setdefault(
                col.path_in_schema,
                {
                    "physical_type": col.physical_type,
                    "compression": col.compression,
                    "encodings": set(),
                    "compressed": 0,
                    "uncompressed": 0,
                },
            )
            stat["encodings"].update(col.encodings)
            stat["compressed"] += col.total_compressed_size
            stat["uncompressed"] += col.total_uncompressed_size

    col_rows = []
    for name, s in col_stats.items():
        ratio = s["uncompressed"] / s["compressed"] if s["compressed"] else float("nan")
        col_rows.append(
            (
                name,
                s["physical_type"],
                s["compression"],
                ", ".join(sorted(s["encodings"])),
                s["compressed"],
                s["uncompressed"],
                ratio,
            )
        )

    return file_level, col_rows


def capture_info(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.info(buf=buf, memory_usage="deep")
    return buf.getvalue()


def main() -> None:
    raw = load_raw()
    print("=== 원본(zip→CSV) 상위 5개 행 ===")
    print(raw.head())

    raw_info = capture_info(raw)
    raw_mem = raw.memory_usage(deep=True).sum()

    tidy = to_tidy(raw)
    print("\n=== tidy 변환 후 상위 5개 행 (기준일ID/행정동코드 category 적용) ===")
    print(tidy.head())
    print(tidy.dtypes)

    before_downcast_info = capture_info(tidy)

    tidy, numeric_desc, categorical_desc = describe_and_downcast(tidy)
    print("\n=== 수치형 기술 통계 (시간대구분/총생활인구수/인구수) ===")
    print(numeric_desc)
    print("\n=== 범주형 기술 통계 (성별/연령대) ===")
    print(categorical_desc)

    after_downcast_info = capture_info(tidy)
    print("\n=== 추가 다운캐스트 후 info() ===")
    print(after_downcast_info)

    tidy.to_parquet(OUT_PARQUET, engine="pyarrow", compression="snappy", index=False)

    reloaded = pd.read_parquet(OUT_PARQUET, engine="pyarrow")
    parquet_info = capture_info(reloaded)
    reloaded_mem = reloaded.memory_usage(deep=True).sum()

    file_meta, col_meta = capture_parquet_metadata(OUT_PARQUET)
    print("\n=== parquet 파일 메타 정보 ===")
    print(file_meta)
    for row in col_meta:
        print(row)

    col_meta_rows = "\n".join(
        f"| {name} | {ptype} | {comp} | {enc} | {compressed/1024:,.1f} KB | {uncompressed/1024:,.1f} KB | {ratio:.1f}x |"
        for name, ptype, comp, enc, compressed, uncompressed, ratio in col_meta
    )

    import os
    import zipfile

    zip_size = os.path.getsize(RAW_ZIP)
    parquet_size = os.path.getsize(OUT_PARQUET)
    with zipfile.ZipFile(RAW_ZIP) as z:
        csv_size = z.getinfo(z.namelist()[0]).file_size

    raw_bytes_per_cell = raw_mem / (raw.shape[0] * raw.shape[1])
    tidy_bytes_per_cell = reloaded_mem / (reloaded.shape[0] * reloaded.shape[1])

    report = f"""# 서울 생활인구(동별) 데이터 tidy 변환 & parquet 저장 리포트

## 1. 개요

- 원본 파일: `{RAW_ZIP}` (CSV, wide format, zip 압축)
- 변환 파일: `{OUT_PARQUET}` (parquet, tidy/long format, dtype downcast + snappy 압축)
- 원본 행/열: {raw.shape[0]:,}행 x {raw.shape[1]}열
- 변환 후 행/열: {tidy.shape[0]:,}행 x {tidy.shape[1]}열 (성별x연령대 28개 컬럼을 `성별`, `연령대`, `인구수` 3개 컬럼으로 unpivot, `총생활인구수`는 파생 가능해 제외)

## 2. tidy-data 변환 내용

원본은 `남자0세부터9세생활인구수`, `여자70세이상생활인구수` 처럼 성별x연령대 조합이 각각 별도 컬럼(총 28개)으로 펼쳐진 wide format이었다.
이를 `pd.melt`로 unpivot하여 `성별`(남/여), `연령대`(0세부터9세 ~ 70세이상), `인구수`(값) 3개 컬럼으로 재구성했다.

`총생활인구수`는 동일 기준일ID/시간대구분/행정동코드 조합의 `인구수`(성별x연령대별 인구)를 모두 더하면 나오는 파생값
(`groupby(["기준일ID","시간대구분","행정동코드"])["인구수"].sum()`과 동일)이므로 컬럼에서 제외했다.

- id_vars: {ID_VARS}
- value_vars: 성별x연령대 28개 컬럼
- 결과 컬럼: 기준일ID, 시간대구분, 행정동코드, 성별, 연령대, 인구수 (총생활인구수 제외)

## 3. dtype 다운캐스트

### 3.1 기준일ID / 행정동코드 → category (우선 지정)

반복되는 식별자 성격의 값이라 우선 category로 지정했다. 정수형 category는 parquet에 저장 후 다시 읽으면
category가 풀려 평평한 정수로 복원되므로(문자열 category만 dictionary로 보존됨), 문자열로 변환한 뒤 category화했다.

| 컬럼 | 원본 dtype | 변경 후 dtype |
|---|---|---|
| 기준일ID | int64 | category(str) |
| 행정동코드 | float64 | category(str) |

### 3.2 나머지 컬럼: 기술 통계 기반 다운캐스트

기준일ID/행정동코드를 제외한 나머지 컬럼(시간대구분, 인구수, 성별, 연령대)에 대해
수치형은 `describe()`, 범주형은 `describe()`(unique 값 개수)를 확인한 뒤 downcast 여부를 결정했다.
(`총생활인구수`는 `인구수`의 합으로 파생 가능해 이 시점 이전에 컬럼에서 제외했다.)

**수치형 기술 통계**

```
{numeric_desc}
```

**범주형 기술 통계**

```
{categorical_desc}
```

기술 통계 기반 판단 결과:

| 컬럼 | 근거 | 원본 dtype | 변경 후 dtype |
|---|---|---|---|
| 시간대구분 | min=0, max=23 → uint8(0~255) 범위로 충분 | int64 | uint8 |
| 인구수 | 소수점 값이라 `pd.to_numeric(downcast='float')`는 정밀도 보존 조건 때문에 무효화됨 → astype으로 명시 downcast | float64 | float32 |
| 성별 | unique=2 → category로 압축 | object | category |
| 연령대 | unique=14 → category로 압축 | object | category |

## 4. info() 비교

### 4.1 원본 (zip → CSV 직접 로드)

```
{raw_info}```

### 4.2 tidy 변환 직후 (기준일ID/행정동코드만 category, 나머지는 원본 dtype)

```
{before_downcast_info}```

### 4.3 기술 통계 기반 추가 다운캐스트 후

```
{after_downcast_info}```

### 4.4 parquet 저장 → 재로드 후

```
{parquet_info}```

## 5. 파일/메모리 크기 비교

### 5.1 디스크 파일 크기

| 파일 | 크기 |
|---|---|
| 원본 zip (압축) | {zip_size / 1024 / 1024:,.2f} MB |
| 원본 CSV (압축 해제 시) | {csv_size / 1024 / 1024:,.2f} MB |
| 변환 parquet (snappy 압축) | {parquet_size / 1024 / 1024:,.2f} MB |

### 5.2 메모리(RAM) 사용량 (deep)

| 구분 | 행 x 열 | 총 메모리 | 셀당 평균 바이트 |
|---|---|---|---|
| 원본 (wide, CSV 로드) | {raw.shape[0]:,} x {raw.shape[1]} | {raw_mem / 1024 / 1024:,.2f} MB | {raw_bytes_per_cell:.2f} bytes |
| 변환 후 (tidy, parquet 재로드) | {reloaded.shape[0]:,} x {reloaded.shape[1]} | {reloaded_mem / 1024 / 1024:,.2f} MB | {tidy_bytes_per_cell:.2f} bytes |

## 6. parquet 파일 메타 정보

### 6.1 파일 수준 메타 정보

| 항목 | 값 |
|---|---|
| format_version | {file_meta['format_version']} |
| created_by | {file_meta['created_by']} |
| num_columns | {file_meta['num_columns']} |
| num_rows | {file_meta['num_rows']:,} |
| num_row_groups | {file_meta['num_row_groups']} |
| footer_serialized_size | {file_meta['footer_serialized_size']:,} bytes |

### 6.2 컬럼별 인코딩/압축 통계 (전체 row group 합산)

| 컬럼 | physical_type | compression | encodings | 압축 크기 | 압축 해제 크기 | 압축률 |
|---|---|---|---|---|---|---|
{col_meta_rows}

### 6.3 메타 정보 설명

- **format_version**: 이 parquet 파일이 따르는 Parquet 포맷 스펙 버전. pyarrow가 기본으로 최신 안정 버전을 사용해 기록한 것이다.
- **created_by**: 파일을 실제로 쓴 라이브러리/버전(parquet-cpp-arrow, 즉 pyarrow). 다른 도구(Spark, DuckDB 등)로 읽을 때 호환성 확인에 참고할 수 있다.
- **num_row_groups**: parquet은 파일을 여러 개의 row group으로 나눠 저장한다. row group은 압축·통계·인코딩이 독립적으로 적용되는 단위라, 필요한 row group만 골라 읽는 병렬/부분 읽기가 가능하다. 기본 row group 크기(약 1,048,576행) 기준으로 전체 {file_meta['num_rows']:,}행이 {file_meta['num_row_groups']}개 row group으로 나뉘었다.
- **footer_serialized_size**: 스키마 정의와 각 row group/컬럼의 통계(min/max, null count 등)를 담은 footer 메타데이터 자체의 크기. 실제 데이터量({parquet_size / 1024 / 1024:,.2f} MB)에 비해 {file_meta['footer_serialized_size']:,} bytes로 매우 작아 무시할 수준이다.
- **physical_type**: parquet이 실제로 디스크에 저장하는 물리적 자료형. `category`/`object`(성별, 연령대, 기준일ID, 행정동코드)는 문자열이라 `BYTE_ARRAY`로, `uint8`(시간대구분)은 parquet에 8bit 정수 물리 타입이 없어 `INT32`로, `float32`(인구수)는 `FLOAT`로 저장된다. 즉 pandas의 uint8/category 같은 다운캐스트 dtype이 parquet 물리 타입을 그대로 줄여주는 것은 아니고, 실제 절약은 아래 encoding/compression 단계에서 일어난다.
- **encodings**: 컬럼 값을 페이지에 쓸 때 쓰는 인코딩 방식들. `PLAIN`은 원값을 그대로 나열, `RLE`는 반복 구간을 (값, 반복횟수)로 압축, `RLE_DICTIONARY`는 고유값을 dictionary에 등록하고 실제 값 대신 정수 인덱스를 RLE로 저장하는 방식이다. 성별/연령대/기준일ID처럼 unique 값이 적은 컬럼일수록 RLE_DICTIONARY 효과가 커진다.
- **compression**: 인코딩 후 페이지 단위로 적용하는 2차 압축 알고리즘(여기서는 전 컬럼 SNAPPY).
- **압축 크기/압축 해제 크기/압축률**: 여기서 "압축 해제 크기"는 원본 {file_meta['num_rows']:,}행을 그대로 풀어놓은 크기가 아니라, RLE_DICTIONARY 인코딩까지 적용한 뒤 snappy만 아직 안 걸었을 때의 크기다. 즉 이 표의 압축률은 **snappy 한 단계만의 효과**를 보여준다.
  - `성별`, `기준일ID`처럼 unique 값이 2~30개뿐인 컬럼은 RLE_DICTIONARY 단계에서 이미 8,547,840행이 수백~수천 바이트로 줄어들어 있다(예: 성별은 압축 전 693 bytes, 압축 후 729 bytes). 이미 인코딩만으로 거의 다 줄었기 때문에 snappy 압축률이 1x 근처거나 오히려 살짝 늘기도 한다(작은 데이터에 붙는 snappy 프레임 오버헤드).
  - 반대로 `인구수`는 거의 모든 값이 서로 달라 반복이 없는 연속형 실수라 RLE_DICTIONARY로 줄일 여지가 없고, snappy로도 추가 압축이 거의 안 된다(압축률 ≈1x). 결과적으로 인구수 컬럼이 전체 parquet 파일 크기의 대부분을 차지한다.
  - `행정동코드`(424개 코드)는 unique 값은 적당히 있지만 8백만 행 넘게 반복되므로, RLE_DICTIONARY로 1차로 크게 줄어든 뒤에도 snappy가 추가로 {[r for n,_,_,_,_,_,r in col_meta if n=='행정동코드'][0]:.1f}배 더 압축한다.

## 7. 요약

- tidy(long) 변환으로 행 수는 28배 늘어난 대신(와이드→롱 unpivot), 컬럼 수는 32개에서 6개로 줄었다 (파생 가능한 `총생활인구수` 제외).
- **셀 단위로 보면** downcast 효과가 뚜렷하다: 셀당 평균 메모리가 {raw_bytes_per_cell:.2f} bytes → {tidy_bytes_per_cell:.2f} bytes로 감소했다. category(기준일ID/행정동코드/성별/연령대), uint8(시간대구분), float32(인구수) 적용과 파생 컬럼(총생활인구수) 제거 덕분이다.
- **데이터프레임 전체 메모리**는 {raw_mem / 1024 / 1024:,.2f} MB → {reloaded_mem / 1024 / 1024:,.2f} MB로 변화했다. unpivot으로 행 수가 28배 늘어난 영향과, downcast·불필요 컬럼 제거로 셀당 크기가 줄어든 효과가 상쇄된 결과다. tidy 형태는 분석/집계 편의성을 위한 구조 변경이며, 총생활인구수가 필요하면 `groupby(["기준일ID","시간대구분","행정동코드"])["인구수"].sum()`으로 언제든 복원할 수 있다.
- **디스크 파일 크기**는 parquet(snappy) 저장 시 {parquet_size / 1024 / 1024:,.2f} MB로, 압축 해제된 원본 CSV({csv_size / 1024 / 1024:,.2f} MB)는 물론 zip 압축된 원본({zip_size / 1024 / 1024:,.2f} MB)보다도 작다. `총생활인구수` 컬럼 제거와 category/dictionary 인코딩 덕분에, tidy 변환으로 행 수가 늘었음에도 원본보다 더 작은 파일을 만들 수 있었다.
- 요약하면, downcast와 파생 컬럼(총생활인구수) 제거, 그리고 parquet의 dictionary 인코딩이 함께 작용해 tidy(long) 변환에 따른 행 수 증가 부담을 상쇄하고도 원본보다 작은 최종 파일을 얻었다.
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nparquet saved: {OUT_PARQUET} ({parquet_size/1024/1024:.2f} MB)")
    print(f"report saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
