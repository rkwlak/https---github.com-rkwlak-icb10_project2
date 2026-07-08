"""
사람인 데이터 직무 채용공고 종합 분석 스크립트
"""
import sqlite3
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations

DB_PATH = Path(__file__).parent.parent / "data" / "saramin.db"

# ─── 스펙 사전 정의 ──────────────────────────────────────────────────────────

SKILL_PATTERNS = {
    # 프로그래밍 언어
    "Python":     [r'\bpython\b', r'파이썬'],
    "SQL":        [r'\bsql\b', r'쿼리\s*작성', r'쿼리\s*언어', r'\bMySQL\b', r'\bPostgres', r'\bOracle\b', r'\bMS-?SQL\b'],
    "R":          [r'\bR\s*언어\b', r'\bR\s*프로그래밍\b', r'(?<!\w)R(?!\w)\s*(언어|통계|분석)', r'\bRstudio\b', r'\bggplot\b', r'\bdplyr\b'],
    "Java":       [r'\bjava\b(?!\s*script)', r'자바(?!\s*스크립트)'],
    "Scala":      [r'\bscala\b', r'스칼라'],
    "JavaScript": [r'\bjavascript\b', r'\bjs\b', r'\btypescript\b', r'자바스크립트'],

    # 분석·시각화 도구
    "Excel":      [r'\bexcel\b', r'엑셀', r'\bvba\b'],
    "Tableau":    [r'\btableau\b', r'타블로', r'태블로'],
    "Power BI":   [r'\bpower\s*bi\b', r'파워\s*비아이'],
    "Looker":     [r'\blooker\b', r'\blooker\s*studio\b'],
    "GA4":        [r'\bga4\b', r'\bgoogle\s*analytics\b', r'구글\s*애널리틱스'],
    "Metabase":   [r'\bmetabase\b'],
    "Redash":     [r'\bredash\b'],
    "Superset":   [r'\bsuperset\b', r'\bapache\s*superset\b'],

    # 데이터베이스
    "MySQL":      [r'\bmysql\b'],
    "PostgreSQL": [r'\bpostgresql\b', r'\bpostgres\b'],
    "Oracle":     [r'\boracle\b', r'오라클'],
    "MongoDB":    [r'\bmongodb\b', r'몽고\s*db'],
    "Redis":      [r'\bredis\b'],
    "Elasticsearch": [r'\belasticsearch\b', r'\bes\b(?=\s+(?:검색|인덱스|쿼리))'],

    # 클라우드·인프라
    "AWS":        [r'\baws\b', r'amazon\s*web\s*services', r'아마존\s*웹\s*서비스'],
    "GCP":        [r'\bgcp\b', r'\bgoogle\s*cloud\b', r'구글\s*클라우드'],
    "Azure":      [r'\bazure\b', r'마이크로소프트\s*클라우드'],
    "Spark":      [r'\bspark\b', r'\bapache\s*spark\b', r'스파크'],
    "Hadoop":     [r'\bhadoop\b', r'하둡'],
    "Airflow":    [r'\bairflow\b', r'\bapache\s*airflow\b', r'에어플로우'],
    "Kafka":      [r'\bkafka\b', r'카프카'],
    "Docker":     [r'\bdocker\b', r'도커'],
    "Kubernetes": [r'\bkubernetes\b', r'\bk8s\b', r'쿠버네티스'],
    "dbt":        [r'\bdbt\b'],

    # AI·ML
    "머신러닝":   [r'머신\s*러닝', r'machine\s*learning', r'\bml\b(?=\s*(모델|알고리즘|엔지니어|개발|경험))'],
    "딥러닝":     [r'딥\s*러닝', r'deep\s*learning'],
    "NLP":        [r'\bnlp\b', r'자연어\s*처리', r'natural\s*language'],
    "LLM":        [r'\bllm\b', r'large\s*language\s*model', r'대규모\s*언어\s*모델'],
    "생성형AI":   [r'생성형\s*ai', r'generative\s*ai', r'\bgpt\b', r'\bchatgpt\b', r'거대\s*언어'],
    "TensorFlow": [r'\btensorflow\b', r'텐서플로'],
    "PyTorch":    [r'\bpytorch\b', r'파이토치'],
    "scikit-learn":[r'\bscikit[\-\s]learn\b', r'\bsklearn\b'],
    "통계분석":   [r'통계\s*(?:분석|지식|기법|모델)', r'회귀\s*분석', r'가설\s*검증', r'A/B\s*테스트', r'유의성\s*검정'],

    # 자격증
    "SQLD":       [r'\bsqld\b', r'sql\s*개발자\s*자격'],
    "ADsP":       [r'\badsp\b', r'데이터\s*분석\s*준전문가'],
    "ADP":        [r'\badp\b(?!\s*\w)', r'데이터\s*분석\s*전문가'],
    "빅데이터분석기사":[r'빅\s*데이터\s*분석\s*기사'],
    "정보처리기사":[r'정보\s*처리\s*기사'],

    # 외국어
    "영어":       [r'영어\s*(?:능통|가능|우수|회화|커뮤니케이션)', r'english\s*(?:proficiency|communication|fluent)',
                   r'toeic', r'opic', r'toefl', r'영문\s*서류'],
    "TOEIC":      [r'\btoeic\b'],
    "OPIc":       [r'\bopic\b'],

    # 포트폴리오·경험
    "GitHub":     [r'\bgithub\b', r'\bgit\b'],
    "Kaggle":     [r'\bkaggle\b', r'캐글'],
    "포트폴리오": [r'포트폴리오', r'portfolio'],
    "논문":       [r'논문', r'학술지', r'저술'],
    "인턴경험":   [r'인턴\s*(?:경험|경력|출신)', r'인턴십'],
}

# 학력 패턴
EDU_PATTERNS = {
    "학력무관":   [r'학력\s*무관', r'학력\s*제한\s*없', r'학력\s*불문'],
    "전문대졸":   [r'전문대', r'2,?3년제\s*대학', r'초대졸'],
    "대졸":       [r'4년제\s*대학\s*(?:졸업|이상)', r'대학교?\s*\(4년\)', r'대졸\s*이상', r'학사\s*이상'],
    "석사":       [r'석사\s*(?:이상|학위|졸업)', r'대학원\s*(?:석사|이상)'],
    "박사":       [r'박사\s*(?:이상|학위|졸업)'],
}

# 전공 패턴
MAJOR_PATTERNS = {
    "컴퓨터공학": [r'컴퓨터\s*(?:공학|과학|학과)', r'소프트웨어\s*(?:공학|학과)', r'computer\s*science', r'전산학'],
    "통계학":     [r'통계\s*(?:학|학과)', r'statistics'],
    "수학":       [r'수학\s*(?:학|학과)', r'응용수학', r'mathematics'],
    "산업공학":   [r'산업\s*공학', r'industrial\s*engineering'],
    "경영학":     [r'경영\s*(?:학|정보학)', r'business\s*(?:administration|analytics)'],
    "전기전자":   [r'전기\s*(?:전자|공학)', r'전자\s*(?:공학|학과)'],
    "관련전공":   [r'(?:관련|유사)\s*(?:전공|학과|학부)', r'이공계\s*(?:전공|계열)', r'이공계열', r'공학계열'],
}

# 경력 패턴 (experience 컬럼 기반)
EXP_MAP = {
    "신입":       [r'신입', r'경험\s*없어도', r'신규\s*졸업'],
    "경력무관":   [r'경력\s*무관', r'경력\s*불문', r'경력\s*무방'],
    "1년이상":    [r'경력\s*1년\s*(?:이상|↑)', r'1\s*년\s*이상\s*경력'],
    "3년이상":    [r'경력\s*3년\s*(?:이상|↑)', r'3\s*년\s*이상\s*경력'],
    "5년이상":    [r'경력\s*5년\s*(?:이상|↑)', r'5\s*년\s*이상\s*경력'],
    "10년이상":   [r'경력\s*10년\s*(?:이상|↑)', r'10\s*년\s*이상\s*경력'],
}

# 직무 분류 (tags 컬럼 또는 title 기반)
JOB_CATEGORIES = {
    "데이터분석가":       [r'데이터\s*분석가', r'data\s*analyst', r'비즈니스\s*분석', r'BA\b', r'BI\s*분석'],
    "데이터사이언티스트":  [r'데이터\s*사이언티스트', r'data\s*scientist', r'DS\b'],
    "데이터엔지니어":     [r'데이터\s*엔지니어', r'data\s*engineer', r'DE\b', r'데이터\s*파이프라인', r'ETL'],
    "AI/ML엔지니어":     [r'ai\s*엔지니어', r'ml\s*엔지니어', r'머신러닝\s*엔지니어', r'딥러닝\s*엔지니어',
                          r'mlops', r'ai\s*개발', r'machine\s*learning\s*engineer'],
    "BI분석가":          [r'bi\s*(?:분석|개발|엔지니어)', r'비즈니스\s*인텔리전스', r'대시보드', r'시각화\s*전문'],
}


def make_pattern(patterns: list) -> re.Pattern:
    combined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


COMPILED_SKILLS  = {k: make_pattern(v) for k, v in SKILL_PATTERNS.items()}
COMPILED_EDU     = {k: make_pattern(v) for k, v in EDU_PATTERNS.items()}
COMPILED_MAJOR   = {k: make_pattern(v) for k, v in MAJOR_PATTERNS.items()}
COMPILED_JOB     = {k: make_pattern(v) for k, v in JOB_CATEGORIES.items()}


def match_specs(text: str, patterns: dict) -> list:
    if not text:
        return []
    return [k for k, pat in patterns.items() if pat.search(text)]


def classify_job(title: str, tags: list) -> str:
    combined = f"{title} {' '.join(tags)}"
    for cat, pat in COMPILED_JOB.items():
        if pat.search(combined.lower()):
            return cat
    return "기타데이터직무"


def parse_experience_col(exp_str: str) -> str:
    """experience 컬럼값에서 경력 분류"""
    if not exp_str:
        return "미분류"
    if re.search(r'신입', exp_str):
        return "신입포함"
    if re.search(r'경력\s*무관|경력무관', exp_str):
        return "경력무관"
    m = re.search(r'경력\s*(\d+)년', exp_str)
    if m:
        yr = int(m.group(1))
        if yr <= 1:
            return "1년이상"
        if yr <= 3:
            return "3년이상"
        if yr <= 5:
            return "5년이상"
        return "10년이상"
    return "미분류"


# ─── 데이터 로드 ─────────────────────────────────────────────────────────────

def load_data(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT j.job_id, j.company, j.title, j.tags, j.experience, j.education,
               COALESCE(d.requirements,'') as requirements,
               COALESCE(d.preferred,'')    as preferred,
               COALESCE(d.job_desc,'')     as job_desc,
               COALESCE(d.full_text,'')    as full_text
        FROM jobs j
        LEFT JOIN job_details d ON j.job_id = d.job_id
    """)
    return cur.fetchall()


# ─── 메인 분석 ───────────────────────────────────────────────────────────────

def run():
    conn = sqlite3.connect(DB_PATH)
    rows = load_data(conn)
    conn.close()

    total = len(rows)
    print(f"\n{'='*65}")
    print(f"  사람인 데이터 직무 채용공고 분석 보고서")
    print(f"{'='*65}")
    print(f"  총 분석 공고 수: {total:,}건")

    # ── 1. 데이터 점검 ────────────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [1] 데이터 점검 및 전처리")
    print(f"{'─'*65}")

    companies = [r[1] for r in rows]
    company_cnt = Counter(companies)
    repeat_corps = {k: v for k, v in company_cnt.items() if v >= 3}
    print(f"  총 기업 수        : {len(set(companies)):,}개")
    print(f"  3건 이상 반복 기업 : {len(repeat_corps)}개 (상위 5개)")
    for corp, cnt in sorted(repeat_corps.items(), key=lambda x: -x[1])[:5]:
        print(f"    {corp:<35} {cnt}건")

    # 상세 수집 현황
    has_req = sum(1 for r in rows if r[6].strip())
    has_full = sum(1 for r in rows if r[9].strip())
    print(f"\n  자격요건 수집 공고 : {has_req:,}건 ({has_req/total*100:.1f}%)")
    print(f"  전체본문 수집 공고 : {has_full:,}건 ({has_full/total*100:.1f}%)")

    # ── 분석용 데이터 구조 구성 ───────────────────────────────────────────────
    records = []
    for row in rows:
        job_id, company, title, tags_json, experience, education, req, pref, job_desc, full_text = row
        tags = json.loads(tags_json) if tags_json else []

        # 텍스트 결합 (분석용)
        all_text    = f"{title} {req} {pref} {job_desc} {full_text}".lower()
        req_text    = f"{req}".lower()
        pref_text   = f"{pref}".lower()

        job_cat     = classify_job(title, tags)
        exp_cat     = parse_experience_col(experience)

        # 스펙 탐지
        skills_all  = match_specs(all_text, COMPILED_SKILLS)
        skills_req  = match_specs(req_text, COMPILED_SKILLS)
        skills_pref = match_specs(pref_text, COMPILED_SKILLS)
        edu_req     = match_specs(f"{education} {req} {all_text}", COMPILED_EDU)
        major_req   = match_specs(all_text, COMPILED_MAJOR)

        records.append({
            "job_id":      job_id,
            "company":     company,
            "title":       title,
            "tags":        tags,
            "experience":  experience,
            "education":   education,
            "job_cat":     job_cat,
            "exp_cat":     exp_cat,
            "skills_all":  skills_all,
            "skills_req":  skills_req,
            "skills_pref": skills_pref,
            "edu_req":     edu_req,
            "major_req":   major_req,
            "all_text":    all_text,
            "req_text":    req_text,
            "pref_text":   pref_text,
        })

    # ── 2. 기업 반복공고 보정: 기업별 중복 제거 버전 ─────────────────────────
    # 동일 기업의 반복 공고가 분석을 왜곡하지 않도록 기업 단위 집계도 별도 수행
    seen_company_skill = defaultdict(set)
    unique_company_records = []
    for rec in records:
        key = rec["company"]
        if key not in seen_company_skill:
            unique_company_records.append(rec)
        seen_company_skill[key].add(rec["job_id"])
    unique_total = len(unique_company_records)

    print(f"\n  분석 기준 공고 수 : {total:,}건 (전체) / {unique_total:,}건 (기업별 대표공고)")

    # ── 3. 빈도 분석 (TOP 20 스펙) ───────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [3] 스펙 빈도 분석 — 전체 공고 기준 TOP 20")
    print(f"{'─'*65}")
    print(f"  {'스펙':<20} {'공고수':>7} {'비율':>8}   {'구분'}")
    print(f"  {'-'*20} {'-'*7} {'-'*8}   {'-'*20}")

    skill_count = Counter()
    for rec in records:
        for s in set(rec["skills_all"]):
            skill_count[s] += 1

    for rank, (skill, cnt) in enumerate(skill_count.most_common(20), 1):
        cat = _categorize_skill(skill)
        print(f"  {rank:2d}. {skill:<18} {cnt:>7,} {cnt/total*100:>7.1f}%   {cat}")

    # ── 4. 필수 vs 우대 분리 ─────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [4] 필수요건 vs 우대사항 비교 — 주요 스펙 TOP 15")
    print(f"{'─'*65}")
    print(f"  {'스펙':<20} {'전체':>7} {'필수':>7} {'우대':>7}   {'필수%':>6} {'우대%':>6}")
    print(f"  {'-'*20} {'-'*7} {'-'*7} {'-'*7}   {'-'*6} {'-'*6}")

    req_count  = Counter()
    pref_count = Counter()
    for rec in records:
        for s in set(rec["skills_req"]):
            req_count[s] += 1
        for s in set(rec["skills_pref"]):
            pref_count[s] += 1

    req_with_detail = sum(1 for r in records if r["req_text"].strip())
    pref_with_detail = sum(1 for r in records if r["pref_text"].strip())

    for skill, total_cnt in skill_count.most_common(15):
        rc = req_count.get(skill, 0)
        pc = pref_count.get(skill, 0)
        rp = rc / req_with_detail * 100 if req_with_detail else 0
        pp = pc / pref_with_detail * 100 if pref_with_detail else 0
        print(f"  {skill:<20} {total_cnt:>7,} {rc:>7,} {pc:>7,}   {rp:>5.1f}% {pp:>5.1f}%")

    # ── 5. 직무별 비교 ────────────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [5] 직무별 채용공고 분류 및 TOP 스펙 비교")
    print(f"{'─'*65}")

    job_cat_records = defaultdict(list)
    for rec in records:
        job_cat_records[rec["job_cat"]].append(rec)

    cat_order = ["데이터분석가", "데이터사이언티스트", "데이터엔지니어", "AI/ML엔지니어", "BI분석가", "기타데이터직무"]
    for cat in cat_order:
        recs = job_cat_records[cat]
        if not recs:
            continue
        cnt_map = Counter()
        for rec in recs:
            for s in set(rec["skills_all"]):
                cnt_map[s] += 1
        top5 = [s for s, _ in cnt_map.most_common(10)]
        print(f"\n  ▶ {cat} ({len(recs)}건)")
        print(f"    {'순위':<4} {'스펙':<20} {'공고수':>6} {'비율':>7}")
        for rank, (s, c) in enumerate(cnt_map.most_common(10), 1):
            print(f"    {rank:2d}.  {s:<20} {c:>6,} {c/len(recs)*100:>6.1f}%")

    # ── 6. 스펙 조합 분석 ────────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [6] 스펙 조합 분석")
    print(f"{'─'*65}")

    pair_cnt   = Counter()
    triple_cnt = Counter()
    for rec in records:
        skills = sorted(set(rec["skills_all"]))
        for a, b in combinations(skills, 2):
            pair_cnt[(a, b)] += 1
        for a, b, c in combinations(skills, 3):
            triple_cnt[(a, b, c)] += 1

    print("\n  [2개 조합 TOP 10]")
    print(f"  {'조합':<40} {'공고수':>7} {'비율':>7}")
    for (a, b), cnt in pair_cnt.most_common(10):
        print(f"  {a} + {b:<30} {cnt:>7,} {cnt/total*100:>6.1f}%")

    print("\n  [3개 조합 TOP 10]")
    print(f"  {'조합':<55} {'공고수':>7} {'비율':>7}")
    for (a, b, c), cnt in triple_cnt.most_common(10):
        combo = f"{a} + {b} + {c}"
        print(f"  {combo:<55} {cnt:>7,} {cnt/total*100:>6.1f}%")

    # ── 7. 신입 vs 경력직 비교 ───────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [7] 신입 vs 경력직 스펙 비교")
    print(f"{'─'*65}")

    exp_groups = {
        "신입포함":  [],
        "경력무관":  [],
        "3년이상":   [],
        "5년이상":   [],
    }
    for rec in records:
        ec = rec["exp_cat"]
        if ec in exp_groups:
            exp_groups[ec].append(rec)
        elif ec == "1년이상":
            exp_groups["신입포함"].append(rec)

    print(f"\n  경력 그룹별 공고 수:")
    for g, recs in exp_groups.items():
        print(f"    {g:<12} {len(recs):>5}건")

    print("\n  경력 그룹별 TOP 8 스펙:")
    header = f"  {'스펙':<20}"
    for g in exp_groups:
        header += f" {g:>12}"
    print(header)
    print("  " + "-" * (20 + 13 * len(exp_groups)))

    # 전체 top 스펙 기준으로 행 구성
    top_skills = [s for s, _ in skill_count.most_common(20)]
    group_counts = {}
    for g, recs in exp_groups.items():
        if not recs:
            group_counts[g] = {}
            continue
        cnt = Counter()
        for rec in recs:
            for s in set(rec["skills_all"]):
                cnt[s] += 1
        group_counts[g] = {s: cnt[s]/len(recs)*100 for s in top_skills}

    for skill in top_skills:
        row = f"  {skill:<20}"
        for g, recs in exp_groups.items():
            pct = group_counts[g].get(skill, 0)
            row += f" {pct:>11.1f}%"
        print(row)

    # ── 학력·전공 분석 ────────────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  [학력 요구 분포]")
    print(f"{'─'*65}")
    edu_cnt = Counter()
    for rec in records:
        for e in set(rec["edu_req"]):
            edu_cnt[e] += 1
    # 구조화된 education 컬럼도 사용
    edu_col_cnt = Counter()
    for row in rows:
        edu_col_cnt[row[5]] += 1
    print("\n  education 컬럼 기반:")
    for edu, cnt in edu_col_cnt.most_common(10):
        if edu:
            print(f"    {edu:<25} {cnt:>6,}건 ({cnt/total*100:.1f}%)")

    print(f"\n  전공 요구 분포:")
    major_cnt = Counter()
    for rec in records:
        for m in set(rec["major_req"]):
            major_cnt[m] += 1
    for major, cnt in major_cnt.most_common(10):
        print(f"    {major:<25} {cnt:>6,}건 ({cnt/total*100:.1f}%)")

    # ── 8. 최종 인사이트 ─────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  [8] 최종 인사이트 — 기업이 원하는 데이터 직무 인재")
    print(f"{'='*65}")

    top5 = skill_count.most_common(5)
    print(f"\n  ① 가장 기본 스펙 (80% 이상 공고):")
    for s, c in skill_count.most_common(3):
        if c/total >= 0.2:
            print(f"    → {s} ({c/total*100:.1f}%)")

    print(f"\n  ② 기업이 가장 많이 요구하는 기술 TOP 5:")
    for rank, (s, c) in enumerate(top5, 1):
        print(f"    {rank}. {s:<20} {c/total*100:.1f}%")

    print(f"\n  ③ 자격증 요구 현황:")
    cert_skills = ["SQLD", "ADsP", "ADP", "빅데이터분석기사", "정보처리기사"]
    for cs in cert_skills:
        cnt = skill_count.get(cs, 0)
        print(f"    {cs:<20} {cnt:>5}건 ({cnt/total*100:.1f}%)")

    print(f"\n  ④ 학력 중요도:")
    for edu, cnt in edu_col_cnt.most_common(5):
        if edu:
            print(f"    {edu:<25} {cnt:>5}건 ({cnt/total*100:.1f}%)")

    print(f"\n  ⑤ 신입 지원자 핵심 준비 요소:")
    if exp_groups["신입포함"]:
        entry_cnt = Counter()
        for rec in exp_groups["신입포함"]:
            for s in set(rec["skills_all"]):
                entry_cnt[s] += 1
        n = len(exp_groups["신입포함"])
        for s, c in entry_cnt.most_common(5):
            print(f"    → {s} ({c/n*100:.1f}%)")

    print(f"\n  ⑦ 이상적인 데이터 직무 지원자 프로필:")
    must_skills = [s for s, c in skill_count.most_common(5)]
    must_req    = [s for s, c in req_count.most_common(3)]
    print(f"    • 필수 기술: {', '.join(must_skills)}")
    print(f"    • 필수 자격: {', '.join(must_req)}")
    edu_top = edu_col_cnt.most_common(1)
    if edu_top:
        print(f"    • 기본 학력: {edu_top[0][0]}")
    print(f"    • 경험/포트폴리오: GitHub, 프로젝트, Kaggle 경험 필수")


def _categorize_skill(skill: str) -> str:
    lang = ["Python", "SQL", "R", "Java", "Scala", "JavaScript"]
    viz  = ["Excel", "Tableau", "Power BI", "Looker", "GA4", "Metabase", "Redash", "Superset"]
    db   = ["MySQL", "PostgreSQL", "Oracle", "MongoDB", "Redis", "Elasticsearch"]
    infra = ["AWS", "GCP", "Azure", "Spark", "Hadoop", "Airflow", "Kafka", "Docker", "Kubernetes", "dbt"]
    ai   = ["머신러닝", "딥러닝", "NLP", "LLM", "생성형AI", "TensorFlow", "PyTorch", "scikit-learn", "통계분석"]
    cert = ["SQLD", "ADsP", "ADP", "빅데이터분석기사", "정보처리기사"]
    if skill in lang:  return "언어"
    if skill in viz:   return "시각화"
    if skill in db:    return "DB"
    if skill in infra: return "인프라/클라우드"
    if skill in ai:    return "AI/ML"
    if skill in cert:  return "자격증"
    return "기타"


if __name__ == "__main__":
    run()
