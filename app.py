import streamlit as st
import altair as alt
from src.analyzer import ReviewAnalyzer
from src.utils import validate_url
import pandas as pd
import json
import time

# Streamlit 앱 제목 설정
st.set_page_config(page_title="쿠팡 리뷰 분석기", layout="wide")

# CSS 스타일 추가
st.markdown("""
    <style>
        .stApp {
            background-color: #FFF5F7;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-box {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-label {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        .stat-value {
            color: #333;
            font-size: 1.5rem;
            font-weight: bold;
        }
        .chart-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }
        .stat-container {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stat-header {
            color: #666;
            font-size: 1.2rem;
            margin-bottom: 1rem;
        }
        .stat-value-large {
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.5rem;
        }
        .stat-subtext {
            color: #666;
            font-size: 0.9rem;
        }
        .chart-box {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("쿠팡 리뷰 분석기")

# 입력 섹션
url = st.text_input("쿠팡 상품 URL을 입력하세요", placeholder="https://www.coupang.com/vp/products/...")
col1, col2 = st.columns([5,1])
with col1:
    pages = st.select_slider("분석할 페이지 수", options=[5, 10, 20, 30, 50, 100, 1000], value=10)
with col2:
    analyze_button = st.button("분석하기", use_container_width=True)

if analyze_button:
    if not url:
        st.error("URL을 입력해주세요.")
    else:
        # URL 유효성 검사
        is_valid, error_message = validate_url(url)
        if not is_valid:
            st.error(f"유효하지 않은 URL: {error_message}")
        else:
            # 분석 시작
            with st.spinner("리뷰를 분석하고 있습니다..."):
                analyzer = ReviewAnalyzer()
                product_id = analyzer.extract_product_id(url)
                if not product_id:
                    st.error("올바른 쿠팡 URL이 아닙니다.")
                else:
                    # 리뷰 수집 및 분석
                    progress_placeholder = st.empty()
                    def update_progress(current_page):
                        progress_placeholder.text(f"진행 중... {current_page}/{pages} 페이지")
                    result = analyzer.get_reviews(product_id, max_pages=pages, progress_callback=update_progress)
                    
                    if not result or not result['reviews']:
                        st.error("이 상품의 리뷰를 찾을 수 없습니다.")
                    else:
                        analysis_result = analyzer.analyze_reviews(result['reviews'])
                        
                        if not analysis_result:
                            st.error("리뷰 분석 중 오류가 발생했습니다.")
                        else:
                            st.success("분석이 완료되었습니다!")
                            
                            # 제품 정보 표시
                            if 'product_info' in result:
                                st.subheader(result['product_info']['title'])
                                for attr in result['product_info']['attributes']:
                                    st.write(f"• {attr}")

                            # 통계 정보 계산
                            total_reviews = analysis_result['totalReviews']
                            avg_rating = analysis_result['averageRating']
                            positive_ratio = (analysis_result['ratingDistribution']['4'] + 
                                            analysis_result['ratingDistribution']['5']) / total_reviews * 100
                            media_ratio = 0  # 실제 데이터에서 계산 필요
                            
                            # 4개의 열로 통계 표시
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric(
                                    label="총 리뷰 수",
                                    value=f"{total_reviews}개",
                                    delta=f"전체 {result['product_info']['total_reviews']}개"
                                )
                            
                            with col2:
                                st.metric(
                                    label="평균 평점",
                                    value=f"{avg_rating:.1f}"
                                )
                            
                            with col3:
                                st.metric(
                                    label="긍정적 리뷰 비율",
                                    value=f"{positive_ratio:.1f}%"
                                )
                            
                            with col4:
                                st.metric(
                                    label="미디어 첨부 비율",
                                    value=f"{media_ratio:.1f}%"
                                )
                            
                            # 차트 섹션
                            st.markdown("---")
                            chart_col1, chart_col2 = st.columns(2)
                            
                            with chart_col1:
                                st.subheader("평점 분포")
                                rating_data = pd.DataFrame({
                                    '평점': ['1점', '2점', '3점', '4점', '5점'],
                                    '개수': [analysis_result['ratingDistribution'][str(i)] for i in range(1, 6)]
                                })
                                rating_chart = alt.Chart(rating_data).mark_bar(color='#FFB5C2').encode(
                                    x=alt.X('평점:N', axis=alt.Axis(labelAngle=0)),
                                    y=alt.Y('개수:Q', axis=alt.Axis(grid=True))
                                ).properties(height=400)
                                st.altair_chart(rating_chart, use_container_width=True)
                            
                            with chart_col2:
                                st.subheader("주요 키워드")
                                keywords_df = pd.DataFrame(analysis_result['keywords'])
                                if not keywords_df.empty:
                                    # 데이터프레임 정렬
                                    keywords_df = keywords_df.sort_values('count', ascending=True)
                                    
                                    # 차트 생성
                                    keyword_chart = alt.Chart(keywords_df).mark_bar(
                                        color='#B5E5FF',
                                        cornerRadius=3
                                    ).encode(
                                        x=alt.X('count:Q', 
                                               title='출현 빈도',
                                               axis=alt.Axis(grid=True)),
                                        y=alt.Y('word:N', 
                                               title='키워드',
                                               sort=None,  # 데이터프레임 정렬 순서 유지
                                               axis=alt.Axis(labelLimit=150)),  # 긴 키워드도 표시
                                        tooltip=['word', 'count']
                                    ).properties(
                                        height=min(400, len(keywords_df) * 30),  # 키워드 수에 따라 높이 조정
                                        width=400
                                    )
                                    st.altair_chart(keyword_chart, use_container_width=True)
                                    # 키워드 데이터 표시
                                    with st.expander("키워드 상세 데이터"):
                                        st.dataframe(keywords_df.sort_values('count', ascending=False)) 