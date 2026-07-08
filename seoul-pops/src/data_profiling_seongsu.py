"""성수동(성수1가1동/1가2동/2가1동/2가3동)만 추출해 ydata-profiling 리포트를 생성한다.

- extract_dong.py로 parquet 필터 pushdown을 걸어 성수동 데이터만 가져온다(전체 850만 행을
  메모리에 올리지 않음).
- ydata-profiling(fg-data-profiling 요청을 Python 버전 문제로 대체한 원 패키지)으로 프로파일링.
"""

import sys

import koreanize_matplotlib  # noqa: F401 (한글 폰트를 matplotlib 전역에 등록)
import matplotlib.font_manager as fm

# ydata-profiling 내부 matplotlib 스타일이 font.sans-serif를 Arial로 강제 지정해 한글이
# 깨지는 문제 회피: AppleGothic 폰트 파일을 "Arial"이라는 이름으로 등록해 대체 매칭시킨다.
_apple_gothic = next(f for f in fm.fontManager.ttflist if f.name == "AppleGothic")
fm.fontManager.ttflist.insert(
    0,
    fm.FontEntry(
        fname=_apple_gothic.fname,
        name="Arial",
        style="normal",
        variant="normal",
        weight=400,
        stretch="normal",
        size="scalable",
    ),
)

from ydata_profiling import ProfileReport  # noqa: E402 (폰트 패치 이후에 import)

sys.path.insert(0, "src")
from extract_dong import extract_dong, find_matching_dong_names, load_dong_mapping  # noqa: E402

DONG_QUERY = ["성수동"]
OUT_HTML = "report/data_profiling_seongsu.html"


def main() -> None:
    mapping = load_dong_mapping()
    dong_names = find_matching_dong_names(mapping, DONG_QUERY)
    print(f"대상 행정동: {dong_names}")

    df = extract_dong(dong_names)
    print(f"추출 행 수: {len(df):,}")

    profile = ProfileReport(
        df,
        title=f"성수동({', '.join(dong_names)}) 생활인구 데이터 프로파일링",
        explorative=True,
    )
    profile.to_file(OUT_HTML)
    print(f"saved: {OUT_HTML}")


if __name__ == "__main__":
    main()
