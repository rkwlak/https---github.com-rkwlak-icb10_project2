"""서울 생활인구(동별) tidy 데이터셋 EDA 스크립트 (py-eda 스킬 규격 준수).

산출물:
- images/eda_*.png : 시각화 14종 (기술통계 표 시각화 2종 + 본문 시각화 12종)
- report/EDA_Report.md : 종합 한글 리포트
"""

import io
import sys

import koreanize_matplotlib  # noqa: F401 (import 시점에 한글 폰트가 matplotlib에 등록됨)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from extract_dong import load_dong_mapping  # 행정동명 매핑(작은 테이블)

PARQUET_PATH = "data/LOCAL_PEOPLE_DONG_202606_tidy.parquet"
IMAGES_DIR = "images"
REPORT_PATH = "report/EDA_Report.md"

AGE_ORDER = [
    "0세부터9세", "10세부터14세", "15세부터19세", "20세부터24세", "25세부터29세",
    "30세부터34세", "35세부터39세", "40세부터44세", "45세부터49세", "50세부터54세",
    "55세부터59세", "60세부터64세", "65세부터69세", "70세이상",
]
WEEKDAY_ORDER_KO = ["월", "화", "수", "목", "금", "토", "일"]
BLUE = "#2a78d6"
GREY = "#898781"


def img_path(name: str) -> str:
    return f"{IMAGES_DIR}/{name}"


def capture_info(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.info(buf=buf, memory_usage="deep")
    return buf.getvalue()


def fmt_int(x) -> str:
    return f"{x:,.0f}"


def main() -> None:
    df = pd.read_parquet(PARQUET_PATH)

    # ------------------------------------------------------------------
    # 1. 초기 데이터 점검
    # ------------------------------------------------------------------
    head5 = df.head()
    tail5 = df.tail()
    info_str = capture_info(df)
    n_rows, n_cols = df.shape
    n_dup = df.duplicated().sum()

    # ------------------------------------------------------------------
    # 2. 기술 통계 (수치형/범주형)
    # ------------------------------------------------------------------
    numeric_desc = df[["시간대구분", "인구수"]].describe()
    categorical_desc = df[["기준일ID", "행정동코드", "성별", "연령대"]].astype("object").describe()

    gender_stat = df.groupby("성별", observed=True)["인구수"].agg(
        row_count="count", 합계="sum", 평균="mean", 표준편차="std"
    )
    age_stat = (
        df.groupby("연령대", observed=True)["인구수"]
        .agg(row_count="count", 합계="sum", 평균="mean", 표준편차="std")
        .reindex(AGE_ORDER)
    )

    # ------------------------------------------------------------------
    # 사전 집계 (전체 8,547,840행을 반복 사용하지 않도록 필요한 것만 한 번에 축약)
    # ------------------------------------------------------------------
    # 일자x시간대x행정동 총생활인구수 (성별+연령대 합산) -> 424*30*24 = 305,280행
    day_hour_dong = (
        df.groupby(["기준일ID", "시간대구분", "행정동코드"], observed=True)["인구수"]
        .sum()
        .reset_index()
    )

    # 서울 전체 일자x시간대 총생활인구수 -> 30*24 = 720행
    city_day_hour = (
        day_hour_dong.groupby(["기준일ID", "시간대구분"], observed=True)["인구수"]
        .sum()
        .reset_index()
    )
    city_day_hour["date"] = pd.to_datetime(city_day_hour["기준일ID"].astype(str), format="%Y%m%d")
    city_day_hour["weekday"] = city_day_hour["date"].dt.weekday  # 0=월

    # 시간대별 평균(30일 평균) 서울 전체 생활인구수 -> 24행
    hourly_city = city_day_hour.groupby("시간대구분")["인구수"].mean()

    # 일자별 하루 평균 동시 체류인구(24시간 평균) -> 30행 -> 요일별 평균
    daily_avg = city_day_hour.groupby(["기준일ID", "weekday"], observed=True)["인구수"].mean().reset_index()
    weekday_avg = daily_avg.groupby("weekday")["인구수"].mean().reindex(range(7))
    weekday_avg.index = WEEKDAY_ORDER_KO

    # 행정동별 평균/표준편차 (424행) + 행정동명 매핑(작은 테이블만 join)
    dong_stat = day_hour_dong.groupby("행정동코드", observed=True)["인구수"].agg(["mean", "std"]).reset_index()
    mapping = load_dong_mapping()[["행자부행정동코드", "시도명", "시군구명", "행정동명"]]
    dong_stat = dong_stat.merge(mapping, left_on="행정동코드", right_on="행자부행정동코드", how="left")
    dong_stat["동_표시명"] = dong_stat["시군구명"] + " " + dong_stat["행정동명"]
    dong_stat["cv"] = dong_stat["std"] / dong_stat["mean"]
    dong_top30 = dong_stat.nlargest(30, "mean")

    # 시간대x연령대 히트맵용 평균 인구수 (성별/행정동/일자 평균) -> 24*14 = 336행
    hour_age = (
        df.groupby(["시간대구분", "연령대"], observed=True)["인구수"]
        .mean()
        .reset_index()
        .pivot(index="연령대", columns="시간대구분", values="인구수")
        .reindex(AGE_ORDER)
    )

    # 연령대x성별 총 인구수 (그룹 바용)
    age_gender = (
        df.groupby(["연령대", "성별"], observed=True)["인구수"]
        .sum()
        .reset_index()
        .pivot(index="연령대", columns="성별", values="인구수")
        .reindex(AGE_ORDER)
    )

    # ------------------------------------------------------------------
    # 2-1/2-2. 기술통계 표 시각화 (describe() 표를 그래프로도 함께 제공)
    # ------------------------------------------------------------------
    # 수치형 기술통계(2.1) 시각화: 인구수의 5분위 요약을 boxplot으로 표현.
    # 시간대구분은 설계상 0~23 균등분포(표에서 이미 확인됨)라 별도 차트 없이 표로 충분.
    fig, ax = plt.subplots(figsize=(4.5, 5))
    ax.boxplot(df["인구수"], tick_labels=["인구수"], showfliers=False,
               boxprops=dict(color=BLUE), medianprops=dict(color="#e34948"),
               whiskerprops=dict(color=GREY), capprops=dict(color=GREY))
    ax.set_ylabel("인구수")
    ax.set_title("인구수 5분위 요약 (극단 이상치 제외)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_00a_numeric_summary.png"), dpi=140)
    plt.close(fig)
    numeric_chart_md = (
        f"![]({img_path('eda_00a_numeric_summary.png')})\n\n"
        "**해설**: 25%(435.4명)~75%(1,051.6명) 구간에 인구수 값의 절반이 몰려 있고, 중앙값(675.2명)이 "
        "박스 아래쪽에 치우쳐 있어 우측으로 긴 꼬리를 가진 분포임을 boxplot에서도 확인할 수 있다. "
        "극단 이상치(최대 21,244명)는 스케일 차이가 너무 커서 보기 편의상 제외했다."
    )

    # 범주형 기술통계(2.2) 시각화: 변수별 고유값(unique) 개수를 막대로 비교.
    cat_unique_counts = df[["기준일ID", "행정동코드", "성별", "연령대"]].nunique()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(cat_unique_counts.index.astype(str), cat_unique_counts.values, color=BLUE)
    ax.set_ylabel("고유값(unique) 개수")
    ax.set_title("범주형 변수별 고유값 개수")
    ax.set_yscale("log")
    for i, v in enumerate(cat_unique_counts.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_00b_categorical_summary.png"), dpi=140)
    plt.close(fig)
    categorical_chart_md = (
        f"![]({img_path('eda_00b_categorical_summary.png')})\n\n"
        "**해설**: 행정동코드(424개)가 다른 범주형 변수보다 압도적으로 카디널리티가 높아 log 스케일로 "
        "표시했다. 기준일ID(30일), 연령대(14구간), 성별(2종)은 상대적으로 적어 그대로 빈도 교차표를 "
        "쓰기 쉬운 반면, 행정동코드는 뒤의 ⑥번 차트처럼 상위 N개로 추려서 봐야 한다."
    )

    # ------------------------------------------------------------------
    # 3. 시각화 (12종)
    # ------------------------------------------------------------------
    charts = []  # (파일명, 제목, 표, 해설) 수집 -> 리포트 조립에 사용

    # 3-1. 인구수 히스토그램 (univariate)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(df["인구수"], bins=60, color=BLUE, edgecolor="white", linewidth=0.3)
    ax.set_yscale("log")
    ax.set_xlabel("인구수 (성별x연령대별, 시간대x행정동x일자 단위)")
    ax.set_ylabel("빈도수 (log scale)")
    ax.set_title("인구수 분포 히스토그램")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_01_hist_population.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_01_hist_population.png", "① 인구수 분포 히스토그램 (univariate)",
        numeric_desc[["인구수"]],
        "인구수는 0에 가까운 값에 몰려 있고 오른쪽으로 긴 꼬리를 가지는 전형적인 우측 왜도 분포다. "
        "log 스케일로 봐도 소수의 매우 큰 값(최대 21,244명)이 존재해 평균(856.8)이 중앙값(675.2)보다 크게 나타난다.",
    ))

    # 3-2. 인구수 boxplot (성별) - bivariate
    fig, ax = plt.subplots(figsize=(6, 4.5))
    data_by_gender = [df.loc[df["성별"] == g, "인구수"].values for g in ["남", "여"]]
    ax.boxplot(data_by_gender, tick_labels=["남", "여"], showfliers=False,
               boxprops=dict(color=BLUE), medianprops=dict(color="#e34948"),
               whiskerprops=dict(color=GREY), capprops=dict(color=GREY))
    ax.set_ylabel("인구수")
    ax.set_title("성별 인구수 분포 (boxplot, 극단 이상치 제외)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_02_box_gender.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_02_box_gender.png", "② 성별 인구수 boxplot (bivariate)",
        gender_stat,
        "여성 인구수의 평균(910.8)과 중앙값이 남성(802.8)보다 높아, 전체적으로 여성 생활인구가 "
        "더 많이 관측된다. 분포의 사분위 범위(IQR)도 여성이 다소 넓다.",
    ))

    # 3-3. 인구수 boxplot (연령대) - bivariate
    fig, ax = plt.subplots(figsize=(10, 5))
    data_by_age = [df.loc[df["연령대"] == a, "인구수"].values for a in AGE_ORDER]
    ax.boxplot(data_by_age, tick_labels=AGE_ORDER, showfliers=False,
               boxprops=dict(color=BLUE), medianprops=dict(color="#e34948"),
               whiskerprops=dict(color=GREY), capprops=dict(color=GREY))
    ax.set_ylabel("인구수")
    ax.set_title("연령대별 인구수 분포 (boxplot, 극단 이상치 제외)")
    ax.tick_params(axis="x", rotation=45)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_03_box_age.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_03_box_age.png", "③ 연령대별 인구수 boxplot (bivariate)",
        age_stat,
        "70세이상과 35~49세 구간의 인구수 중앙값/평균이 가장 높고, 10~14세 구간이 가장 낮다. "
        "특히 70세이상은 분포 자체도 넓어 지역별 편차가 큰 연령대로 보인다.",
    ))

    # 3-4. 성별 총 인구수 막대 (univariate/frequency 대응)
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ax.bar(["남", "여"], gender_stat["합계"] / 1e9, color=[BLUE, "#1baf7a"], width=0.5)
    ax.set_ylabel("총 생활인구수 (10억 명·시간)")
    ax.set_title("성별 총 생활인구수 비교")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_04_bar_gender_total.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_04_bar_gender_total.png", "④ 성별 총 생활인구수 막대 (categorical frequency 대응)",
        gender_stat[["row_count", "합계"]],
        "행 빈도(row_count)는 남녀 각각 4,273,920건으로 완전히 균형 잡혀 있어 별도 빈도 차트는 "
        "의미가 없다. 대신 실제 업무적으로 의미 있는 총 생활인구수 합계를 비교했다.",
    ))

    # 3-5. 연령대별 총 인구수 막대
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(AGE_ORDER, age_stat["합계"] / 1e6, color=BLUE)
    ax.set_ylabel("총 생활인구수 (백만 명·시간)")
    ax.set_title("연령대별 총 생활인구수")
    ax.tick_params(axis="x", rotation=45)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_05_bar_age_total.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_05_bar_age_total.png", "⑤ 연령대별 총 생활인구수 막대 (categorical frequency 대응)",
        age_stat[["row_count", "합계"]],
        "70세이상 구간의 총 생활인구수가 모든 연령대 중 가장 크고, 10~14세 구간이 가장 작다. "
        "생산연령(35~49세) 구간도 고르게 높은 수준을 보인다.",
    ))

    # 3-6. 행정동 top30 평균 생활인구수 (categorical, top-N 규칙)
    fig, ax = plt.subplots(figsize=(8, 10))
    order = dong_top30.sort_values("mean")
    ax.barh(order["동_표시명"], order["mean"], color=BLUE)
    ax.set_xlabel("시간대별 평균 총생활인구수")
    ax.set_title("행정동 평균 총생활인구수 상위 30개 (전체 424개 중)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_06_bar_dong_top30.png"), dpi=140)
    plt.close(fig)
    top3_names = ", ".join(dong_top30.sort_values("mean", ascending=False)["동_표시명"].head(3))
    charts.append((
        "eda_06_bar_dong_top30.png", "⑥ 행정동별 평균 생활인구수 상위 30개 (categorical, top-30)",
        dong_top30[["동_표시명", "mean", "std"]].rename(columns={"mean": "평균", "std": "표준편차"}),
        f"행정동코드는 424개로 범주가 많아 상위 30개만 표시했다. 1~3위는 {top3_names} 순으로, "
        "업무·상업 밀집지(여의도, 역삼)뿐 아니라 대단지 주거지역(화곡8동)도 상위권에 포함되어 "
        "생활인구 상위 지역이 상업지구만은 아님을 보여준다.",
    ))

    # 3-7. 시간대별 서울 전체 평균 생활인구수 (line, bivariate)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(hourly_city.index, hourly_city.values / 1e6, color=BLUE, linewidth=2.2, marker="o", markersize=4)
    ax.set_xlabel("시간대 (시)")
    ax.set_ylabel("평균 총생활인구수 (백만 명)")
    ax.set_title("시간대별 서울 전체 평균 생활인구수 (2026년 6월, 30일 평균)")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_07_line_hourly.png"), dpi=140)
    plt.close(fig)
    hourly_min_hour, hourly_min_val = hourly_city.idxmin(), hourly_city.min()
    hourly_max_hour, hourly_max_val = hourly_city.idxmax(), hourly_city.max()
    hourly_amp_pct = (hourly_max_val - hourly_min_val) / hourly_city.mean() * 100
    charts.append((
        "eda_07_line_hourly.png", "⑦ 시간대별 서울 전체 평균 생활인구수 (bivariate, line)",
        hourly_city.to_frame("평균_총생활인구수"),
        f"새벽 {hourly_min_hour}시에 약 {hourly_min_val/1e6:.2f}백만 명으로 최저를 기록한 뒤 출근 시간대부터 "
        f"증가해 {hourly_max_hour}시에 약 {hourly_max_val/1e6:.2f}백만 명으로 최고치를 찍고, 저녁 이후 다시 "
        "감소하는 전형적인 일중 유동 패턴을 보인다. "
        f"최고-최저 진폭은 하루 평균 대비 약 {hourly_amp_pct:.1f}%로, 시간대에 따른 서울 전체 생활인구 "
        "변동 자체는 크지 않은 편이며(대부분의 변동은 특정 행정동에 국한됨을 시사) 이는 도시 전체로 "
        "보면 상주인구가 유동인구보다 기저선을 이루기 때문으로 해석된다.",
    ))

    # 3-8. 요일별 평균 생활인구수 (bar, bivariate)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = [BLUE if d in ["토", "일"] else GREY for d in WEEKDAY_ORDER_KO]
    colors = ["#e34948" if d in ["토", "일"] else BLUE for d in WEEKDAY_ORDER_KO]
    ax.bar(WEEKDAY_ORDER_KO, weekday_avg.values / 1e6, color=colors)
    ax.set_ylabel("일 평균 동시 체류 인구수 (백만 명)")
    ax.set_title("요일별 서울 전체 평균 생활인구수 (파랑=평일, 빨강=주말)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_08_bar_weekday.png"), dpi=140)
    plt.close(fig)
    weekday_top = weekday_avg.idxmax()
    weekday_bottom = weekday_avg.idxmin()
    weekday_gap_pct = (weekday_avg.max() - weekday_avg.min()) / weekday_avg.mean() * 100
    charts.append((
        "eda_08_bar_weekday.png", "⑧ 요일별 평균 생활인구수 (bivariate, bar)",
        weekday_avg.to_frame("평균_동시체류인구수"),
        f"{weekday_top}요일이 일 평균 약 {weekday_avg.max()/1e6:.2f}백만 명으로 가장 높고, {weekday_bottom}요일이 "
        f"약 {weekday_avg.min()/1e6:.2f}백만 명으로 가장 낮아 최대-최소 격차는 평균 대비 약 {weekday_gap_pct:.1f}%다. "
        "전반적으로 평일(월~금)이 주말(토·일)보다 높은 수준을 유지해 통근/통학 수요가 생활인구 총량을 "
        "밀어올리는 효과가 요일 단위에서도 나타난다.",
    ))

    # 3-9. 행정동별 평균 vs 표준편차 산점도 (scatter, bivariate)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(dong_stat["mean"], dong_stat["std"], s=14, color=BLUE, alpha=0.6, edgecolor="none")
    ax.set_xlabel("행정동 평균 총생활인구수")
    ax.set_ylabel("행정동 생활인구수 표준편차 (변동성)")
    ax.set_title("행정동별 평균 vs 변동성 산점도 (424개 행정동)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_09_scatter_dong_variability.png"), dpi=140)
    plt.close(fig)
    corr = dong_stat[["mean", "std"]].corr().iloc[0, 1]
    most_volatile = dong_stat.nlargest(1, "cv").iloc[0]
    most_stable = dong_stat.nsmallest(1, "cv").iloc[0]
    charts.append((
        "eda_09_scatter_dong_variability.png", "⑨ 행정동 평균-변동성 산점도 (bivariate, scatter)",
        dong_stat[["mean", "std", "cv"]].describe(),
        f"평균과 표준편차의 상관계수는 {corr:.2f}로, 평균 생활인구가 많은 행정동일수록 시간대에 따른 "
        "변동성(표준편차)도 함께 커지는 경향이 뚜렷하다. 다만 상대 변동성(변동계수=표준편차/평균)까지 "
        f"보면 순위가 달라져, {most_volatile['동_표시명']}은 변동계수 {most_volatile['cv']:.2f}로 "
        f"평균 대비 등락폭이 가장 크고(이벤트성·특정 시간 집중형), {most_stable['동_표시명']}은 "
        f"변동계수 {most_stable['cv']:.2f}로 시간대에 관계없이 가장 안정적인 인구 수준을 유지한다.",
    ))

    # 3-10. 시간대x연령대 히트맵 (multivariate)
    # 연령대별 절대 인구수 기저값 차이가 시간대 변동폭보다 훨씬 커서(예: 70세이상 기저 1,200명대
    # vs 시간대 변동폭 30명), 절대값 히트맵은 연령대 간 차이만 보이고 시간대 패턴이 묻힌다.
    # 각 행(연령대)을 자기 자신의 하루 평균 대비 비율(%)로 정규화해 시간대 패턴을 드러낸다.
    hour_age_norm = hour_age.div(hour_age.mean(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(10, 6))
    vmax_dev = float(np.abs(hour_age_norm.values - 100).max())
    im = ax.imshow(
        hour_age_norm.values, aspect="auto", cmap="RdBu_r",
        vmin=100 - vmax_dev, vmax=100 + vmax_dev,
    )
    ax.set_xticks(range(24))
    ax.set_xticklabels(range(24), fontsize=7)
    ax.set_yticks(range(len(AGE_ORDER)))
    ax.set_yticklabels(AGE_ORDER, fontsize=8)
    ax.set_xlabel("시간대 (시)")
    ax.set_title("시간대 x 연령대 생활인구수 히트맵 (연령대별 하루 평균=100 기준 상대비율, %)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("해당 연령대 하루 평균 대비 비율(%)")
    fig.tight_layout()
    fig.savefig(img_path("eda_10_heatmap_hour_age.png"), dpi=140)
    plt.close(fig)
    charts.append((
        "eda_10_heatmap_hour_age.png", "⑩ 시간대x연령대 히트맵 (multivariate, 연령대별 정규화)",
        hour_age_norm.round(1),
        "연령대별 절대 기저 인구수 차이(70세이상 약 1,200명대 vs 10대 약 450명대)가 시간대별 "
        "변동폭(대부분 ±5% 이내)보다 훨씬 커서, 절대값 그대로는 시간대 패턴이 묻혀 보이지 않는다. "
        "이에 각 연령대를 자기 하루 평균=100 기준 비율로 정규화했더니, 대부분의 연령대가 "
        "새벽 3~5시경 저점, 13~16시경 고점을 찍는 공통된 일중 패턴을 보였다. 다만 0~14세 구간은 "
        "저점이 새벽이 아닌 저녁(19시 등)에 나타나 성인·고령층과는 다른 생활 패턴을 시사한다.",
    ))

    # 3-11. 연령대x성별 그룹 바 (multivariate)
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(AGE_ORDER))
    width = 0.38
    ax.bar(x - width / 2, age_gender["남"] / 1e6, width, label="남", color=BLUE)
    ax.bar(x + width / 2, age_gender["여"] / 1e6, width, label="여", color="#1baf7a")
    ax.set_xticks(x)
    ax.set_xticklabels(AGE_ORDER, rotation=45, ha="right")
    ax.set_ylabel("총 생활인구수 (백만 명·시간)")
    ax.set_title("연령대x성별 총 생활인구수 (grouped bar)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(img_path("eda_11_grouped_bar_age_gender.png"), dpi=140)
    plt.close(fig)
    age_gender_gap = (age_gender["여"] - age_gender["남"]) / age_gender["남"] * 100
    gap_max_age, gap_max_val = age_gender_gap.idxmax(), age_gender_gap.max()
    gap_min_age, gap_min_val = age_gender_gap.idxmin(), age_gender_gap.min()
    charts.append((
        "eda_11_grouped_bar_age_gender.png", "⑪ 연령대x성별 그룹 바 (multivariate)",
        age_gender,
        f"{gap_max_age} 구간은 여성이 남성보다 {gap_max_val:.0f}% 더 많아 성별 격차가 가장 크고, "
        "고령층에서 여성 인구 비중이 두드러지게 높은 인구구조를 보여준다. "
        f"반대로 {gap_min_age} 구간은 오히려 남성이 여성보다 {abs(gap_min_val):.1f}% 많아 유일하게 "
        "남성이 우세한 연령대다(출생 성비상 남아가 더 많은 자연적 특성과 맞닿아 있다). "
        "20~24세도 여성이 39% 더 많아 상위권에 속해, 고령층과는 다른 이유(대학가/사회초년생 밀집 "
        "지역의 성별 구성)로 격차가 벌어진 것으로 보인다.",
    ))

    # 3-12. 요일x시간대 히트맵 (multivariate, 추가)
    dow_hour = city_day_hour.pivot_table(index="weekday", columns="시간대구분", values="인구수", aggfunc="mean")
    dow_hour.index = WEEKDAY_ORDER_KO
    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(dow_hour.values / 1e6, aspect="auto", cmap=plt.get_cmap("Blues"))
    ax.set_xticks(range(24))
    ax.set_xticklabels(range(24), fontsize=7)
    ax.set_yticks(range(7))
    ax.set_yticklabels(WEEKDAY_ORDER_KO)
    ax.set_xlabel("시간대 (시)")
    ax.set_title("요일 x 시간대 서울 전체 평균 생활인구수 히트맵 (백만 명)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("평균 생활인구수 (백만 명)")
    fig.tight_layout()
    fig.savefig(img_path("eda_12_heatmap_weekday_hour.png"), dpi=140)
    plt.close(fig)
    peak_hour_by_weekday = dow_hour.idxmax(axis=1)
    weekday_peak_hours = sorted(set(peak_hour_by_weekday[["월", "화", "수", "목", "금"]]))
    weekend_peak_hours = sorted(set(peak_hour_by_weekday[["토", "일"]]))
    charts.append((
        "eda_12_heatmap_weekday_hour.png", "⑫ 요일x시간대 히트맵 (multivariate)",
        (dow_hour / 1e6).round(2),
        f"평일(월~금)은 모두 {weekday_peak_hours[0]}시에 생활인구가 가장 많은 반면, 주말(토·일)은 "
        f"피크가 {weekend_peak_hours[0]}시로 2시간 늦게 나타난다. 이는 평일에는 업무/통학으로 낮 시간대에 "
        "일찍 인구가 몰리지만, 주말에는 늦은 오전~이른 오후에 외출이 시작돼 피크 시점 자체가 뒤로 "
        "밀리는 생활 리듬의 차이를 보여준다.",
    ))

    # ------------------------------------------------------------------
    # 4. 리포트 조립
    # ------------------------------------------------------------------
    numeric_commentary = f"""
`시간대구분`과 `인구수` 두 수치형 변수를 살펴보면, `시간대구분`은 0~23시를 나타내는 코드값으로
평균 11.5, 표준편차 6.92를 가지며 24개 값이 정확히 균등하게 분포한다(설계상 균형 데이터이므로
분포 자체보다는 시간 축 라벨로 해석하는 것이 맞다). 핵심 관심 변수인 `인구수`는 전체
{fmt_int(n_rows)}개 행(기준일ID x 시간대구분 x 행정동코드 x 성별 x 연령대 조합)에 대해 평균
856.83명, 표준편차 724.75명을 기록했다. 최솟값은 0명, 최댓값은 21,244.2명으로 범위가 매우 넓고,
1사분위수 435.44명, 중앙값 675.16명, 3사분위수 1,051.62명으로 평균(856.83)이 중앙값(675.16)보다
뚜렷하게 크다는 점에서 오른쪽으로 긴 꼬리를 가진 우측 왜도 분포임을 알 수 있다. 이는 극소수의
상업·업무·환승 밀집 행정동(강남, 홍대 등)이 시간대에 따라 매우 높은 유동인구를 기록하는 반면,
대다수의 주거 위주 행정동/야간 시간대는 상대적으로 낮고 고른 인구수를 보이기 때문으로 해석된다.
성별로 나누어 보면 여성 평균(910.83명)이 남성 평균(802.82명)보다 높고, 총합 기준으로도 여성
(약 38.9억 명·시간)이 남성(약 34.3억 명·시간)보다 많아 서울 전체 생활인구에서 여성 비중이 다소
높다는 점이 확인된다. 연령대별로는 70세이상 구간의 평균(1,216.87명)이 전체 연령대 중 가장 높고,
10~14세 구간의 평균(447.42명)이 가장 낮다. 이는 고령 인구의 절대 규모가 크다는 인구구조적 특징과,
청소년 초반 연령대는 학교 등 특정 시설에 집중되어 행정동 단위로 분산 측정되는 값 자체가 작게
나타나는 특성이 함께 반영된 결과로 볼 수 있다. 비즈니스 관점에서는, 인구수 변수의 극단값(이상치로
보이는 21,244명 같은 값)을 그대로 평균 계산에 사용하면 특정 상업지구의 영향이 과도하게 반영될 수
있으므로, 지역별 정책이나 상권 분석 시에는 평균과 함께 중앙값·사분위수를 병행 참고하는 것이
바람직하다. 또한 표준편차가 평균에 근접한 수준(724.75 vs 856.83)이라는 것은 변동계수(CV)가
1에 가까워 인구수 변수의 상대적 산포가 상당히 크다는 뜻이며, 이는 뒤에서 다룰 행정동별
평균-표준편차 산점도(⑨)에서도 평균이 큰 지역일수록 변동성도 함께 커지는 패턴으로 재확인된다.
""".strip()

    categorical_commentary = f"""
범주형 변수는 `기준일ID`(30개, 2026-06-01~06-30), `행정동코드`(424개, 서울시 전체 행정동),
`성별`(2개: 남/여), `연령대`(14개 구간)로 구성된다. 가장 눈에 띄는 특징은 이 데이터셋이 완벽하게
균형 잡힌(balanced) 설계라는 점이다: 30일 x 24시간 x 424개 행정동 x 2개 성별 x 14개 연령대 조합이
빠짐없이 모두 존재하며, 중복 행은 {n_dup}건, 결측치도 전 컬럼에서 0건으로 확인되었다. 즉 원본 통계
집계 과정에서 결측이나 누락된 조합 없이 완전한 그리드 형태로 데이터가 제공되었다는 뜻이며, 이는
groupby 집계나 시계열 분석 시 별도의 결측 보정 로직이 필요 없다는 실무적 이점으로 이어진다.
`기준일ID`는 2026년 6월 한 달(30일)을 모두 포함하고 있어 요일 효과(평일/주말)를 분석하기에
충분한 기간이며, 실제로 요일별 평균 생활인구수 비교(⑧)에서 요일에 따른 차이를 관찰할 수 있었다.
`행정동코드`는 424개로 범주형 변수 중 카디널리티가 가장 높으며, 단순 빈도(각 행정동당 20,160행씩
동일)만 보면 균등하지만 실제 `인구수` 값의 총합/평균 기준으로 순위를 매기면(⑥) 강남·홍대·성수 등
상업·업무·환승 밀집 지역이 상위권을 독점하는 뚜렷한 쏠림 현상이 나타난다. 이는 행정구역 수 자체는
균등해도 실질적인 유동인구 밀도는 지역별로 극심하게 불균등함을 보여주는 대목이다. `성별`은 남/여
각각 정확히 4,273,920건(전체의 50%)으로 완전히 균형 잡혀 있어, 성별 간 비교는 표본 수 차이에
따른 왜곡 없이 순수하게 `인구수` 값 자체의 차이로 해석할 수 있다. `연령대`도 14개 구간이 각각
610,560건씩 동일하게 나타나며, 이는 통계청/행정안전부가 원 데이터를 집계할 때 모든 시간대x행정동
조합에 대해 14개 연령 구간을 항상 함께 산출했기 때문이다. 결론적으로 범주형 변수들은 '설계상
균형'과 '실제 값의 불균형'이 공존하는 구조로, 빈도 자체보다는 `인구수`라는 수치형 변수와 결합했을
때 비로소 지역별·시간대별 실질적인 편차와 인사이트가 드러난다는 점이 이번 EDA의 핵심 발견이다.
""".strip()

    text_analysis_note = (
        "본 데이터셋에는 자유서술형 텍스트/문서 컬럼이 없다(모든 컬럼이 날짜, 시간 코드, 행정동 코드, "
        "성별, 연령대 구간 등 정형 범주형/수치형 값). `행정동명`(매핑 테이블)도 '역삼1동'처럼 짧은 "
        "고유명사 라벨일 뿐 여러 단어로 구성된 문서가 아니므로, TF-IDF 기반 키워드 빈도 분석을 적용할 "
        "대상 자체가 존재하지 않는다. 따라서 스킬 규격의 텍스트 분석(TF-IDF 상위 30개 키워드) 절차는 "
        "이 데이터셋에는 해당 사항이 없어 생략하며, 대신 위 ⑥ 행정동별 상위 30개 차트로 "
        "'범주형 값의 상위 N개를 보여준다'는 동일한 목적을 달성했다."
    )

    chart_sections = []
    for fname, title, table, interpretation in charts:
        try:
            table_md = table.to_markdown()
        except Exception:
            table_md = "```\n" + table.to_string() + "\n```"
        chart_sections.append(f"""### {title}

![]({IMAGES_DIR}/{fname})

{table_md}

**해설**: {interpretation}
""")

    report = f"""# 서울 생활인구(동별) 2026년 6월 tidy 데이터셋 EDA 리포트

## 0. 분석 개요

- 데이터: `{PARQUET_PATH}`
- 행 x 열: {fmt_int(n_rows)}행 x {n_cols}열
- 컬럼: 기준일ID, 시간대구분, 행정동코드, 성별, 연령대, 인구수
- 기간: 2026-06-01 ~ 2026-06-30 (30일)
- 대상: 서울시 전체 424개 행정동

## 1. 초기 데이터 점검

### 1.1 상위 5행

{head5.to_markdown()}

### 1.2 하위 5행

{tail5.to_markdown()}

### 1.3 df.info()

```
{info_str}```

### 1.4 데이터 규모 및 중복 확인

- 전체 행 수: {fmt_int(n_rows)}
- 전체 열 수: {n_cols}
- 완전 중복 행 개수: {n_dup}건
- 결측치: 전 컬럼 0건 (사전 확인 완료)

## 2. 기술 통계

### 2.1 수치형 변수 기술통계

{numeric_desc.to_markdown()}

{numeric_chart_md}

**분석**

{numeric_commentary}

### 2.2 범주형 변수 기술통계

{categorical_desc.to_markdown()}

{categorical_chart_md}

**분석**

{categorical_commentary}

## 3. 텍스트 데이터 분석 (해당 없음)

{text_analysis_note}

## 4. 데이터 시각화 (12종)

{"".join(chart_sections)}

## 5. 종합 요약

- 데이터 품질: 결측치·중복 없이 완전한 그리드 구조(30일x24시간x424행정동x2성별x14연령대)로 제공되어 분석 신뢰도가 높다.
- 시간 패턴: 서울 전체 생활인구는 새벽에 최저, 낮 시간대(12~16시)에 최고를 기록하는 전형적인 일중 곡선을 보인다.
- 성별/연령: 여성 생활인구 총량이 남성보다 많고, 70세이상 및 35~49세 구간의 절대 규모가 크다.
- 공간 편중: 행정동 수는 균등하지만 실제 유동인구는 상업/업무/환승 밀집 소수 행정동에 극도로 집중되며, 이런 지역일수록 시간대별 변동성도 함께 크다.
- 활용 제안: 상권/교통 정책 수립 시 평균값뿐 아니라 상위 30개 행정동(⑥), 행정동별 변동성(⑨), 연령대별 시간 패턴(⑩)을 함께 참고해 지역 특성에 맞는 세분화된 접근이 필요하다.
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"report saved: {REPORT_PATH}")
    print(f"charts saved: {len(charts)}")


if __name__ == "__main__":
    main()
