"""
사람인 데이터 직무 채용공고 분석 대시보드
"""
import sqlite3
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─── 경로 ────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "saramin.db"

# ─── 스킬 패턴 사전 ──────────────────────────────────────────────────────────
SKILL_PATTERNS = {
    "Python":       [r'\bpython\b', r'파이썬'],
    "SQL":          [r'\bsql\b', r'쿼리\s*작성', r'\bMySQL\b', r'\bPostgres', r'\bOracle\b', r'\bMS-?SQL\b'],
    "딥러닝":        [r'딥\s*러닝', r'deep\s*learning'],
    "LLM":          [r'\bllm\b', r'large\s*language\s*model', r'대규모\s*언어\s*모델'],
    "머신러닝":      [r'머신\s*러닝', r'machine\s*learning', r'\bml\b(?=\s*(모델|알고리즘|엔지니어|개발|경험))'],
    "포트폴리오":    [r'포트폴리오', r'portfolio'],
    "AWS":          [r'\baws\b', r'amazon\s*web\s*services'],
    "PyTorch":      [r'\bpytorch\b', r'파이토치'],
    "GitHub":       [r'\bgithub\b', r'\bgit\b'],
    "생성형AI":      [r'생성형\s*ai', r'generative\s*ai', r'\bgpt\b', r'\bchatgpt\b'],
    "Docker":       [r'\bdocker\b', r'도커'],
    "논문":          [r'논문', r'학술지', r'저술'],
    "영어":          [r'영어\s*(?:능통|가능|우수|회화|커뮤니케이션)', r'toeic', r'opic', r'toefl', r'영문\s*서류'],
    "JavaScript":   [r'\bjavascript\b', r'\bjs\b', r'\btypescript\b', r'자바스크립트'],
    "Java":         [r'\bjava\b(?!\s*script)', r'자바(?!\s*스크립트)'],
    "TensorFlow":   [r'\btensorflow\b', r'텐서플로'],
    "GCP":          [r'\bgcp\b', r'\bgoogle\s*cloud\b', r'구글\s*클라우드'],
    "Excel":        [r'\bexcel\b', r'엑셀', r'\bvba\b'],
    "PostgreSQL":   [r'\bpostgresql\b', r'\bpostgres\b'],
    "Azure":        [r'\bazure\b'],
    "통계분석":      [r'통계\s*(?:분석|지식|기법|모델)', r'회귀\s*분석', r'가설\s*검증', r'A/B\s*테스트'],
    "Spark":        [r'\bspark\b', r'\bapache\s*spark\b', r'스파크'],
    "Airflow":      [r'\bairflow\b', r'\bapache\s*airflow\b'],
    "Kafka":        [r'\bkafka\b', r'카프카'],
    "Kubernetes":   [r'\bkubernetes\b', r'\bk8s\b', r'쿠버네티스'],
    "Tableau":      [r'\btableau\b', r'타블로', r'태블로'],
    "Power BI":     [r'\bpower\s*bi\b'],
    "NLP":          [r'\bnlp\b', r'자연어\s*처리'],
    "scikit-learn": [r'\bscikit[\-\s]learn\b', r'\bsklearn\b'],
    "R":            [r'\bRstudio\b', r'\bggplot\b', r'\bdplyr\b', r'R\s*언어', r'R\s*프로그래밍'],
    "MongoDB":      [r'\bmongodb\b'],
    "Redis":        [r'\bredis\b'],
    "dbt":          [r'\bdbt\b'],
    "정보처리기사":  [r'정보\s*처리\s*기사'],
    "SQLD":         [r'\bsqld\b'],
    "ADP":          [r'\badp\b(?!\s*\w)', r'데이터\s*분석\s*전문가'],
    "ADsP":         [r'\badsp\b'],
    "빅데이터분석기사": [r'빅\s*데이터\s*분석\s*기사'],
    "Looker":       [r'\blooker\b'],
    "GA4":          [r'\bga4\b', r'\bgoogle\s*analytics\b'],
    "Hadoop":       [r'\bhadoop\b'],
    "인턴경험":      [r'인턴\s*(?:경험|경력|출신)', r'인턴십'],
    "Kaggle":       [r'\bkaggle\b', r'캐글'],
}

SKILL_CATEGORY = {
    "Python": "언어", "SQL": "언어", "JavaScript": "언어",
    "Java": "언어", "Scala": "언어", "R": "언어",
    "Excel": "시각화/BI", "Tableau": "시각화/BI", "Power BI": "시각화/BI",
    "Looker": "시각화/BI", "GA4": "시각화/BI",
    "PostgreSQL": "DB", "MongoDB": "DB", "Redis": "DB",
    "AWS": "클라우드", "GCP": "클라우드", "Azure": "클라우드",
    "Spark": "인프라", "Airflow": "인프라", "Kafka": "인프라",
    "Docker": "인프라", "Kubernetes": "인프라", "dbt": "인프라", "Hadoop": "인프라",
    "머신러닝": "AI/ML", "딥러닝": "AI/ML", "NLP": "AI/ML",
    "LLM": "AI/ML", "생성형AI": "AI/ML", "TensorFlow": "AI/ML",
    "PyTorch": "AI/ML", "scikit-learn": "AI/ML", "통계분석": "AI/ML",
    "SQLD": "자격증", "ADsP": "자격증", "ADP": "자격증",
    "빅데이터분석기사": "자격증", "정보처리기사": "자격증",
    "영어": "외국어",
    "GitHub": "경험/포트폴리오", "포트폴리오": "경험/포트폴리오",
    "논문": "경험/포트폴리오", "Kaggle": "경험/포트폴리오", "인턴경험": "경험/포트폴리오",
}

CAT_COLOR = {
    "언어":         "#4C78A8",
    "AI/ML":        "#E45756",
    "클라우드":      "#F58518",
    "인프라":        "#72B7B2",
    "시각화/BI":     "#54A24B",
    "DB":           "#EECA3B",
    "경험/포트폴리오": "#B279A2",
    "외국어":        "#FF9DA6",
    "자격증":        "#9D755D",
}

JOB_CATEGORIES = {
    "데이터분석가":       [r'데이터\s*분석가', r'data\s*analyst', r'비즈니스\s*분석', r'\bBA\b', r'BI\s*분석'],
    "데이터사이언티스트":  [r'데이터\s*사이언티스트', r'data\s*scientist', r'\bDS\b'],
    "데이터엔지니어":     [r'데이터\s*엔지니어', r'data\s*engineer', r'\bDE\b', r'데이터\s*파이프라인', r'ETL'],
    "AI/ML엔지니어":     [r'ai\s*엔지니어', r'ml\s*엔지니어', r'머신러닝\s*엔지니어', r'딥러닝\s*엔지니어',
                          r'mlops', r'machine\s*learning\s*engineer'],
    "BI분석가":          [r'bi\s*(?:분석|개발|엔지니어)', r'비즈니스\s*인텔리전스', r'대시보드', r'시각화\s*전문'],
}


def make_pattern(patterns):
    combined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


COMPILED_SKILLS = {k: make_pattern(v) for k, v in SKILL_PATTERNS.items()}
COMPILED_JOBS   = {k: make_pattern(v) for k, v in JOB_CATEGORIES.items()}

# ─── Gap 분석 상수 ────────────────────────────────────────────────────────────
GAP_REPORT_PATH = Path(__file__).parent.parent.parent / "linkareer" / "report" / "gap_analysis.json"
CERT_SKILLS = {"ADsP", "SQLD", "ADP", "빅데이터분석기사", "정보처리기사"}

LEARN_TIME: Dict[str, str] = {
    "Python": "1~3개월", "SQL": "1~2개월", "R": "2~3개월",
    "Excel": "2~4주", "JavaScript": "2~4개월", "Java": "3~6개월",
    "머신러닝": "2~4개월", "딥러닝": "3~5개월", "LLM": "2~3개월",
    "PyTorch": "2~4개월", "TensorFlow": "2~4개월", "scikit-learn": "1~2개월",
    "통계분석": "2~3개월", "NLP": "2~4개월", "생성형AI": "1~2개월",
    "AWS": "1~2개월", "GCP": "1~2개월", "Azure": "1~2개월",
    "Docker": "2~4주", "Kubernetes": "1~3개월", "Airflow": "1~2개월",
    "Spark": "2~3개월", "Kafka": "1~2개월", "dbt": "2~4주",
    "GitHub": "1~2주", "Tableau": "1개월", "Power BI": "1개월",
    "PostgreSQL": "1~2개월", "MongoDB": "1개월", "Redis": "2~4주",
    "Looker": "1개월", "GA4": "2~4주", "Hadoop": "1~2개월",
}

SKILL_TIPS: Dict[str, str] = {
    "Python":    "pandas·numpy 기초 → kaggle 입문 대회 → GitHub 프로젝트 공개",
    "SQL":       "프로그래머스 SQL 고득점 Kit → HackerRank SQL 100제 (SQLD 자격증보다 실무 쿼리 경험이 핵심)",
    "머신러닝":   "scikit-learn 공식 튜토리얼 → kaggle 노트북 포크 → 직접 모델 설계",
    "딥러닝":     "PyTorch or TensorFlow 중 선택 → 논문 구현 → 개인 프로젝트",
    "LLM":       "OpenAI API → LangChain → RAG 프로젝트 구현 (구직자 준비율 0% — 차별화 최고 포인트)",
    "AWS":       "AWS Free Tier + S3·EC2·RDS 실습 → Solutions Architect Associate 자격증",
    "Docker":    "Dockerfile 작성 → docker-compose → 기존 프로젝트에 컨테이너 적용",
    "GitHub":    "공개 저장소 3개 이상 + 상세 README → 면접관이 가장 먼저 확인합니다",
    "Tableau":   "Tableau Public(무료)으로 공개 데이터 대시보드 제작 → 포트폴리오 링크",
    "Power BI":  "Microsoft Learn 무료 과정 → 실제 업무 데이터로 보고서 제작",
    "Airflow":   "로컬 Docker 환경 설정 → DAG 작성 → 파이프라인 프로젝트",
    "통계분석":   "통계학 기초(분포·가설검증·회귀) → Python(scipy·statsmodels)로 실습",
    "Spark":     "PySpark 입문 → Databricks 무료 커뮤니티 에디션 실습",
    "생성형AI":   "프롬프트 엔지니어링 → Hugging Face 모델 파인튜닝 → 서비스 배포",
}

JOB_FIT_DEF: Dict[str, set] = {
    "데이터분석가":      {"SQL","Python","Excel","Tableau","Power BI","통계분석","GA4","Looker"},
    "데이터사이언티스트": {"Python","머신러닝","딥러닝","PyTorch","TensorFlow","통계분석","SQL","NLP"},
    "데이터엔지니어":    {"Python","SQL","Spark","Airflow","Kafka","Docker","dbt","Kubernetes","Hadoop"},
    "AI/ML엔지니어":    {"딥러닝","LLM","PyTorch","NLP","생성형AI","Python","Docker"},
    "BI분석가":         {"Tableau","Power BI","SQL","Excel","Looker","GA4"},
}



# ─── 데이터 로드 & 분석 ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_and_analyze():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT j.job_id, j.company, j.title, j.tags, j.experience, j.education,
               COALESCE(d.requirements,'') as req,
               COALESCE(d.preferred,'')    as pref,
               COALESCE(d.job_desc,'')     as job_desc,
               COALESCE(d.full_text,'')    as full_text,
               j.location
        FROM jobs j
        LEFT JOIN job_details d ON j.job_id = d.job_id
    """)
    rows = cur.fetchall()
    conn.close()

    records = []
    for row in rows:
        job_id, company, title, tags_json, experience, education, req, pref, job_desc, full_text, location = row
        tags = json.loads(tags_json) if tags_json else []

        all_text  = f"{title} {req} {pref} {job_desc} {full_text}".lower()
        req_text  = req.lower()
        pref_text = pref.lower()

        # 직무 분류
        combo = f"{title} {' '.join(tags)}".lower()
        job_cat = "기타데이터직무"
        for cat, pat in COMPILED_JOBS.items():
            if pat.search(combo):
                job_cat = cat
                break

        # 경력 분류
        exp_cat = "미분류"
        if experience:
            if re.search(r'신입', experience):
                exp_cat = "신입포함"
            elif re.search(r'경력\s*무관', experience):
                exp_cat = "경력무관"
            else:
                m = re.search(r'경력\s*(\d+)년', experience)
                if m:
                    yr = int(m.group(1))
                    exp_cat = "1~2년" if yr <= 2 else ("3~4년" if yr <= 4 else "5년↑")

        # 스킬 매칭
        skills_all  = [k for k, p in COMPILED_SKILLS.items() if p.search(all_text)]
        skills_req  = [k for k, p in COMPILED_SKILLS.items() if p.search(req_text)]
        skills_pref = [k for k, p in COMPILED_SKILLS.items() if p.search(pref_text)]

        records.append({
            "job_id":      job_id,
            "company":     company,
            "title":       title,
            "education":   education,
            "location":    location,
            "job_cat":     job_cat,
            "exp_cat":     exp_cat,
            "skills_all":  skills_all,
            "skills_req":  skills_req,
            "skills_pref": skills_pref,
        })

    return records


def compute_freq(records, field="skills_all"):
    total  = len(records)
    cnt    = Counter()
    for r in records:
        for s in set(r[field]):
            cnt[s] += 1
    rows = [{"스킬": k, "공고수": v, "비율(%)": round(v/total*100, 1),
             "카테고리": SKILL_CATEGORY.get(k, "기타")} for k, v in cnt.most_common()]
    return pd.DataFrame(rows), total


# ─── 색상 헬퍼 ───────────────────────────────────────────────────────────────
def bar_colors(df):
    return [CAT_COLOR.get(c, "#888") for c in df["카테고리"]]


@st.cache_data(ttl=300)
def load_gap_data():
    if not GAP_REPORT_PATH.exists():
        return None
    with open(GAP_REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ─── 페이지 설정 ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="사람인 데이터직무 분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
[data-testid="stMetricLabel"] { font-size: 0.85rem; color: #888; }
.section-title {
    font-size: 1.15rem; font-weight: 700; color: #1a1a2e;
    border-left: 4px solid #4C78A8; padding-left: 10px; margin: 1rem 0 0.5rem;
}
.section-title-dark {
    font-size: 1.1rem; font-weight: 700; color: #e2e8f0;
    border-left: 4px solid #4a9eff; padding-left: 10px; margin: 1rem 0 0.5rem;
}
.insight-box {
    background: #f0f4ff; border-radius: 10px; padding: 14px 18px;
    margin: 8px 0; border-left: 4px solid #4C78A8; font-size: 0.92rem;
}
.tag { display:inline-block; background:#4C78A8; color:#fff;
       border-radius:12px; padding:2px 10px; margin:2px; font-size:0.8rem; }
.tag-red { background:#E45756; }
.tag-green { background:#54A24B; }
</style>
""", unsafe_allow_html=True)

# ─── 데이터 로드 ─────────────────────────────────────────────────────────────
with st.spinner("DB에서 데이터를 불러오는 중..."):
    records = load_and_analyze()

total = len(records)
companies = set(r["company"] for r in records)

# ─── 사이드바 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.saramin.co.kr/favicon.ico", width=32)
    st.title("분석 필터")

    job_cats  = ["전체"] + sorted(set(r["job_cat"] for r in records))
    sel_cat   = st.selectbox("직무 분류", job_cats)

    exp_cats  = ["전체"] + sorted(set(r["exp_cat"] for r in records if r["exp_cat"] != "미분류"))
    sel_exp   = st.selectbox("경력 조건", exp_cats)

    top_n = st.slider("상위 N개 스킬 표시", 10, 40, 20)

    st.markdown("---")
    st.caption("📅 수집일: 2026-07-04")
    st.caption(f"총 공고: {total:,}건 / {len(companies):,}개 기업")

# ─── 필터 적용 ───────────────────────────────────────────────────────────────
filtered = records
if sel_cat != "전체":
    filtered = [r for r in filtered if r["job_cat"] == sel_cat]
if sel_exp != "전체":
    filtered = [r for r in filtered if r["exp_cat"] == sel_exp]

ftotal = len(filtered)

# ─── 헤더 ────────────────────────────────────────────────────────────────────
st.title("📊 사람인 데이터 직무 채용공고 분석")
st.markdown(f"**{sel_cat}** · **{sel_exp}** 기준 — 총 **{ftotal:,}건** 분석")

# ─── KPI 카드 ────────────────────────────────────────────────────────────────
filtered_companies = set(r["company"] for r in filtered)
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("총 공고", f"{ftotal:,}건",
              delta=f"전체 {total:,}건" if ftotal != total else None,
              delta_color="off")
with k2:
    st.metric("기업 수", f"{len(filtered_companies):,}개",
              delta=f"전체 {len(companies):,}개" if len(filtered_companies) != len(companies) else None,
              delta_color="off")
with k3:
    py_cnt = sum(1 for r in filtered if "Python" in r["skills_all"])
    st.metric("Python 요구", f"{py_cnt/ftotal*100:.1f}%" if ftotal else "0%")
with k4:
    sql_cnt = sum(1 for r in filtered if "SQL" in r["skills_all"])
    st.metric("SQL 요구", f"{sql_cnt/ftotal*100:.1f}%" if ftotal else "0%")
with k5:
    ai_cnt = sum(1 for r in filtered if any(s in r["skills_all"] for s in ["딥러닝","머신러닝","LLM","PyTorch","TensorFlow"]))
    st.metric("AI/ML 요구", f"{ai_cnt/ftotal*100:.1f}%" if ftotal else "0%")

st.divider()

# ─── 탭 구성 ─────────────────────────────────────────────────────────────────
tab_strategy, tab_req, tab_core, tab_misc1, tab_misc2 = st.tabs([
    "🎯 취업 전략 진단", "⚖️ 필수 vs 우대", "🔑 핵심 스킬",
    "📋 비고 1 (직무·조합)", "📋 비고 2 (경력·학력)",
])

# ══════════════════════════════════════════════════════════════
# TAB: 핵심 스킬
# ══════════════════════════════════════════════════════════════
with tab_core:
    df_all, _ = compute_freq(filtered, "skills_all")
    df_top    = df_all.head(top_n)

    # ── 카테고리 범례 ─────────────────────────────────────────
    legend_html = "".join(
        f'<span style="display:inline-flex;align-items:center;margin:3px 6px 3px 0;">'
        f'<span style="width:12px;height:12px;border-radius:3px;background:{c};'
        f'display:inline-block;margin-right:5px;"></span>'
        f'<span style="font-size:0.82rem;color:#444;">{cat}</span></span>'
        for cat, c in CAT_COLOR.items()
    )
    st.markdown(
        f'<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;'
        f'margin-bottom:16px;display:flex;flex-wrap:wrap;align-items:center;">'
        f'<span style="font-size:0.82rem;font-weight:600;color:#666;margin-right:10px;">카테고리</span>'
        f'{legend_html}</div>',
        unsafe_allow_html=True,
    )

    # ── TOP 5 하이라이트 카드 ─────────────────────────────────
    st.markdown('<div class="section-title">TOP 5 핵심 스킬</div>', unsafe_allow_html=True)
    top5_cols = st.columns(5)
    for i, (_, row) in enumerate(df_top.head(5).iterrows()):
        cat   = row["카테고리"]
        color = CAT_COLOR.get(cat, "#888")
        with top5_cols[i]:
            st.markdown(
                f'<div style="border-radius:12px;border:2px solid {color};'
                f'padding:16px 10px;text-align:center;background:#fff;">'
                f'<div style="font-size:1.7rem;font-weight:800;color:{color};">'
                f'{row["비율(%)"]:.1f}%</div>'
                f'<div style="font-size:1.05rem;font-weight:700;margin:4px 0 2px;color:#1a1a2e;">'
                f'{row["스킬"]}</div>'
                f'<div style="font-size:0.75rem;color:#fff;background:{color};'
                f'border-radius:10px;padding:1px 8px;display:inline-block;">{cat}</div>'
                f'<div style="font-size:0.78rem;color:#888;margin-top:6px;">'
                f'{row["공고수"]:,}건 / {ftotal:,}건</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 메인 가로 막대 차트 ───────────────────────────────────
    st.markdown(
        f'<div class="section-title">기업이 요구하는 스킬 TOP {top_n} — 공고 수 & 비율</div>',
        unsafe_allow_html=True,
    )

    # y축 라벨: "Python  [언어]" 형태로 카테고리 함께 표시
    y_labels = [
        f"{row['스킬']}  [{row['카테고리']}]"
        for _, row in df_top.iterrows()
    ]
    bar_clrs = [CAT_COLOR.get(row["카테고리"], "#888") for _, row in df_top.iterrows()]

    # 바 텍스트: 비율 + 건수를 바 끝 바깥에 표시
    bar_text = [
        f"<b>{row['비율(%)']:.1f}%</b>  {row['공고수']:,}건"
        for _, row in df_top.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_top["비율(%)"].tolist(),
        y=y_labels,
        orientation="h",
        marker=dict(
            color=bar_clrs,
            line=dict(color="rgba(0,0,0,0.08)", width=0.5),
        ),
        text=bar_text,
        textposition="outside",
        textfont=dict(size=13),
        cliponaxis=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "카테고리: %{customdata[1]}<br>"
            "요구 공고: %{customdata[2]:,}건<br>"
            "전체 비율: %{x:.1f}%<extra></extra>"
        ),
        customdata=[
            [row["스킬"], row["카테고리"], row["공고수"]]
            for _, row in df_top.iterrows()
        ],
    ))

    x_max = df_top["비율(%)"].max()
    fig.update_layout(
        height=max(500, top_n * 44),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=0, r=160, t=10, b=40),
        xaxis=dict(
            title=dict(text="전체 공고 대비 비율 (%)", font=dict(size=13)),
            range=[0, x_max * 1.35],
            gridcolor="#ebebeb",
            gridwidth=1,
            ticksuffix="%",
            tickfont=dict(size=12),
            showline=True,
            linecolor="#ddd",
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=13.5),
            ticklabeloverflow="allow",
        ),
        bargap=0.38,
    )

    # 배경 줄무늬 (짝수 항목에 연한 회색 배경)
    for i in range(0, top_n, 2):
        if i < len(df_top):
            fig.add_hrect(
                y0=i - 0.5, y1=i + 0.5,
                fillcolor="rgba(0,0,0,0.025)",
                line_width=0,
                layer="below",
            )

    st.plotly_chart(fig, use_container_width=True)

    # ── 카테고리별 트리맵 ────────────────────────────────────
    st.markdown('<div class="section-title">카테고리별 스킬 분포 (트리맵)</div>', unsafe_allow_html=True)

    tree_df = df_all.copy()
    tree_df["루트"] = "전체 스킬"
    fig_tree = px.treemap(
        tree_df,
        path=["루트", "카테고리", "스킬"],
        values="공고수",
        color="카테고리",
        color_discrete_map=CAT_COLOR,
        custom_data=["비율(%)", "공고수"],
    )
    fig_tree.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:.1f}%",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>공고 수: %{customdata[1]:,}건<br>비율: %{customdata[0]:.1f}%<extra></extra>",
    )
    fig_tree.update_layout(
        height=420,
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_tree, use_container_width=True)

    # ── 인사이트 ─────────────────────────────────────────────
    top3 = df_top.head(3)
    ai_cnt_tab = sum(
        row["공고수"] for _, row in df_all.iterrows()
        if row["카테고리"] == "AI/ML"
    )
    st.markdown(
        f'<div class="insight-box">'
        f'💡 <b>핵심 인사이트</b><br>'
        f'1위 <span class="tag">{top3.iloc[0]["스킬"]}</span> {top3.iloc[0]["비율(%)"]:.1f}% · '
        f'2위 <span class="tag">{top3.iloc[1]["스킬"]}</span> {top3.iloc[1]["비율(%)"]:.1f}% · '
        f'3위 <span class="tag">{top3.iloc[2]["스킬"]}</span> {top3.iloc[2]["비율(%)"]:.1f}%<br>'
        f'<b>AI/ML</b>(딥러닝·LLM·머신러닝·PyTorch 등) 카테고리 요구 공고가 누적 <b>{ai_cnt_tab:,}건</b>으로 '
        f'2026년 채용 시장은 <b>Python + AI</b> 역량 중심으로 재편되고 있습니다.'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# TAB: 필수 vs 우대
# ══════════════════════════════════════════════════════════════
with tab_req:
    st.markdown('<div class="section-title">필수 자격요건 vs 우대사항 비교</div>', unsafe_allow_html=True)

    df_req,  req_base  = compute_freq(filtered, "skills_req")
    df_pref, pref_base = compute_freq(filtered, "skills_pref")

    top_skills = df_all["스킬"].head(top_n).tolist()
    req_map  = dict(zip(df_req["스킬"],  df_req["비율(%)"]))
    pref_map = dict(zip(df_pref["스킬"], df_pref["비율(%)"]))

    compare_df = pd.DataFrame({
        "스킬":    top_skills,
        "필수(%)": [req_map.get(s, 0) for s in top_skills],
        "우대(%)": [pref_map.get(s, 0) for s in top_skills],
    }).sort_values("필수(%)", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="필수 자격요건",
        y=compare_df["스킬"],
        x=compare_df["필수(%)"],
        orientation="h",
        marker_color="#E45756",
        text=compare_df["필수(%)"].map(lambda x: f"{x:.1f}%"),
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="우대사항",
        y=compare_df["스킬"],
        x=compare_df["우대(%)"],
        orientation="h",
        marker_color="#4C78A8",
        text=compare_df["우대(%)"].map(lambda x: f"{x:.1f}%"),
        textposition="outside",
    ))
    fig.update_layout(
        barmode="group",
        height=max(450, top_n * 30),
        yaxis=dict(autorange="reversed"),
        xaxis_title="해당 섹션 내 비율 (%)",
        legend=dict(orientation="h", y=1.04, x=0),
        margin=dict(l=10, r=70, t=40, b=10),
        plot_bgcolor="#fafafa",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 필수 강도 Top5 / 우대 강도 Top5
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🔴 필수 요구 강도 TOP 5**")
        must_df = compare_df.nlargest(5, "필수(%)")
        for _, row in must_df.iterrows():
            st.markdown(
                f'<span class="tag tag-red">{row["스킬"]}</span> '
                f'필수 {row["필수(%)"]:.1f}% | 우대 {row["우대(%)"]:.1f}%',
                unsafe_allow_html=True
            )
    with c2:
        st.markdown("**🔵 우대 요구 강도 TOP 5**")
        nice_df = compare_df.nlargest(5, "우대(%)")
        for _, row in nice_df.iterrows():
            st.markdown(
                f'<span class="tag">{row["스킬"]}</span> '
                f'필수 {row["필수(%)"]:.1f}% | 우대 {row["우대(%)"]:.1f}%',
                unsafe_allow_html=True
            )

    st.markdown("""
    <div class="insight-box">
    💡 <b>필수 vs 우대 인사이트</b><br>
    • <b>Python·SQL·PyTorch·딥러닝</b>은 "필수 자격요건" 비율이 "우대사항"보다 훨씬 높습니다 → <b>반드시 갖춰야 할 스킬</b><br>
    • <b>LLM·AWS·논문·생성형AI</b>는 우대사항 비율이 더 높습니다 → <b>차별화 포인트</b><br>
    • 포트폴리오는 필수(0.8%)보다 우대(3.2%) 성격이 강하나, 암묵적으로 당연히 기대되는 항목입니다.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB: 비고1 — 직무별 비교 + 스킬 조합
# ══════════════════════════════════════════════════════════════
with tab_misc1:
    sub_job, sub_combo = st.tabs(["💼 직무별 비교", "🔗 스킬 조합"])

with sub_job:
    st.markdown('<div class="section-title">직무 분류 현황</div>', unsafe_allow_html=True)

    cat_cnt = Counter(r["job_cat"] for r in filtered)
    cat_df2 = pd.DataFrame(cat_cnt.most_common(), columns=["직무", "공고수"])

    c1, c2 = st.columns([1, 2])
    with c1:
        fig_pie = px.pie(cat_df2, values="공고수", names="직무",
                         color_discrete_sequence=px.colors.qualitative.Set2,
                         hole=0.45, height=320)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.dataframe(
            cat_df2.assign(비율=lambda d: (d["공고수"]/ftotal*100).round(1).map(lambda x: f"{x}%")),
            use_container_width=True, hide_index=True, height=320
        )

    # 직무별 TOP 스킬 히트맵
    st.markdown('<div class="section-title">직무 × 스킬 히트맵</div>', unsafe_allow_html=True)

    top15 = df_all["스킬"].head(15).tolist()
    job_order = [c for c in ["데이터분석가","데이터엔지니어","데이터사이언티스트","AI/ML엔지니어","BI분석가","기타데이터직무"] if c in cat_cnt]

    heat = []
    for jcat in job_order:
        jrecs = [r for r in filtered if r["job_cat"] == jcat]
        n = len(jrecs) or 1
        row_data = {}
        for sk in top15:
            cnt = sum(1 for r in jrecs if sk in r["skills_all"])
            row_data[sk] = round(cnt / n * 100, 1)
        heat.append(row_data)

    heat_df = pd.DataFrame(heat, index=job_order)

    fig_heat = px.imshow(
        heat_df,
        color_continuous_scale="Blues",
        labels=dict(color="요구 비율(%)"),
        text_auto=".0f",
        aspect="auto",
        height=350,
    )
    fig_heat.update_layout(
        xaxis_title="", yaxis_title="",
        margin=dict(t=10, b=10, l=10, r=10),
        coloraxis_colorbar=dict(title="비율(%)")
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # 직무별 TOP 5 스킬 테이블
    st.markdown('<div class="section-title">직무별 TOP 5 스킬</div>', unsafe_allow_html=True)
    cols = st.columns(len(job_order))
    for i, jcat in enumerate(job_order):
        jrecs = [r for r in filtered if r["job_cat"] == jcat]
        if not jrecs:
            continue
        cnt2 = Counter()
        for r in jrecs:
            for s in set(r["skills_all"]):
                cnt2[s] += 1
        n = len(jrecs)
        with cols[i]:
            st.markdown(f"**{jcat}**<br><small>({n}건)</small>", unsafe_allow_html=True)
            for rank, (sk, c) in enumerate(cnt2.most_common(5), 1):
                pct = c/n*100
                color = CAT_COLOR.get(SKILL_CATEGORY.get(sk, "기타"), "#888")
                st.markdown(
                    f'<div style="font-size:0.8rem; margin:2px 0;">'
                    f'<span style="color:{color}">●</span> {rank}. <b>{sk}</b> {pct:.0f}%</div>',
                    unsafe_allow_html=True
                )


with sub_combo:
    st.markdown('<div class="section-title">함께 요구되는 스킬 조합 분석</div>', unsafe_allow_html=True)

    pair_cnt   = Counter()
    triple_cnt = Counter()
    for r in filtered:
        skills = sorted(set(r["skills_all"]))
        for a, b in combinations(skills, 2):
            pair_cnt[(a, b)] += 1
        for a, b, c in combinations(skills, 3):
            triple_cnt[(a, b, c)] += 1

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**2개 스킬 조합 TOP 15**")
        pair_rows = [{"조합": f"{a} + {b}", "공고수": cnt, "비율(%)": round(cnt/ftotal*100,1)}
                     for (a,b), cnt in pair_cnt.most_common(15)]
        pair_df = pd.DataFrame(pair_rows)
        fig_pair = px.bar(pair_df, x="비율(%)", y="조합", orientation="h",
                          text="비율(%)", color="비율(%)",
                          color_continuous_scale="Blues", height=450)
        fig_pair.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_pair.update_layout(yaxis=dict(autorange="reversed"),
                               plot_bgcolor="#fafafa", showlegend=False,
                               coloraxis_showscale=False, margin=dict(t=10,b=10,l=10,r=60))
        st.plotly_chart(fig_pair, use_container_width=True)

    with c2:
        st.markdown("**3개 스킬 조합 TOP 15**")
        triple_rows = [{"조합": f"{a}+{b}+{c}", "공고수": cnt, "비율(%)": round(cnt/ftotal*100,1)}
                       for (a,b,c), cnt in triple_cnt.most_common(15)]
        triple_df = pd.DataFrame(triple_rows)
        fig_tri = px.bar(triple_df, x="비율(%)", y="조합", orientation="h",
                         text="비율(%)", color="비율(%)",
                         color_continuous_scale="Reds", height=450)
        fig_tri.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_tri.update_layout(yaxis=dict(autorange="reversed"),
                              plot_bgcolor="#fafafa", showlegend=False,
                              coloraxis_showscale=False, margin=dict(t=10,b=10,l=10,r=60))
        st.plotly_chart(fig_tri, use_container_width=True)

    # 네트워크 대체: 주요 스킬 간 공동 출현 버블 차트
    st.markdown('<div class="section-title">주요 스킬 공동 출현 매트릭스</div>', unsafe_allow_html=True)
    focus = ["Python","SQL","딥러닝","머신러닝","LLM","AWS","PyTorch","Docker","GitHub","Excel","통계분석","생성형AI"]
    mat_data = []
    for i, a in enumerate(focus):
        for j, b in enumerate(focus):
            if i < j:
                cnt = pair_cnt.get((a,b), pair_cnt.get((b,a), 0))
                mat_data.append({"스킬A": a, "스킬B": b, "공동출현": cnt, "비율": round(cnt/ftotal*100,1)})

    mat_df = pd.DataFrame(mat_data)
    fig_mat = px.scatter(mat_df, x="스킬A", y="스킬B", size="공동출현",
                         color="비율", color_continuous_scale="Blues",
                         size_max=50, height=400,
                         hover_data={"공동출현": True, "비율": ":.1f%"})
    fig_mat.update_layout(plot_bgcolor="#fafafa", margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(fig_mat, use_container_width=True)

    top3_pair = pair_rows[:3]
    st.markdown(f"""
    <div class="insight-box">
    💡 <b>스킬 조합 인사이트</b><br>
    가장 자주 함께 요구되는 조합은
    <span class="tag">{top3_pair[0]['조합']}</span>
    <span class="tag">{top3_pair[1]['조합']}</span>
    <span class="tag">{top3_pair[2]['조합']}</span> 입니다.<br>
    3개 조합에서는 <b>PyTorch + Python + 딥러닝</b>이 압도적 1위로,
    딥러닝/AI 직무에서 이 세 가지는 사실상 세트로 요구됩니다.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB: 비고2 — 경력별 비교 + 학력·자격증
# ══════════════════════════════════════════════════════════════
with tab_misc2:
    sub_exp, sub_edu = st.tabs(["📈 경력별 비교", "🎓 학력·자격증"])

with sub_exp:
    st.markdown('<div class="section-title">경력 조건별 공고 분포</div>', unsafe_allow_html=True)

    exp_order = ["신입포함", "경력무관", "1~2년", "3~4년", "5년↑"]
    exp_cnt = Counter(r["exp_cat"] for r in filtered if r["exp_cat"] != "미분류")
    exp_df = pd.DataFrame(
        [(e, exp_cnt.get(e, 0)) for e in exp_order if exp_cnt.get(e, 0) > 0],
        columns=["경력", "공고수"]
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        fig_exp = px.pie(exp_df, values="공고수", names="경력",
                         color_discrete_sequence=px.colors.qualitative.Pastel,
                         hole=0.4, height=300)
        fig_exp.update_traces(textposition="inside", textinfo="percent+label")
        fig_exp.update_layout(showlegend=False, margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig_exp, use_container_width=True)
    with c2:
        st.dataframe(
            exp_df.assign(비율=lambda d: (d["공고수"]/d["공고수"].sum()*100).round(1).map(lambda x: f"{x}%")),
            use_container_width=True, hide_index=True, height=300
        )

    # 경력별 스킬 비교 히트맵
    st.markdown('<div class="section-title">경력별 스킬 요구 비교</div>', unsafe_allow_html=True)

    exp_groups = {e: [r for r in filtered if r["exp_cat"] == e]
                  for e in exp_order if exp_cnt.get(e, 0) > 0}

    top12 = df_all["스킬"].head(15).tolist()
    exp_heat = {}
    for exp_name, recs in exp_groups.items():
        n = len(recs) or 1
        exp_heat[exp_name] = {sk: round(sum(1 for r in recs if sk in r["skills_all"])/n*100, 1) for sk in top12}

    exp_heat_df = pd.DataFrame(exp_heat).T
    exp_heat_df = exp_heat_df.loc[[e for e in exp_order if e in exp_heat_df.index]]

    fig_eh = px.imshow(
        exp_heat_df,
        color_continuous_scale="RdYlGn",
        text_auto=".0f",
        aspect="auto",
        height=280,
        labels=dict(color="비율(%)"),
    )
    fig_eh.update_layout(margin=dict(t=10,b=10,l=10,r=10),
                         xaxis_title="", yaxis_title="")
    st.plotly_chart(fig_eh, use_container_width=True)

    # 신입 vs 5년↑ 비교 레이더 차트
    st.markdown('<div class="section-title">신입포함 vs 5년↑ 스킬 레이더 비교</div>', unsafe_allow_html=True)

    radar_skills = ["Python","SQL","딥러닝","머신러닝","AWS","Docker","GitHub","영어","Excel","통계분석"]
    entry_recs  = exp_groups.get("신입포함", [])
    senior_recs = exp_groups.get("5년↑", [])

    entry_vals  = [sum(1 for r in entry_recs  if sk in r["skills_all"])/(len(entry_recs) or 1)*100 for sk in radar_skills]
    senior_vals = [sum(1 for r in senior_recs if sk in r["skills_all"])/(len(senior_recs) or 1)*100 for sk in radar_skills]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=entry_vals + [entry_vals[0]], theta=radar_skills + [radar_skills[0]],
        fill="toself", name="신입포함", line_color="#4C78A8", fillcolor="rgba(76,120,168,0.2)"
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=senior_vals + [senior_vals[0]], theta=radar_skills + [radar_skills[0]],
        fill="toself", name="5년↑", line_color="#E45756", fillcolor="rgba(228,87,86,0.2)"
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max(max(entry_vals), max(senior_vals))*1.1])),
        showlegend=True, height=400, margin=dict(t=30,b=30,l=50,r=50)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("""
    <div class="insight-box">
    💡 <b>신입 vs 경력 인사이트</b><br>
    • <b>신입</b>: Python·SQL 기초 + GitHub·포트폴리오 + 영어 비중이 상대적으로 높음<br>
    • <b>경력직(3~5년↑)</b>: SQL 비중이 더 높아지고, Java·Azure·Airflow 등 엔터프라이즈 기술 요구 증가<br>
    • 신입과 경력직 모두 Python은 가장 중요한 공통 스킬입니다.
    </div>
    """, unsafe_allow_html=True)


with sub_edu:
    st.markdown('<div class="section-title">학력 요구 분포</div>', unsafe_allow_html=True)

    edu_cnt = Counter(r["education"] for r in filtered if r["education"])
    edu_df = pd.DataFrame(edu_cnt.most_common(), columns=["학력", "공고수"])
    edu_df["비율(%)"] = (edu_df["공고수"] / edu_df["공고수"].sum() * 100).round(1)

    edu_color_map = {
        "대학교(4년)↑": "#4C78A8", "학력무관": "#72B7B2",
        "대학(2,3년)↑": "#54A24B", "석사↑": "#E45756",
        "고졸↑": "#F58518", "박사": "#B279A2",
    }

    c1, c2 = st.columns(2)
    with c1:
        fig_edu = px.pie(edu_df, values="공고수", names="학력",
                         color="학력", color_discrete_map=edu_color_map,
                         hole=0.45, height=320)
        fig_edu.update_traces(textposition="inside", textinfo="percent+label")
        fig_edu.update_layout(showlegend=True, margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig_edu, use_container_width=True)
    with c2:
        fig_edu_bar = px.bar(edu_df, x="학력", y="비율(%)",
                             color="학력", color_discrete_map=edu_color_map,
                             text="비율(%)", height=320)
        fig_edu_bar.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_edu_bar.update_layout(showlegend=False, plot_bgcolor="#fafafa",
                                  margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig_edu_bar, use_container_width=True)

    # 자격증 현황
    st.markdown('<div class="section-title">자격증 요구 현황</div>', unsafe_allow_html=True)

    cert_skills = ["정보처리기사","ADP","ADsP","빅데이터분석기사","SQLD"]
    cert_rows = []
    for cs in cert_skills:
        cnt = sum(1 for r in filtered if cs in r["skills_all"])
        req_cnt = sum(1 for r in filtered if cs in r["skills_req"])
        pref_cnt = sum(1 for r in filtered if cs in r["skills_pref"])
        cert_rows.append({
            "자격증": cs, "전체 공고수": cnt,
            "필수": req_cnt, "우대": pref_cnt,
            "비율(%)": round(cnt/ftotal*100,1) if ftotal else 0
        })
    cert_df = pd.DataFrame(cert_rows).sort_values("비율(%)", ascending=False)

    fig_cert = go.Figure()
    fig_cert.add_trace(go.Bar(name="필수", x=cert_df["자격증"], y=cert_df["필수"],
                               marker_color="#E45756"))
    fig_cert.add_trace(go.Bar(name="우대", x=cert_df["자격증"], y=cert_df["우대"],
                               marker_color="#4C78A8"))
    fig_cert.update_layout(barmode="stack", height=300,
                            yaxis_title="공고 수", plot_bgcolor="#fafafa",
                            margin=dict(t=10,b=10,l=10,r=10))
    st.plotly_chart(fig_cert, use_container_width=True)

    st.dataframe(cert_df, use_container_width=True, hide_index=True)

    # 학력별 스킬 비교
    st.markdown('<div class="section-title">학력 조건별 스킬 비교</div>', unsafe_allow_html=True)

    edu_groups = {}
    for edu_key in ["학력무관", "대학(2,3년)↑", "대학교(4년)↑", "석사↑"]:
        edu_groups[edu_key] = [r for r in filtered if r["education"] == edu_key]

    focus_skills = ["Python","SQL","딥러닝","머신러닝","LLM","AWS","PyTorch","GitHub","통계분석","논문"]
    edu_heat_data = {}
    for edu_key, recs in edu_groups.items():
        n = len(recs) or 1
        edu_heat_data[edu_key] = {sk: round(sum(1 for r in recs if sk in r["skills_all"])/n*100, 1)
                                  for sk in focus_skills}

    edu_heat_df = pd.DataFrame(edu_heat_data).T
    fig_edu_heat = px.imshow(edu_heat_df, color_continuous_scale="Blues",
                              text_auto=".0f", aspect="auto", height=280,
                              labels=dict(color="비율(%)"))
    fig_edu_heat.update_layout(margin=dict(t=10,b=10,l=10,r=10),
                                xaxis_title="", yaxis_title="")
    st.plotly_chart(fig_edu_heat, use_container_width=True)

    st.markdown(f"""
    <div class="insight-box">
    💡 <b>학력·자격증 인사이트</b><br>
    • <b>4년제 대졸 이상</b> 요구가 43.6%로 가장 많지만, <b>학력무관</b>도 28.9%로 상당합니다.<br>
    • <b>자격증(SQLD·ADsP 등)은 실제 요구 비율이 매우 낮습니다(0.2~4.3%)</b>. 자격증보다 실무 프로젝트·포트폴리오가 훨씬 중요합니다.<br>
    • <b>석사↑</b> 요구 공고에서는 <b>논문·PyTorch·통계분석</b> 비중이 급격히 높아집니다.<br>
    • 이공계 관련 전공자 우대가 많으며, 컴퓨터공학(15.5%)과 관련전공(21.4%)이 주를 이룹니다.
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB: 취업 전략 진단
# ══════════════════════════════════════════════════════════════
with tab_strategy:
    gap_data = load_gap_data()

    # ── 자격증 역설 임팩트 배너 ───────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
    border-radius:14px;padding:24px 28px;color:#fff;margin-bottom:22px;">
      <div style="font-size:1.2rem;font-weight:800;margin-bottom:14px;letter-spacing:-0.2px;">
        ⚡ 데이터 분석 취업 시장의 가장 큰 역설
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">
        <div style="background:rgba(228,87,86,0.18);border:1px solid rgba(228,87,86,0.5);
        border-radius:10px;padding:16px;">
          <div style="color:#ff9090;font-size:0.78rem;font-weight:700;letter-spacing:0.5px;margin-bottom:10px;">
            ❌ 구직자가 집중하는 것</div>
          <div style="font-size:0.9rem;line-height:2.0;">
            ADsP 취득 <b style="color:#ffb3b3;">30.2%</b> &nbsp;→&nbsp; 기업 우대 <b style="color:#ffb3b3;">0.1%</b><br>
            SQLD 취득 <b style="color:#ffb3b3;">22.6%</b> &nbsp;→&nbsp; 기업 우대 <b style="color:#ffb3b3;">0.2%</b><br>
            <span style="color:#aaa;font-size:0.78rem;">수개월을 자격증에 투자하지만…</span>
          </div>
        </div>
        <div style="background:rgba(84,162,75,0.18);border:1px solid rgba(84,162,75,0.5);
        border-radius:10px;padding:16px;">
          <div style="color:#90d98a;font-size:0.78rem;font-weight:700;letter-spacing:0.5px;margin-bottom:10px;">
            ✅ 기업이 실제로 원하는 것</div>
          <div style="font-size:0.9rem;line-height:2.0;">
            Python 요구 <b style="color:#aaffaa;">31.0%</b> &nbsp;→&nbsp; 구직자 준비 <b style="color:#aaffaa;">11.3%</b><br>
            LLM 요구 <b style="color:#aaffaa;">11.0%</b> &nbsp;→&nbsp; 구직자 준비 <b style="color:#aaffaa;">0.0%</b><br>
            <span style="color:#aaa;font-size:0.78rem;">포트폴리오·GitHub 실무 프로젝트</span>
          </div>
        </div>
      </div>
      <div style="color:#777;font-size:0.78rem;">
        * 링커리어 커뮤니티 구직자 53명 분석 × 사람인 데이터 직무 채용공고 1,550건 (2026.07)
      </div>
    </div>
    """, unsafe_allow_html=True)

    if gap_data is None:
        st.info("Gap 분석 리포트가 없습니다. `linkareer/src/gap_analysis.py`를 먼저 실행해주세요.")
    else:
        lk_data   = gap_data["linkareer"]
        sa_data   = gap_data["saramin"]
        gaps_list = gap_data["gaps"]
        demand_map = {g["skill"]: g["demand_rate"] for g in gaps_list}
        supply_map = {g["skill"]: g["supply_rate"] for g in gaps_list}

        # ── Gap 시각화: 수요 vs 공급 ─────────────────────────
        # 다크 배경 + 충분한 폰트 크기 + grouped bar (겹치지 않고 명확 비교)
        st.markdown("""
        <div style="background:#1a1a2e;border-radius:12px;padding:16px 20px 6px;margin-bottom:4px;">
          <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:4px;">
            📊 구인 수요 vs 구직 공급 비교 <span style="color:#718096;font-size:0.85rem;">(자격증 제외 · 수요 2% 이상)</span>
          </div>
          <div style="font-size:0.85rem;color:#ff9090;font-weight:600;">
            💡 Python은 기업 수요 31.0% vs 구직자 준비 11.3% — 공급이 절반 수준
          </div>
        </div>
        """, unsafe_allow_html=True)

        DARK_BG   = "#1a1a2e"
        DARK_PLOT = "#16213e"

        gc_data = sorted(
            [g for g in gaps_list if g["skill"] not in CERT_SKILLS and g["demand_rate"] > 1.5],
            key=lambda x: -x["demand_rate"],
        )[:14]  # TOP 14개만

        if gc_data:
            skills_c  = [g["skill"] for g in gc_data]
            demand_c  = [g["demand_rate"] for g in gc_data]
            supply_c  = [g["supply_rate"] for g in gc_data]
            # Gap이 큰 항목 강조색
            bar_colors_d = ["#ff6b6b" if g["gap"] > 10 else "#fa8072" for g in gc_data]

            fig_gap = go.Figure()
            # 구인 요구율 (왼쪽)
            fig_gap.add_trace(go.Bar(
                name="🏢 기업 구인 요구율",
                y=skills_c, x=demand_c, orientation="h",
                marker=dict(color=bar_colors_d, line=dict(color="rgba(0,0,0,0)", width=0)),
                text=[f"<b>{v:.1f}%</b>" for v in demand_c],
                textposition="outside",
                textfont=dict(size=13, color="#ffd5d5"),
                cliponaxis=False,
            ))
            # 구직자 보유율 (오른쪽)
            fig_gap.add_trace(go.Bar(
                name="👤 구직자 보유율",
                y=skills_c, x=supply_c, orientation="h",
                marker=dict(color="#4a9eff", line=dict(color="rgba(0,0,0,0)", width=0)),
                text=[f"<b>{v:.1f}%</b>" if v > 0 else "<b>0%</b>" for v in supply_c],
                textposition="outside",
                textfont=dict(size=13, color="#b3d9ff"),
                cliponaxis=False,
            ))

            x_max = max(demand_c) * 1.45

            fig_gap.update_layout(
                barmode="group",
                height=max(480, len(skills_c) * 46),
                paper_bgcolor=DARK_BG,
                plot_bgcolor=DARK_PLOT,
                font=dict(color="#e2e8f0", size=13),
                margin=dict(l=10, r=100, t=16, b=50),
                xaxis=dict(
                    title=dict(text="전체 공고 대비 비율 (%)", font=dict(size=13, color="#a0aec0")),
                    range=[0, x_max],
                    gridcolor="rgba(255,255,255,0.08)",
                    ticksuffix="%",
                    tickfont=dict(size=12, color="#a0aec0"),
                    showline=True, linecolor="rgba(255,255,255,0.15)",
                    zeroline=False,
                ),
                yaxis=dict(
                    autorange="reversed",
                    tickfont=dict(size=13.5, color="#e2e8f0"),
                    gridcolor="rgba(255,255,255,0.06)",
                ),
                legend=dict(
                    orientation="h", y=-0.08, x=0,
                    font=dict(size=13, color="#e2e8f0"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                bargap=0.28,
                bargroupgap=0.06,
                hoverlabel=dict(bgcolor="#0d1117", font=dict(color="#fff", size=13)),
            )
            # Gap이 큰 항목에 annotation
            big_gap_items = sorted(gc_data, key=lambda x: -x["gap"])[:3]
            for g in big_gap_items:
                idx = skills_c.index(g["skill"])
                fig_gap.add_annotation(
                    x=g["demand_rate"],
                    y=idx,
                    text=f"  Gap +{g['gap']:.1f}%p",
                    xanchor="left", yanchor="middle",
                    font=dict(size=11, color="#fbbf24"),
                    showarrow=False,
                    xshift=80,
                )
            st.plotly_chart(fig_gap, use_container_width=True)

        # ── 자격증 역설 차트 ──────────────────────────────────
        st.markdown("""
        <div style="background:#1a1a2e;border-radius:12px;padding:16px 20px 6px;margin:12px 0 4px;">
          <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:4px;">
            🎓 자격증 역설 — 구직자 과잉 투자 vs 실제 기업 수요
          </div>
          <div style="font-size:0.85rem;color:#fbbf24;font-weight:600;">
            ⚠️ ADsP 취득자 30.2% ↔ 기업 우대 0.1% — 300배 과잉 공급
          </div>
        </div>
        """, unsafe_allow_html=True)

        cert_rows = [
            {"자격증": c,
             "구직자 보유율": lk_data["certs"].get(c, {}).get("rate", 0),
             "기업 우대율":   sa_data["certs"].get(c, {}).get("rate", 0)}
            for c in ["ADsP", "SQLD", "빅데이터분석기사", "ADP", "정보처리기사"]
        ]
        cdf = pd.DataFrame(cert_rows).sort_values("구직자 보유율", ascending=False)

        cl, cr = st.columns([2, 1])
        with cl:
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(
                name="👤 구직자 보유율",
                x=cdf["자격증"], y=cdf["구직자 보유율"],
                marker=dict(color="#4a9eff", line=dict(width=0)),
                text=cdf["구직자 보유율"].map(lambda v: f"<b>{v:.1f}%</b>"),
                textposition="outside",
                textfont=dict(size=14, color="#b3d9ff"),
            ))
            fig_c.add_trace(go.Bar(
                name="🏢 기업 우대율",
                x=cdf["자격증"], y=cdf["기업 우대율"],
                marker=dict(color="#ff6b6b", line=dict(width=0)),
                text=cdf["기업 우대율"].map(lambda v: f"<b>{v:.2f}%</b>"),
                textposition="outside",
                textfont=dict(size=14, color="#ffd5d5"),
            ))
            y_max = cdf["구직자 보유율"].max() * 1.35
            fig_c.update_layout(
                barmode="group", height=340,
                paper_bgcolor=DARK_BG, plot_bgcolor=DARK_PLOT,
                font=dict(color="#e2e8f0", size=13),
                yaxis=dict(
                    title=dict(text="비율 (%)", font=dict(size=13, color="#a0aec0")),
                    ticksuffix="%",
                    range=[0, y_max],
                    gridcolor="rgba(255,255,255,0.08)",
                    tickfont=dict(size=12, color="#a0aec0"),
                    zeroline=False,
                ),
                xaxis=dict(
                    tickfont=dict(size=14, color="#e2e8f0"),
                    linecolor="rgba(255,255,255,0.15)",
                ),
                margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(
                    orientation="h", y=1.1, x=0,
                    font=dict(size=13, color="#e2e8f0"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                bargap=0.25,
                hoverlabel=dict(bgcolor="#0d1117", font=dict(color="#fff", size=13)),
            )
            st.plotly_chart(fig_c, use_container_width=True)

        with cr:
            # 각 자격증 ROI 카드
            for _, row in cdf.iterrows():
                ratio = row["구직자 보유율"] / row["기업 우대율"] if row["기업 우대율"] > 0 else 999
                ratio_str = f"약 {ratio:.0f}배 과잉" if ratio < 999 else "기업 수요 거의 0"
                st.markdown(
                    f'<div style="background:#0d1117;border:1px solid rgba(255,107,107,0.4);'
                    f'border-radius:8px;padding:10px 12px;margin-bottom:8px;">'
                    f'<div style="font-size:0.92rem;font-weight:700;color:#e2e8f0;">{row["자격증"]}</div>'
                    f'<div style="font-size:0.82rem;color:#b3d9ff;">구직자 {row["구직자 보유율"]:.1f}%</div>'
                    f'<div style="font-size:0.82rem;color:#ffd5d5;">기업 {row["기업 우대율"]:.2f}%</div>'
                    f'<div style="font-size:0.78rem;color:#fbbf24;font-weight:600;">{ratio_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── 나의 스킬 진단 ────────────────────────────────────
        st.markdown('<div class="section-title">🔍 나의 스킬 진단 — 직접 선택하면 맞춤 전략 제공</div>',
                    unsafe_allow_html=True)

        my_skills = st.multiselect(
            "보유한 스킬을 모두 선택하세요 (자격증 포함)",
            options=sorted(SKILL_PATTERNS.keys()),
            default=[],
            placeholder="스킬을 선택하면 공고 커버리지·부족 스킬·맞춤 조언을 알려드립니다...",
            help="가능한 많이 선택할수록 더 정확한 조언을 드립니다.",
        )

        if not my_skills:
            st.markdown("""
            <div style="text-align:center;padding:32px;color:#999;font-size:0.95rem;
            background:#f9f9f9;border-radius:10px;margin-top:10px;">
            위에서 보유 스킬을 선택하면<br>
            <b>공고 커버리지 · 우선 학습 스킬 · 직무 적합도 · 맞춤 전략 조언</b>을 보여드립니다.
            </div>
            """, unsafe_allow_html=True)
        else:
            my_set   = set(my_skills)
            my_certs = [s for s in my_skills if s in CERT_SKILLS]
            my_real  = [s for s in my_skills if s not in CERT_SKILLS]
            cert_pct = round(len(my_certs) / len(my_skills) * 100) if my_skills else 0

            # 커버리지 계산
            covered    = sum(1 for r in filtered if set(r["skills_all"]) & my_set)
            coverage   = round(covered / ftotal * 100, 1) if ftotal else 0
            top10_list = df_all["스킬"].head(10).tolist()
            top10_have = [s for s in top10_list if s in my_set]

            # KPI 4개
            km1, km2, km3, km4 = st.columns(4)
            km1.metric("공고 커버리지",   f"{coverage}%",
                       help="내 스킬 1개 이상을 요구하는 공고 비율")
            km2.metric("TOP 10 스킬 보유", f"{len(top10_have)}/10",
                       help="전체 공고에서 가장 많이 요구하는 10개 스킬 중 보유 수")
            km3.metric("실무 스킬",        f"{len(my_real)}개",
                       help="자격증을 제외한 실제 기술 스킬 수")
            km4.metric("자격증 비중",      f"{cert_pct}%",
                       delta="과잉 투자 주의" if cert_pct > 50 else ("양호" if my_real else None),
                       delta_color="inverse" if cert_pct > 50 else "off")

            st.markdown("<br>", unsafe_allow_html=True)
            d_col, a_col = st.columns(2)

            # ── 우선 학습 스킬 ────────────────────────────────
            with d_col:
                st.markdown("**📋 추가해야 할 핵심 스킬 (수요 순위)**")
                missing = sorted(
                    [(g["skill"], g["demand_rate"], g["supply_rate"])
                     for g in gaps_list
                     if g["skill"] not in my_set
                     and g["skill"] not in CERT_SKILLS
                     and g["demand_rate"] > 2],
                    key=lambda x: -x[1],
                )[:6]

                for skill, demand, supply in missing:
                    lt  = LEARN_TIME.get(skill, "?")
                    tip = SKILL_TIPS.get(skill, "")
                    urg = "🚨" if demand > 15 else "🔶" if demand > 7 else "🔷"
                    with st.expander(f"{urg} **{skill}** — 수요 {demand:.1f}%  ·  예상 {lt}"):
                        if tip:
                            st.markdown(f"**학습 경로:** {tip}")
                        gap_val = demand - supply
                        st.progress(min(1.0, demand / 35))
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric("구인 수요", f"{demand:.1f}%")
                        mc2.metric("구직자 준비", f"{supply:.1f}%")
                        mc3.metric("Gap", f"+{gap_val:.1f}%p")
                        if supply < 1:
                            st.success("⭐ 준비하는 사람이 거의 없어 차별화 효과가 매우 큽니다!")

            # ── 맞춤 전략 조언 ────────────────────────────────
            with a_col:
                st.markdown("**💬 나에게 맞는 전략 조언**")

                has_py    = "Python" in my_set
                has_sql   = "SQL" in my_set
                has_gh    = "GitHub" in my_set or "포트폴리오" in my_set or "Kaggle" in my_set
                has_ml    = "머신러닝" in my_set or "딥러닝" in my_set
                has_llm   = "LLM" in my_set or "생성형AI" in my_set
                has_cloud = any(s in my_set for s in ["AWS", "GCP", "Azure"])

                if not has_py:
                    st.error("🚨 **Python 없음 — 최우선 과제**\n\n"
                             "데이터 직무 입문의 관문입니다. 다른 모든 것보다 Python 학습을 먼저 시작하세요.\n\n"
                             "수요 **31.0%** | 예상 기간 1~3개월")

                if has_py and not has_sql:
                    st.warning("🔶 **SQL 부재**\n\n"
                               "Python이 있어도 SQL 없이는 실제 데이터 분석 업무가 불완전합니다.\n\n"
                               "수요 **20.4%** — HackerRank SQL Kit부터 시작하세요.")

                if my_certs and not my_real:
                    st.error("⚠️ **자격증만 있고 실무 스킬 없음**\n\n"
                             f"보유 자격증: {', '.join(my_certs)}\n\n"
                             "기업 우대 비율은 0.1~0.2%에 불과합니다. "
                             "Python·SQL 학습과 GitHub 프로젝트 공개를 지금 당장 시작하세요.")

                if has_py and has_sql and not has_gh:
                    st.warning("🔶 **포트폴리오·GitHub 없음**\n\n"
                               "Python·SQL이 있어도 공개 프로젝트가 없으면 서류에서 불이익을 받습니다.\n\n"
                               "캐글 노트북이나 토이 프로젝트를 README와 함께 공개하세요.")

                if has_py and has_sql and has_gh and not has_ml:
                    st.info("🔷 **다음 단계: 머신러닝 추가**\n\n"
                            "기초 역량이 갖춰졌습니다. scikit-learn으로 ML 프로젝트를 추가하면 "
                            "데이터사이언티스트 지원이 가능합니다. (수요 14.1%)")

                if has_ml and not has_llm:
                    st.info("🔷 **LLM/생성AI로 차별화**\n\n"
                            "ML 보유자가 LLM을 추가하면 시장 희소성이 급격히 높아집니다.\n\n"
                            "구인 수요 **11.0%**, 구직자 준비 **0%** — 지금 가장 강력한 차별화 포인트입니다.")

                if has_ml and not has_cloud:
                    st.info("🔷 **클라우드 추가 권장**\n\n"
                            "ML 모델을 클라우드에 배포하는 능력은 MLOps 수요와 연결됩니다.\n\n"
                            "AWS(수요 7.7%)부터 시작해 S3·EC2·SageMaker 실습을 권장합니다.")

                if has_py and has_sql and has_gh and has_ml and has_llm:
                    st.success("✅ **탁월한 역량 조합!**\n\n"
                               "Python + SQL + 포트폴리오 + ML + LLM 조합은 "
                               "데이터사이언티스트 및 AI 엔지니어 직무 지원에 매우 유리합니다.")

                if not my_certs and has_py and has_sql:
                    st.success("👍 **자격증 없어도 괜찮습니다**\n\n"
                               "기업은 자격증보다 실무 스킬과 포트폴리오를 훨씬 중시합니다. "
                               "현재 방향이 올바릅니다.")

                # 직무 적합도 바 차트
                st.markdown("<br>**🎯 직무 적합도 분석**", unsafe_allow_html=True)
                fits = {
                    cat: round(len(my_set & skills) / len(skills) * 100)
                    for cat, skills in JOB_FIT_DEF.items()
                }
                for cat, pct in sorted(fits.items(), key=lambda x: -x[1]):
                    score = len(my_set & JOB_FIT_DEF[cat])
                    if score == 0:
                        continue
                    bar_color = "#4C78A8" if pct == max(fits.values()) else "#aaa"
                    st.markdown(
                        f'<div style="margin:6px 0;">'
                        f'<div style="display:flex;justify-content:space-between;'
                        f'font-size:0.88rem;margin-bottom:3px;">'
                        f'<b>{cat}</b>'
                        f'<span style="color:#666;font-size:0.8rem;">{score}개 매칭 ({pct}%)</span></div>'
                        f'<div style="background:#eee;border-radius:4px;height:9px;">'
                        f'<div style="background:{bar_color};width:{pct}%;height:9px;'
                        f'border-radius:4px;"></div></div></div>',
                        unsafe_allow_html=True,
                    )

# ─── 푸터 ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("📌 데이터 출처: 사람인 (www.saramin.co.kr) · 수집일: 2026-07-04 · 총 1,550건 분석")
