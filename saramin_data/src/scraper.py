import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import time
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "saramin.db"

BASE_URL = "https://www.saramin.co.kr/zf_user/jobs/list/job-category"
PARAMS = {
    "cat_kewd": "2248,82,83,106,107,108,105",
    "search_optional_item": "n",
    "search_done": "y",
    "panel_count": "y",
    "preview": "y",
    "isAjaxRequest": "0",
    "page_count": "50",
    "sort": "RL",
    "type": "job-category",
    "is_param": "1",
    "isSearchResultEmpty": "1",
    "isSectionHome": "0",
    "searchParamCount": "1",
}

HEADERS = {
    "Host": "www.saramin.co.kr",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Referer": "https://www.saramin.co.kr/zf_user/jobs/list/job-category?cat_kewd=2248%2C82%2C83%2C106%2C107%2C108%2C105&panel_type=&search_optional_item=n&search_done=y&panel_count=y&preview=y",
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id          TEXT PRIMARY KEY,
            company         TEXT,
            company_type    TEXT,
            company_url     TEXT,
            title           TEXT,
            url             TEXT,
            deadline        TEXT,
            posted_relative TEXT,
            location        TEXT,
            experience      TEXT,
            education       TEXT,
            employment      TEXT,
            salary          TEXT,
            tags            TEXT,
            badges          TEXT,
            apply_type      TEXT,
            page            INTEGER,
            collected_at    TEXT,
            raw_json        TEXT
        )
    """)
    conn.commit()
    return conn


def upsert_job(conn, job: dict):
    conn.execute("""
        INSERT INTO jobs (
            job_id, company, company_type, company_url, title, url,
            deadline, posted_relative, location, experience, education,
            employment, salary, tags, badges, apply_type,
            page, collected_at, raw_json
        ) VALUES (
            :job_id, :company, :company_type, :company_url, :title, :url,
            :deadline, :posted_relative, :location, :experience, :education,
            :employment, :salary, :tags, :badges, :apply_type,
            :page, :collected_at, :raw_json
        )
        ON CONFLICT(job_id) DO UPDATE SET
            company         = excluded.company,
            company_type    = excluded.company_type,
            company_url     = excluded.company_url,
            title           = excluded.title,
            url             = excluded.url,
            deadline        = excluded.deadline,
            posted_relative = excluded.posted_relative,
            location        = excluded.location,
            experience      = excluded.experience,
            education       = excluded.education,
            employment      = excluded.employment,
            salary          = excluded.salary,
            tags            = excluded.tags,
            badges          = excluded.badges,
            apply_type      = excluded.apply_type,
            page            = excluded.page,
            collected_at    = excluded.collected_at,
            raw_json        = excluded.raw_json
    """, job)
    conn.commit()


def fetch_page(session: requests.Session, page: int) -> Optional[BeautifulSoup]:
    params = {**PARAMS, "page": str(page)}
    try:
        resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [ERROR] 페이지 {page} 요청 실패: {e}")
        return None


def get_total_pages(soup: BeautifulSoup) -> int:
    # 전체 건수에서 역산: span.total_count > em
    total_el = soup.select_one("span.total_count em")
    if total_el:
        text = re.sub(r"[^\d]", "", total_el.get_text())
        if text:
            total = int(text)
            per_page = int(PARAMS["page_count"])
            pages = (total + per_page - 1) // per_page
            print(f"  전체 공고: {total}건 → {pages}페이지")
            return pages
    return 1


def parse_jobs(soup: BeautifulSoup, page: int) -> list:
    items = soup.select("div.list_item[id^='rec-']")
    jobs = []
    now = datetime.now().isoformat(timespec="seconds")

    for item in items:
        # job_id from element id attr (rec-12345678)
        raw_id = item.get("id", "")
        job_id = raw_id.replace("rec-", "") if raw_id.startswith("rec-") else raw_id

        # company
        company_el = item.select_one("div.col.company_nm a.str_tit")
        company = company_el.get_text(strip=True) if company_el else ""
        company_url = ""
        if company_el:
            href = company_el.get("href", "")
            company_url = "https://www.saramin.co.kr" + href if href.startswith("/") else href

        company_type_el = item.select_one("div.col.company_nm span.info_stock")
        company_type = company_type_el.get("title", company_type_el.get_text(strip=True)) if company_type_el else ""

        # title & url
        title_el = item.select_one("div.col.notification_info div.job_tit a.str_tit")
        title = title_el.get("title", title_el.get_text(strip=True)) if title_el else ""
        job_href = title_el.get("href", "") if title_el else ""
        url = "https://www.saramin.co.kr" + job_href if job_href.startswith("/") else job_href

        # tags / 직종
        tags = [span.get_text(strip=True) for span in item.select("div.job_meta span.job_sector span")]

        # badges (교육지원 TOP100 등)
        badges = [b.get_text(strip=True) for b in item.select("div.job_badge span")]

        # recruit_info: location / career / education
        location = ""
        experience = ""
        education = ""
        employment = ""
        salary = ""

        loc_el = item.select_one("div.col.recruit_info p.work_place")
        location = loc_el.get_text(strip=True) if loc_el else ""

        career_el = item.select_one("div.col.recruit_info p.career")
        experience = career_el.get_text(strip=True) if career_el else ""

        edu_el = item.select_one("div.col.recruit_info p.education")
        education = edu_el.get_text(strip=True) if edu_el else ""

        # employment type and salary may appear in additional li elements
        extra_lis = item.select("div.col.recruit_info ul li")[3:]
        if extra_lis:
            employment = extra_lis[0].get_text(strip=True)
        if len(extra_lis) > 1:
            salary = extra_lis[1].get_text(strip=True)

        # support_info: deadline / posted_relative / apply_type
        deadline_el = item.select_one("div.col.support_info span.date")
        deadline = deadline_el.get_text(strip=True) if deadline_el else ""

        posted_el = item.select_one("div.col.support_info span.deadlines")
        posted_relative = posted_el.get_text(strip=True) if posted_el else ""

        apply_btn = item.select_one("div.col.support_info a.sri_btn_md span")
        apply_type = apply_btn.get_text(strip=True) if apply_btn else ""

        raw = {
            "job_id": job_id,
            "company": company,
            "company_type": company_type,
            "company_url": company_url,
            "title": title,
            "url": url,
            "deadline": deadline,
            "posted_relative": posted_relative,
            "location": location,
            "experience": experience,
            "education": education,
            "employment": employment,
            "salary": salary,
            "tags": tags,
            "badges": badges,
            "apply_type": apply_type,
        }

        jobs.append({
            **raw,
            "tags": json.dumps(tags, ensure_ascii=False),
            "badges": json.dumps(badges, ensure_ascii=False),
            "page": page,
            "collected_at": now,
            "raw_json": json.dumps(raw, ensure_ascii=False),
        })

    return jobs


def scrape():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = init_db()
    session = requests.Session()

    print("=" * 60)
    print("사람인 채용정보 수집 시작")
    print(f"저장 경로: {DB_PATH}")
    print("=" * 60)

    # 1페이지 먼저 수집 및 검증
    print("\n[1단계] 1페이지 테스트 수집 중...")
    soup = fetch_page(session, 1)
    if soup is None:
        print("  1페이지 수집 실패. 종료합니다.")
        conn.close()
        return

    total_pages = get_total_pages(soup)
    jobs = parse_jobs(soup, 1)

    if not jobs:
        print("  1페이지에서 채용 공고를 찾지 못했습니다.")
        debug_path = DB_PATH.parent / "page1_debug.html"
        debug_path.write_text(soup.prettify(), encoding="utf-8")
        print(f"  HTML 저장: {debug_path}")
        conn.close()
        return

    for job in jobs:
        upsert_job(conn, job)

    print(f"  1페이지 수집 성공: {len(jobs)}건")
    print(f"  총 페이지 수: {total_pages}")

    # 나머지 페이지 전체 수집
    if total_pages > 1:
        print(f"\n[2단계] 2 ~ {total_pages}페이지 수집 중...")
        total_collected = len(jobs)
        for page in range(2, total_pages + 1):
            time.sleep(random.uniform(0.3, 1.0))

            page_soup = fetch_page(session, page)
            if page_soup is None:
                print(f"  페이지 {page} 건너뜀")
                continue

            page_jobs = parse_jobs(page_soup, page)
            for job in page_jobs:
                upsert_job(conn, job)

            total_collected += len(page_jobs)
            print(f"  페이지 {page:3d}/{total_pages} 완료 — {len(page_jobs)}건 (누적: {total_collected}건)")

    # 결과 리포트
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_db = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT company) FROM jobs WHERE company != ''")
    company_count = cur.fetchone()[0]

    cur.execute("SELECT MIN(collected_at), MAX(collected_at) FROM jobs")
    time_range = cur.fetchone()

    cur.execute("""
        SELECT company, COUNT(*) cnt FROM jobs
        WHERE company != ''
        GROUP BY company ORDER BY cnt DESC LIMIT 10
    """)
    top_companies = cur.fetchall()

    cur.execute("""
        SELECT location, COUNT(*) cnt FROM jobs
        WHERE location != ''
        GROUP BY location ORDER BY cnt DESC LIMIT 5
    """)
    top_locations = cur.fetchall()

    cur.execute("""
        SELECT experience, COUNT(*) cnt FROM jobs
        WHERE experience != ''
        GROUP BY experience ORDER BY cnt DESC LIMIT 5
    """)
    top_experience = cur.fetchall()

    cur.execute("""
        SELECT education, COUNT(*) cnt FROM jobs
        WHERE education != ''
        GROUP BY education ORDER BY cnt DESC LIMIT 5
    """)
    top_education = cur.fetchall()

    print("\n" + "=" * 60)
    print("수집 완료 리포트")
    print("=" * 60)
    print(f"  DB 총 레코드 수 : {total_db}건")
    print(f"  수집 기업 수    : {company_count}개")
    print(f"  수집 시간 범위  : {time_range[0]} ~ {time_range[1]}")
    print(f"  DB 파일 경로    : {DB_PATH}")

    print("\n  [채용공고 많은 기업 Top 10]")
    for comp, cnt in top_companies:
        print(f"    {comp:<35} {cnt}건")

    print("\n  [근무지역 분포 Top 5]")
    for loc, cnt in top_locations:
        print(f"    {loc:<35} {cnt}건")

    print("\n  [경력 조건 분포 Top 5]")
    for exp, cnt in top_experience:
        print(f"    {exp:<35} {cnt}건")

    print("\n  [학력 조건 분포 Top 5]")
    for edu, cnt in top_education:
        print(f"    {edu:<35} {cnt}건")

    conn.close()
    print("\n수집 완료.")


if __name__ == "__main__":
    scrape()
