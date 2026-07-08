"""ydata-profiling(구 fg-data-profiling 요청 대체)으로 tidy 데이터셋 자동 프로파일링 리포트를 생성한다."""

import koreanize_matplotlib  # noqa: F401 (한글 폰트를 matplotlib 전역에 등록)
import matplotlib.font_manager as fm
import pandas as pd

# ydata-profiling은 내부 matplotlib 스타일 컨텍스트(visualisation/context.py)에서
# font.sans-serif를 ["Arial", "Liberation Sans", ...]로 강제로 덮어써서, koreanize-matplotlib로
# 설정한 전역 폰트가 무시되고 한글 글리프가 깨진다(Glyph missing 경고). 이를 피하려고 실제
# 폰트 파일은 한글이 지원되는 AppleGothic을 쓰되, matplotlib 폰트 매니저에는 이름을
# "Arial"로 등록해 ydata-profiling이 Arial을 찾을 때 이 폰트가 대신 매칭되도록 한다.
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

PARQUET_PATH = "data/LOCAL_PEOPLE_DONG_202606_tidy.parquet"
OUT_HTML = "report/data_profiling_report.html"


def main() -> None:
    df = pd.read_parquet(PARQUET_PATH)

    profile = ProfileReport(
        df,
        title="서울 생활인구(동별) 2026년 6월 - 데이터 프로파일링",
        explorative=True,
    )
    profile.to_file(OUT_HTML)
    print(f"saved: {OUT_HTML}")


if __name__ == "__main__":
    main()
