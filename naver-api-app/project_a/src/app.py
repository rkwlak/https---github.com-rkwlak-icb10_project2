import os
import streamlit as st
from dotenv import load_dotenv
from utils import split_keywords, enforce_limit, format_date, download_df_as_csv, SHOP_CATEGORY_MAP
from api import get_trend, get_shopping, get_blog, get_cafe, get_news, get_shopping_trend
import pandas as pd

# .env 파일 로드
load_dotenv()

st.set_page_config(page_title="Naver API Dashboard", layout="wide")

# ---- Sidebar ----
st.sidebar.title("🛠️ 설정")

# 환경 변수에서 직접 가져오기
client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

if client_id and client_secret:
    st.sidebar.success("🔑 Naver API 키가 로드되었습니다.")
else:
    st.sidebar.warning("⚠️ .env 파일에 API 키를 설정해주세요.")

keywords_raw = st.sidebar.text_area("검색어 (쉼표로 구분, 최대 500개)", "")
keywords = split_keywords(keywords_raw)
keywords = enforce_limit(keywords, max_count=500)

start_date = st.sidebar.date_input("시작 날짜", value=None)
end_date = st.sidebar.date_input("종료 날짜", value=None)

if start_date and end_date:
    start_str = format_date(start_date)
    end_str = format_date(end_date)
else:
    start_str = end_str = None

page = st.sidebar.selectbox("📊 페이지 선택", [
    "검색어 트렌드",
    "쇼핑",
    "블로그",
    "카페",
    "뉴스",
    "쇼핑 트렌드"
])

if page == "쇼핑":
    category_name = st.sidebar.selectbox(
        "쇼핑 카테고리 선택",
        list(SHOP_CATEGORY_MAP.keys()),
        index=0,
    )
    category_id = SHOP_CATEGORY_MAP.get(category_name)

st.title(f"{page} 분석 결과")

if not client_id or not client_secret:
    st.warning("⚠️ .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 올바르게 설정해주세요.")
    st.stop()

if not keywords:
    st.info("검색어를 입력하면 결과가 표시됩니다.")
    st.stop()

if not (start_str and end_str):
    st.info("날짜 범위를 설정해 주세요.")
    st.stop()

if st.button("🔍 데이터 가져오기"):
    with st.spinner("데이터를 가져오는 중…"):
        if page == "검색어 트렌드":
            df = get_trend(keywords, start_str, end_str, client_id, client_secret)
        elif page == "쇼핑":
            df = get_shopping(keywords, client_id, client_secret, category_id)
        elif page == "블로그":
            df = get_blog(keywords, client_id, client_secret)
        elif page == "카페":
            df = get_cafe(keywords, client_id, client_secret)
        elif page == "뉴스":
            df = get_news(keywords, client_id, client_secret)
        else:  # 쇼핑 트렌드
            df = get_shopping_trend(keywords, start_str, end_str, client_id, client_secret)

    if df is None or df.empty:
        st.error("데이터를 가져오지 못했습니다.")
    else:
        # 데이터 표 표시
        st.subheader("📋 데이터 목록")
        st.dataframe(df, use_container_width=True)
        
        # 페이지별 맞춤형 그래프 시각화 추가
        if page in ["검색어 트렌드", "쇼핑 트렌드"]:
            st.subheader("📈 검색량 추이 그래프")
            try:
                chart_df = df.set_index("날짜")
                st.line_chart(chart_df, use_container_width=True)
            except Exception as e:
                st.warning(f"그래프 표시 중 오류가 발생했습니다: {e}")
                
        elif page == "쇼핑":
            col1, col2 = st.columns(2)
            
            with col1:
                if "mallName" in df.columns:
                    st.subheader("🏬 주요 쇼핑몰별 상품 등록 분포")
                    try:
                        mall_counts = df["mallName"].value_counts().head(10)
                        st.bar_chart(mall_counts, use_container_width=True)
                    except Exception as e:
                        st.warning(f"쇼핑몰 분포 그래프 표시 중 오류: {e}")
            
            with col2:
                if "lprice" in df.columns:
                    st.subheader("💵 상품별 최저가 비교 (상위 10개)")
                    try:
                        price_df = df.copy()
                        price_df["price_num"] = pd.to_numeric(price_df["lprice"], errors='coerce').fillna(0)
                        price_df = price_df[price_df["price_num"] > 0].head(10)
                        if not price_df.empty:
                            price_df["clean_title"] = price_df["title"].str.replace(r'<[^>]*>', '', regex=True)
                            chart_data = price_df.set_index("clean_title")[["price_num"]]
                            st.bar_chart(chart_data, use_container_width=True)
                    except Exception as e:
                        st.warning(f"가격 비교 그래프 표시 중 오류: {e}")
                        
        elif page in ["블로그", "카페"]:
            if "postdate" in df.columns:
                st.subheader("📅 일자별 포스팅 등록 추이")
                try:
                    blog_df = df.copy()
                    blog_df["parsed_date"] = pd.to_datetime(blog_df["postdate"], format="%Y%m%d", errors='coerce')
                    blog_df = blog_df.dropna(subset=["parsed_date"])
                    if not blog_df.empty:
                        date_counts = blog_df["parsed_date"].dt.strftime("%Y-%m-%d").value_counts().sort_index()
                        st.line_chart(date_counts, use_container_width=True)
                except Exception as e:
                    st.warning(f"포스팅 추이 그래프 표시 중 오류: {e}")
                    
        elif page == "뉴스":
            if "pubDate" in df.columns:
                st.subheader("📰 일자별 뉴스 발행 추이")
                try:
                    news_df = df.copy()
                    news_df["parsed_date"] = pd.to_datetime(news_df["pubDate"], errors='coerce')
                    news_df = news_df.dropna(subset=["parsed_date"])
                    if not news_df.empty:
                        date_counts = news_df["parsed_date"].dt.strftime("%Y-%m-%d").value_counts().sort_index()
                        st.line_chart(date_counts, use_container_width=True)
                except Exception as e:
                    st.warning(f"뉴스 발행 추이 그래프 표시 중 오류: {e}")
        
        # CSV 다운로드
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 CSV 다운로드", data=csv, file_name=f"naver_{page}_data.csv", mime="text/csv")
