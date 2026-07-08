"""연남동/성수동의 시간대별x연령대별 생활인구수를 행정동 색상별 선그래프로 그린다.

- 행정동코드 매핑에서 '연남동', '성수동'에 해당하는 모든 행정동코드를 찾고,
  parquet 필터 pushdown으로 해당 행정동 데이터만 추출한다 (src/extract_dong.py).
- 연령대(14개 구간)를 세로로 나열한 패싯(facet)으로 배치해 '연령대가 y축을 따라
  나열되는' 형태를 만들고, 각 패싯 안에서 x=시간대(0~23시), y=생활인구수,
  선 색상=행정동명으로 그린다.
- 하루 인구는 요일에 따라 등락이 있으므로, 한 달(30일)치 평균으로 '전형적인 하루'
  패턴을 보여준다.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from extract_dong import extract_dong, find_matching_dong_names, load_dong_mapping

QUERIES = ["연남동", "성수동"]
IMAGE_PATH = "images/dong_hourly_age_lineplot.png"

AGE_ORDER = [
    "0세부터9세",
    "10세부터14세",
    "15세부터19세",
    "20세부터24세",
    "25세부터29세",
    "30세부터34세",
    "35세부터39세",
    "40세부터44세",
    "45세부터49세",
    "50세부터54세",
    "55세부터59세",
    "60세부터64세",
    "65세부터69세",
    "70세이상",
]

# 카테고리 팔레트(fixed order) - dataviz 스킬 references/palette.md 의 categorical 슬롯 1~5
DONG_COLORS = {
    "연남동": "#2a78d6",  # slot 1 blue
    "성수1가1동": "#1baf7a",  # slot 2 aqua
    "성수1가2동": "#eda100",  # slot 3 yellow
    "성수2가1동": "#008300",  # slot 4 green
    "성수2가3동": "#4a3aa7",  # slot 5 violet
}

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False


def load_data() -> pd.DataFrame:
    mapping = load_dong_mapping()
    dong_names = find_matching_dong_names(mapping, QUERIES)
    return extract_dong(dong_names)


def aggregate_typical_day(df: pd.DataFrame) -> pd.DataFrame:
    # 성별 두 값을 더해 총 인구수로 만들고(groupby 키에서 성별 제외),
    # 이후 기준일ID(30일)에 대해 평균을 내 '전형적인 하루' 시간대별 곡선을 만든다.
    daily = (
        df.groupby(["행정동명", "연령대", "시간대구분", "기준일ID"], observed=True)["인구수"]
        .sum()
        .reset_index()
    )
    typical = (
        daily.groupby(["행정동명", "연령대", "시간대구분"], observed=True)["인구수"]
        .mean()
        .reset_index()
    )
    typical["연령대"] = pd.Categorical(typical["연령대"], categories=AGE_ORDER, ordered=True)
    return typical.sort_values(["연령대", "행정동명", "시간대구분"])


def plot(typical: pd.DataFrame) -> None:
    dong_names = sorted(typical["행정동명"].unique(), key=lambda n: list(DONG_COLORS).index(n))

    fig, axes = plt.subplots(
        nrows=len(AGE_ORDER),
        ncols=1,
        figsize=(9, 2 * len(AGE_ORDER)),
        sharex=True,
        sharey=False,
    )

    for i, (ax, age) in enumerate(zip(axes, AGE_ORDER)):
        sub = typical[typical["연령대"] == age]
        for dong in dong_names:
            line = sub[sub["행정동명"] == dong].sort_values("시간대구분")
            ax.plot(
                line["시간대구분"],
                line["인구수"],
                color=DONG_COLORS[dong],
                linewidth=2,
                solid_capstyle="round",
                label=dong,
            )
        ax.set_ylabel(age, rotation=0, ha="right", va="center", fontsize=9, color="#52514e")
        ax.set_xlim(0, 23)
        ax.set_xticks(range(0, 24, 3))
        ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")

        # y축 값(생활인구수)을 완전히 숨기지 않고 3개 정도만 옅게 표시해
        # 패싯마다 실제 규모를 가늠할 수 있게 한다.
        ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=3))
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.tick_params(axis="y", labelleft=True, length=0, labelsize=7, colors="#898781")

        # x축 눈금 숫자는 맨 아래 패싯에만 표시해 반복을 줄인다.
        ax.tick_params(axis="x", colors="#898781", labelbottom=(i == len(AGE_ORDER) - 1))

    axes[-1].set_xlabel("시간대 (시)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=len(dong_names),
        bbox_to_anchor=(0.5, 1.0),
        frameon=False,
    )
    fig.suptitle(
        "연남동 vs 성수동 — 시간대x연령대별 생활인구수 (2026년 6월, 요일 평균)",
        y=1.02,
        fontsize=13,
    )

    fig.tight_layout()
    fig.savefig(IMAGE_PATH, dpi=150, bbox_inches="tight")
    print(f"saved: {IMAGE_PATH}")


def main() -> None:
    df = load_data()
    print(f"추출된 행정동: {sorted(df['행정동명'].unique())}")
    print(f"추출 행 수: {len(df):,}")

    typical = aggregate_typical_day(df)
    plot(typical)


if __name__ == "__main__":
    main()
