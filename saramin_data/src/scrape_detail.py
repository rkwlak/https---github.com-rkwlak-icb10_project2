"""
사람인 개별 채용공고 상세 페이지 수집 스크립트
/view-detail iframe 엔드포인트에서 자격요건, 우대사항, 직무내용 수집
"""
import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import time
import random
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "saramin.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "iframe",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

# 섹션 헤딩 키워드 → 카테고리 매핑
SECTION_MAP = {
    "requirements":  ["자격요건", "필요역량", "자격사항", "지원자격", "필수요건", "필수조건", "지원 자격"],
    "preferred":     ["우대사항", "우대조건", "우대 사항", "우대요건", "우대"],
    "job_desc":      ["담당업무", "주요업무", "직무내용", "업무내용", "담당 업무", "주요 업무", "수행업무"],
    "welfare":       ["복리후생", "복지", "혜택", "근무환경"],
}


def init_detail_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_details (
            job_id       TEXT PRIMARY KEY,
            job_desc     TEXT,
            requirements TEXT,
            preferred    TEXT,
            welfare      TEXT,
            full_text    TEXT,
            fetched_at   TEXT
        )
    """)
    conn.commit()


def get_pending_jobs(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT j.job_id
        FROM jobs j
        LEFT JOIN job_details d ON j.job_id = d.job_id
        WHERE d.job_id IS NULL
        ORDER BY j.page, j.job_id
    """)
    return [r[0] for r in cur.fetchall()]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def classify_heading(text: str) -> str:
    for cat, keywords in SECTION_MAP.items():
        if any(k in text for k in keywords):
            return cat
    return ""


def fetch_detail(session: requests.Session, job_id: str) -> dict:
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail"
    params = {"rec_idx": job_id, "rec_seq": "0"}
    empty = {"job_desc": "", "requirements": "", "preferred": "", "welfare": "", "full_text": ""}

    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return empty

        soup = BeautifulSoup(resp.text, "lxml")
        full_text = clean_text(soup.get_text(separator=" "))[:10000]

        sections = {"job_desc": [], "requirements": [], "preferred": [], "welfare": []}
        current = "job_desc"

        # 테이블 구조 파싱 (th/td 쌍)
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                heading = th.get_text(strip=True)
                content = clean_text(td.get_text(separator=" "))
                cat = classify_heading(heading)
                if cat:
                    sections[cat].append(content)

        # 리스트/단락 구조 파싱
        for el in soup.find_all(["h2", "h3", "h4", "dt", "strong", "b"]):
            heading = el.get_text(strip=True)
            cat = classify_heading(heading)
            if cat:
                current = cat
                # 다음 형제 요소 텍스트 수집
                sibling = el.find_next_sibling()
                while sibling and sibling.name not in ("h2", "h3", "h4", "dt"):
                    txt = clean_text(sibling.get_text(separator=" "))
                    if txt:
                        sections[current].append(txt)
                    sibling = sibling.find_next_sibling()

        # p, li 태그 수집 (섹션이 채워지지 않은 경우 full_text regex fallback)
        if not any(sections.values()):
            req_m = re.search(
                r'(?:자격요건|필요역량|필수조건|지원자격)(.*?)(?:우대|복리|담당|주요|근무|$)',
                full_text, re.DOTALL
            )
            if req_m:
                sections["requirements"].append(req_m.group(1)[:3000])

            pref_m = re.search(
                r'우대\s*(?:사항|조건)?(.*?)(?:복리|담당|주요|혜택|근무|$)',
                full_text, re.DOTALL
            )
            if pref_m:
                sections["preferred"].append(pref_m.group(1)[:3000])

            job_m = re.search(
                r'(?:담당업무|주요업무|직무내용)(.*?)(?:자격|우대|복리|근무|$)',
                full_text, re.DOTALL
            )
            if job_m:
                sections["job_desc"].append(job_m.group(1)[:3000])

        return {
            "job_desc":     clean_text(" ".join(sections["job_desc"]))[:5000],
            "requirements": clean_text(" ".join(sections["requirements"]))[:5000],
            "preferred":    clean_text(" ".join(sections["preferred"]))[:5000],
            "welfare":      clean_text(" ".join(sections["welfare"]))[:3000],
            "full_text":    full_text,
        }

    except Exception:
        return empty


def save_detail(conn, job_id: str, detail: dict, fetched_at: str):
    conn.execute("""
        INSERT INTO job_details (job_id, job_desc, requirements, preferred, welfare, full_text, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            job_desc     = excluded.job_desc,
            requirements = excluded.requirements,
            preferred    = excluded.preferred,
            welfare      = excluded.welfare,
            full_text    = excluded.full_text,
            fetched_at   = excluded.fetched_at
    """, (
        job_id,
        detail["job_desc"], detail["requirements"],
        detail["preferred"], detail["welfare"],
        detail["full_text"], fetched_at,
    ))
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    init_detail_table(conn)

    pending = get_pending_jobs(conn)
    total = len(pending)
    print(f"상세 수집 대상: {total}건")
    if total == 0:
        print("모두 수집 완료.")
        conn.close()
        return

    session = requests.Session()
    success = 0
    fail = 0

    for i, job_id in enumerate(pending, 1):
        now = datetime.now().isoformat(timespec="seconds")
        detail = fetch_detail(session, job_id)

        has_content = bool(detail["requirements"] or detail["job_desc"] or detail["full_text"])
        save_detail(conn, job_id, detail, now)

        if has_content:
            success += 1
        else:
            fail += 1

        if i % 100 == 0 or i == total:
            print(f"  [{i:4d}/{total}] 내용있음 {success}건 / 빈응답 {fail}건")

        time.sleep(random.uniform(0.3, 0.8))

    print(f"\n완료: 내용있음 {success}건 / 빈응답 {fail}건")
    conn.close()


if __name__ == "__main__":
    main()
