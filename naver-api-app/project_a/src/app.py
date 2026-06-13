import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# utils에서 필요한 함수 임포트
from utils import (
    split_keywords, 
    enforce_limit, 
    format_date, 
    download_df_as_csv, 
    download_df_as_excel, 
    get_word_frequencies, 
    SHOP_CATEGORY_MAP
)
from api import (
    get_trend, 
    get_shopping, 
    get_blog, 
    get_cafe, 
    get_news, 
    get_shopping_trend
)

# .env 파일 로드
load_dotenv()

# matplotlib 한글 폰트 설정
try:
    system_os = platform.system()
    if system_os == "Darwin":
        plt.rcParams['font.family'] = 'AppleGothic'
    elif system_os == "Windows":
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else:
        # Streamlit Cloud 등 리눅스 환경 대응
        plt.rcParams['font.family'] = 'NanumGothic'
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

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

if not (start_str and end_str) and page in ["검색어 트렌드", "쇼핑 트렌드"]:
    st.info("날짜 범위를 설정해 주세요.")
    st.stop()

# 트렌드 페이지가 아닌 일반 검색 페이지는 날짜가 비어도 동작할 수 있으므로, 
# start_str와 end_str 체크는 트렌드 페이지만 필수로 설정

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
        
        st.write("---")
        
        # 1. 검색어 트렌드 / 쇼핑 트렌드 시각화 고도화
        if page in ["검색어 트렌드", "쇼핑 트렌드"]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 검색량 추이 그래프")
                try:
                    chart_df = df.set_index("날짜")
                    st.line_chart(chart_df, use_container_width=True)
                except Exception as e:
                    st.warning(f"그래프 표시 중 오류: {e}")
                    
            with col2:
                # 상관관계 히트맵 차트 추가
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 1:
                    st.subheader("📊 키워드 간 패턴 상관관계 히트맵")
                    try:
                        fig, ax = plt.subplots(figsize=(6, 4))
                        corr = df[numeric_cols].corr()
                        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax, vmin=-1, vmax=1)
                        st.pyplot(fig)
                        plt.close(fig)
                    except Exception as e:
                        st.warning(f"히트맵 생성 중 오류: {e}")
                else:
                    st.info("상관관계 분석을 보려면 2개 이상의 검색어를 입력해 주세요.")
            
            # 요약 지표 카드 추가
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                st.subheader("💡 키워드별 주요 지표 요약")
                metric_cols = st.columns(min(len(numeric_cols), 5))
                for i, col_name in enumerate(numeric_cols):
                    col_index = i % 5
                    with metric_cols[col_index]:
                        mean_val = df[col_name].mean()
                        max_val = df[col_name].max()
                        st.metric(
                            label=f"🔑 {col_name}", 
                            value=f"{mean_val:.1f} (평균)", 
                            delta=f"최대 {max_val:.1f}"
                        )
                
        # 2. 쇼핑 시각화 고도화
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
            
            st.write("---")
            col3, col4 = st.columns(2)
            
            with col3:
                # 가격 분포 히스토그램 추가
                if "lprice" in df.columns:
                    price_series = pd.to_numeric(df["lprice"], errors='coerce').dropna()
                    if not price_series.empty:
                        st.subheader("📊 전체 상품 가격 분포 히스토그램")
                        try:
                            fig, ax = plt.subplots(figsize=(6, 4))
                            sns.histplot(price_series, bins=15, kde=True, color="#3498db", ax=ax)
                            ax.set_title("가격 대별 상품 빈도")
                            ax.set_xlabel("가격 (원)")
                            ax.set_ylabel("상품 수")
                            st.pyplot(fig)
                            plt.close(fig)
                        except Exception as e:
                            st.warning(f"가격 히스토그램 생성 중 오류: {e}")
            
            with col4:
                # 상위 브랜드 점유율 도넛 차트 추가
                if "brand" in df.columns:
                    brand_series = df["brand"].replace("", "미분류").fillna("미분류")
                    brand_counts = brand_series.value_counts()
                    if not brand_counts.empty and len(brand_counts) > 1:
                        st.subheader("🍩 상위 브랜드 점유율 (도넛)")
                        try:
                            top_brands = brand_counts.head(5)
                            other_sum = brand_counts.iloc[5:].sum() if len(brand_counts) > 5 else 0
                            if other_sum > 0:
                                top_brands = pd.concat([top_brands, pd.Series({"기타": other_sum})])
                            
                            fig, ax = plt.subplots(figsize=(5, 5))
                            wedges, texts, autotexts = ax.pie(
                                top_brands, 
                                labels=top_brands.index, 
                                autopct='%1.1f%%', 
                                startangle=90, 
                                colors=sns.color_palette("pastel"),
                                wedgeprops=dict(width=0.4, edgecolor='w')
                            )
                            plt.setp(autotexts, size=9, weight="bold")
                            plt.setp(texts, size=9)
                            ax.set_title("상위 브랜드 비율")
                            st.pyplot(fig)
                            plt.close(fig)
                        except Exception as e:
                            st.warning(f"브랜드 점유율 도넛 차트 생성 중 오류: {e}")
                    else:
                        st.info("브랜드 분석을 진행할 데이터가 충분하지 않습니다.")
                        
        # 3. 블로그 / 카페 / 뉴스 시각화 고도화
        elif page in ["블로그", "카페", "뉴스"]:
            col1, col2 = st.columns(2)
            
            with col1:
                # 포스팅 및 뉴스 발행 추이
                if page in ["블로그", "카페"] and "postdate" in df.columns:
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
                        
                elif page == "뉴스" and "pubDate" in df.columns:
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
                        
            with col2:
                # 핵심 언급 단어 빈도 분석 막대 차트 추가
                if "title" in df.columns:
                    st.subheader("🔤 주요 언급 단어(명사) 빈도 TOP 10")
                    try:
                        word_counts = get_word_frequencies(df["title"].tolist())
                        if not word_counts.empty:
                            chart_data = word_counts.set_index("단어")[["bin_col" if "bin_col" in word_counts.columns else "빈도"]]
                            st.bar_chart(chart_data, use_container_width=True)
                        else:
                            st.info("분석할 단어가 충분하지 않습니다.")
                    except Exception as e:
                        st.warning(f"단어 빈도 차트 표시 중 오류: {e}")
                        
        # 4. 데이터 다운로드 기능 확장
        st.write("---")
        st.subheader("📥 데이터 다운로드")
        down_col1, down_col2 = st.columns(2)
        
        with down_col1:
            try:
                csv_data = download_df_as_csv(df)
                st.download_button(
                    label="📄 CSV 파일 다운로드", 
                    data=csv_data, 
                    file_name=f"naver_{page}_data.csv", 
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"CSV 다운로드 버튼 로드 실패: {e}")
                
        with down_col2:
            try:
                excel_data = download_df_as_excel(df)
                st.download_button(
                    label="📊 스타일링 엑셀(.xlsx) 다운로드", 
                    data=excel_data, 
                    file_name=f"naver_{page}_data.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"엑셀 다운로드 버튼 로드 실패: {e}")
