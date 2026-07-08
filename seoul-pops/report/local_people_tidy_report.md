# 서울 생활인구(동별) 데이터 tidy 변환 & parquet 저장 리포트

## 1. 개요

- 원본 파일: `data/LOCAL_PEOPLE_DONG_202606.zip` (CSV, wide format, zip 압축)
- 변환 파일: `data/LOCAL_PEOPLE_DONG_202606_tidy.parquet` (parquet, tidy/long format, dtype downcast + snappy 압축)
- 원본 행/열: 305,280행 x 32열
- 변환 후 행/열: 8,547,840행 x 6열 (성별x연령대 28개 컬럼을 `성별`, `연령대`, `인구수` 3개 컬럼으로 unpivot, `총생활인구수`는 파생 가능해 제외)

## 2. tidy-data 변환 내용

원본은 `남자0세부터9세생활인구수`, `여자70세이상생활인구수` 처럼 성별x연령대 조합이 각각 별도 컬럼(총 28개)으로 펼쳐진 wide format이었다.
이를 `pd.melt`로 unpivot하여 `성별`(남/여), `연령대`(0세부터9세 ~ 70세이상), `인구수`(값) 3개 컬럼으로 재구성했다.

`총생활인구수`는 동일 기준일ID/시간대구분/행정동코드 조합의 `인구수`(성별x연령대별 인구)를 모두 더하면 나오는 파생값
(`groupby(["기준일ID","시간대구분","행정동코드"])["인구수"].sum()`과 동일)이므로 컬럼에서 제외했다.

- id_vars: ['기준일ID', '시간대구분', '행정동코드', '총생활인구수']
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
              시간대구분           인구수
count  8.547840e+06  8.547840e+06
mean   1.150000e+01  8.568292e+02
std    6.922187e+00  7.247550e+02
min    0.000000e+00  0.000000e+00
25%    5.750000e+00  4.354366e+02
50%    1.150000e+01  6.751572e+02
75%    1.725000e+01  1.051624e+03
max    2.300000e+01  2.124420e+04
```

**범주형 기술 통계**

```
             성별      연령대
count   8547840  8547840
unique        2       14
top           남   0세부터9세
freq    4273920   610560
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
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 305280 entries, 0 to 305279
Data columns (total 32 columns):
 #   Column           Non-Null Count   Dtype  
---  ------           --------------   -----  
 0   기준일ID            305280 non-null  int64  
 1   시간대구분            305280 non-null  int64  
 2   행정동코드            305280 non-null  int64  
 3   총생활인구수           305280 non-null  float64
 4   남자0세부터9세생활인구수    305280 non-null  float64
 5   남자10세부터14세생활인구수  305280 non-null  float64
 6   남자15세부터19세생활인구수  305280 non-null  float64
 7   남자20세부터24세생활인구수  305280 non-null  float64
 8   남자25세부터29세생활인구수  305280 non-null  float64
 9   남자30세부터34세생활인구수  305280 non-null  float64
 10  남자35세부터39세생활인구수  305280 non-null  float64
 11  남자40세부터44세생활인구수  305280 non-null  float64
 12  남자45세부터49세생활인구수  305280 non-null  float64
 13  남자50세부터54세생활인구수  305280 non-null  float64
 14  남자55세부터59세생활인구수  305280 non-null  float64
 15  남자60세부터64세생활인구수  305280 non-null  float64
 16  남자65세부터69세생활인구수  305280 non-null  float64
 17  남자70세이상생활인구수     305280 non-null  float64
 18  여자0세부터9세생활인구수    305280 non-null  float64
 19  여자10세부터14세생활인구수  305280 non-null  float64
 20  여자15세부터19세생활인구수  305280 non-null  float64
 21  여자20세부터24세생활인구수  305280 non-null  float64
 22  여자25세부터29세생활인구수  305280 non-null  float64
 23  여자30세부터34세생활인구수  305280 non-null  float64
 24  여자35세부터39세생활인구수  305280 non-null  float64
 25  여자40세부터44세생활인구수  305280 non-null  float64
 26  여자45세부터49세생활인구수  305280 non-null  float64
 27  여자50세부터54세생활인구수  305280 non-null  float64
 28  여자55세부터59세생활인구수  305280 non-null  float64
 29  여자60세부터64세생활인구수  305280 non-null  float64
 30  여자65세부터69세생활인구수  305280 non-null  float64
 31  여자70세이상생활인구수     305280 non-null  float64
dtypes: float64(29), int64(3)
memory usage: 74.5 MB
```

### 4.2 tidy 변환 직후 (기준일ID/행정동코드만 category, 나머지는 원본 dtype)

```
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 8547840 entries, 0 to 8547839
Data columns (total 6 columns):
 #   Column  Dtype   
---  ------  -----   
 0   기준일ID   category
 1   시간대구분   int64   
 2   행정동코드   category
 3   성별      object  
 4   연령대     object  
 5   인구수     float64 
dtypes: category(2), float64(1), int64(1), object(2)
memory usage: 1.6 GB
```

### 4.3 기술 통계 기반 추가 다운캐스트 후

```
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 8547840 entries, 0 to 8547839
Data columns (total 6 columns):
 #   Column  Dtype   
---  ------  -----   
 0   기준일ID   category
 1   시간대구분   uint8   
 2   행정동코드   category
 3   성별      category
 4   연령대     category
 5   인구수     float32 
dtypes: category(4), float32(1), uint8(1)
memory usage: 81.6 MB
```

### 4.4 parquet 저장 → 재로드 후

```
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 8547840 entries, 0 to 8547839
Data columns (total 6 columns):
 #   Column  Dtype   
---  ------  -----   
 0   기준일ID   category
 1   시간대구분   uint8   
 2   행정동코드   category
 3   성별      category
 4   연령대     category
 5   인구수     float32 
dtypes: category(4), float32(1), uint8(1)
memory usage: 81.6 MB
```

## 5. 파일/메모리 크기 비교

### 5.1 디스크 파일 크기

| 파일 | 크기 |
|---|---|
| 원본 zip (압축) | 41.60 MB |
| 원본 CSV (압축 해제 시) | 103.39 MB |
| 변환 parquet (snappy 압축) | 39.10 MB |

### 5.2 메모리(RAM) 사용량 (deep)

| 구분 | 행 x 열 | 총 메모리 | 셀당 평균 바이트 |
|---|---|---|---|
| 원본 (wide, CSV 로드) | 305,280 x 32 | 74.53 MB | 8.00 bytes |
| 변환 후 (tidy, parquet 재로드) | 8,547,840 x 6 | 81.57 MB | 1.67 bytes |

## 6. parquet 파일 메타 정보

### 6.1 파일 수준 메타 정보

| 항목 | 값 |
|---|---|
| format_version | 2.6 |
| created_by | parquet-cpp-arrow version 21.0.0 |
| num_columns | 6 |
| num_rows | 8,547,840 |
| num_row_groups | 9 |
| footer_serialized_size | 9,592 bytes |

### 6.2 컬럼별 인코딩/압축 통계 (전체 row group 합산)

| 컬럼 | physical_type | compression | encodings | 압축 크기 | 압축 해제 크기 | 압축률 |
|---|---|---|---|---|---|---|
| 기준일ID | BYTE_ARRAY | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 3.1 KB | 7.1 KB | 2.3x |
| 시간대구분 | INT32 | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 4.9 KB | 60.5 KB | 12.4x |
| 행정동코드 | BYTE_ARRAY | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 1,430.4 KB | 9,453.3 KB | 6.6x |
| 성별 | BYTE_ARRAY | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 0.7 KB | 0.7 KB | 1.0x |
| 연령대 | BYTE_ARRAY | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 2.1 KB | 3.3 KB | 1.6x |
| 인구수 | FLOAT | SNAPPY | PLAIN, RLE, RLE_DICTIONARY | 38,585.9 KB | 38,584.1 KB | 1.0x |

### 6.3 메타 정보 설명

- **format_version**: 이 parquet 파일이 따르는 Parquet 포맷 스펙 버전. pyarrow가 기본으로 최신 안정 버전을 사용해 기록한 것이다.
- **created_by**: 파일을 실제로 쓴 라이브러리/버전(parquet-cpp-arrow, 즉 pyarrow). 다른 도구(Spark, DuckDB 등)로 읽을 때 호환성 확인에 참고할 수 있다.
- **num_row_groups**: parquet은 파일을 여러 개의 row group으로 나눠 저장한다. row group은 압축·통계·인코딩이 독립적으로 적용되는 단위라, 필요한 row group만 골라 읽는 병렬/부분 읽기가 가능하다. 기본 row group 크기(약 1,048,576행) 기준으로 전체 8,547,840행이 9개 row group으로 나뉘었다.
- **footer_serialized_size**: 스키마 정의와 각 row group/컬럼의 통계(min/max, null count 등)를 담은 footer 메타데이터 자체의 크기. 실제 데이터量(39.10 MB)에 비해 9,592 bytes로 매우 작아 무시할 수준이다.
- **physical_type**: parquet이 실제로 디스크에 저장하는 물리적 자료형. `category`/`object`(성별, 연령대, 기준일ID, 행정동코드)는 문자열이라 `BYTE_ARRAY`로, `uint8`(시간대구분)은 parquet에 8bit 정수 물리 타입이 없어 `INT32`로, `float32`(인구수)는 `FLOAT`로 저장된다. 즉 pandas의 uint8/category 같은 다운캐스트 dtype이 parquet 물리 타입을 그대로 줄여주는 것은 아니고, 실제 절약은 아래 encoding/compression 단계에서 일어난다.
- **encodings**: 컬럼 값을 페이지에 쓸 때 쓰는 인코딩 방식들. `PLAIN`은 원값을 그대로 나열, `RLE`는 반복 구간을 (값, 반복횟수)로 압축, `RLE_DICTIONARY`는 고유값을 dictionary에 등록하고 실제 값 대신 정수 인덱스를 RLE로 저장하는 방식이다. 성별/연령대/기준일ID처럼 unique 값이 적은 컬럼일수록 RLE_DICTIONARY 효과가 커진다.
- **compression**: 인코딩 후 페이지 단위로 적용하는 2차 압축 알고리즘(여기서는 전 컬럼 SNAPPY).
- **압축 크기/압축 해제 크기/압축률**: 여기서 "압축 해제 크기"는 원본 8,547,840행을 그대로 풀어놓은 크기가 아니라, RLE_DICTIONARY 인코딩까지 적용한 뒤 snappy만 아직 안 걸었을 때의 크기다. 즉 이 표의 압축률은 **snappy 한 단계만의 효과**를 보여준다.
  - `성별`, `기준일ID`처럼 unique 값이 2~30개뿐인 컬럼은 RLE_DICTIONARY 단계에서 이미 8,547,840행이 수백~수천 바이트로 줄어들어 있다(예: 성별은 압축 전 693 bytes, 압축 후 729 bytes). 이미 인코딩만으로 거의 다 줄었기 때문에 snappy 압축률이 1x 근처거나 오히려 살짝 늘기도 한다(작은 데이터에 붙는 snappy 프레임 오버헤드).
  - 반대로 `인구수`는 거의 모든 값이 서로 달라 반복이 없는 연속형 실수라 RLE_DICTIONARY로 줄일 여지가 없고, snappy로도 추가 압축이 거의 안 된다(압축률 ≈1x). 결과적으로 인구수 컬럼이 전체 parquet 파일 크기의 대부분을 차지한다.
  - `행정동코드`(424개 코드)는 unique 값은 적당히 있지만 8백만 행 넘게 반복되므로, RLE_DICTIONARY로 1차로 크게 줄어든 뒤에도 snappy가 추가로 6.6배 더 압축한다.

## 7. 요약

- tidy(long) 변환으로 행 수는 28배 늘어난 대신(와이드→롱 unpivot), 컬럼 수는 32개에서 6개로 줄었다 (파생 가능한 `총생활인구수` 제외).
- **셀 단위로 보면** downcast 효과가 뚜렷하다: 셀당 평균 메모리가 8.00 bytes → 1.67 bytes로 감소했다. category(기준일ID/행정동코드/성별/연령대), uint8(시간대구분), float32(인구수) 적용과 파생 컬럼(총생활인구수) 제거 덕분이다.
- **데이터프레임 전체 메모리**는 74.53 MB → 81.57 MB로 변화했다. unpivot으로 행 수가 28배 늘어난 영향과, downcast·불필요 컬럼 제거로 셀당 크기가 줄어든 효과가 상쇄된 결과다. tidy 형태는 분석/집계 편의성을 위한 구조 변경이며, 총생활인구수가 필요하면 `groupby(["기준일ID","시간대구분","행정동코드"])["인구수"].sum()`으로 언제든 복원할 수 있다.
- **디스크 파일 크기**는 parquet(snappy) 저장 시 39.10 MB로, 압축 해제된 원본 CSV(103.39 MB)는 물론 zip 압축된 원본(41.60 MB)보다도 작다. `총생활인구수` 컬럼 제거와 category/dictionary 인코딩 덕분에, tidy 변환으로 행 수가 늘었음에도 원본보다 더 작은 파일을 만들 수 있었다.
- 요약하면, downcast와 파생 컬럼(총생활인구수) 제거, 그리고 parquet의 dictionary 인코딩이 함께 작용해 tidy(long) 변환에 따른 행 수 증가 부담을 상쇄하고도 원본보다 작은 최종 파일을 얻었다.
