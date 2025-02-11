import streamlit as st
import altair as alt
from src.analyzer import ReviewAnalyzer
from src.utils import validate_url
import pandas as pd
import json
import time
import numpy as np

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
        .metric-row {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
        }
        .url-input-container {
            background-color: white;
            border: 2px dashed #FFB5C2;
            border-radius: 10px;
            padding: 30px;
            margin: 20px 0;
            text-align: center;
            transition: all 0.3s ease;
        }
        .url-input-container:hover {
            border-color: #FF8FA3;
            background-color: #FFF5F7;
        }
        .stTextInput > div > div > input {
            font-size: 16px !important;
            padding: 15px !important;
            background-color: transparent !important;
            border: none !important;
            text-align: center !important;
        }
        .url-input-text {
            color: #666;
            margin-bottom: 10px;
            font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("쿠팡 리뷰 분석기")

# 드래그 앤 드롭 스타일의 입력 박스
st.markdown("""
    <div class="url-input-container">
        <div class="url-input-text">쿠팡 상품 URL을 드래그하여 입력하세요</div>
    </div>
""", unsafe_allow_html=True)

# 입력 섹션
url = st.text_input("", 
    placeholder="https://www.coupang.com/vp/products/...",
    label_visibility="collapsed"
)

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

                            # 상단 메트릭 카드들
                            st.markdown("""
                                <style>
                                .metric-row {
                                    display: flex;
                                    justify-content: space-between;
                                    gap: 20px;
                                    margin-bottom: 2rem;
                                }
                                .metric-card {
                                    background: white;
                                    padding: 20px;
                                    border-radius: 10px;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                    flex: 1;
                                }
                                </style>
                            """, unsafe_allow_html=True)
                            
                            # 도넛 차트용 데이터
                            total = len(result['reviews'])
                            positive = sum(1 for r in result['reviews'] if r['rating'] >= 4)
                            negative = sum(1 for r in result['reviews'] if r['rating'] <= 2)
                            neutral = total - positive - negative
                            
                            donut_data = pd.DataFrame({
                                'category': ['긍정', '중립', '부정'],
                                'value': [positive, neutral, negative],
                                'percentage': [
                                    f"{(positive/total)*100:.1f}%",
                                    f"{(neutral/total)*100:.1f}%",
                                    f"{(negative/total)*100:.1f}%"
                                ]
                            })
                            
                            # 도넛 차트
                            donut = alt.Chart(donut_data).mark_arc(innerRadius=50).encode(
                                theta=alt.Theta(field="value", type="quantitative"),
                                color=alt.Color(
                                    'category:N',
                                    scale=alt.Scale(
                                        domain=['긍정', '중립', '부정'],
                                        range=['#4CAF50', '#FFC107', '#FF5252']
                                    )
                                ),
                                tooltip=[
                                    alt.Tooltip('category:N', title='분류'),
                                    alt.Tooltip('value:Q', title='리뷰 수'),
                                    alt.Tooltip('percentage:N', title='비율')
                                ]
                            ).properties(width=200, height=200)
                            
                            col1, col2, col3 = st.columns([2,2,3])
                            with col1:
                                st.altair_chart(donut, use_container_width=True)
                            
                            with col2:
                                st.metric("평균 평점", f"{analysis_result['averageRating']:.1f}")
                                st.metric("리뷰 수", f"{total:,}개")
                            
                            with col3:
                                st.metric("긍정 리뷰 비율", f"{(positive/total)*100:.1f}%")
                                st.metric("부정 리뷰 비율", f"{(negative/total)*100:.1f}%")

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
                            # 1. 평점 분포
                            col1, col2, col3 = st.columns([2,2,3])
                            
                            with col1:
                                st.subheader("평점 분포")
                                rating_data = pd.DataFrame({
                                    '평점': ['1점', '2점', '3점', '4점', '5점'],
                                    '개수': [analysis_result['ratingDistribution'][str(i)] for i in range(1, 6)]
                                })
                                rating_chart = alt.Chart(rating_data).mark_bar().encode(
                                    x=alt.X('평점:N', title=None),
                                    y=alt.Y('개수:Q', title='리뷰 수'),
                                    color=alt.Color(
                                        '평점:N',
                                        scale=alt.Scale(scheme='pastel1'),
                                        legend=None
                                    ),
                                    tooltip=[
                                        alt.Tooltip('평점:N', title='평점'),
                                        alt.Tooltip('개수:Q', title='리뷰 수')
                                    ]
                                ).properties(height=300)
                                st.altair_chart(rating_chart, use_container_width=True)
                            
                            with col2:
                                st.subheader("리뷰 트렌드")
                                # 리뷰 트렌드 차트
                                if not result['reviews']:
                                    st.error("리뷰 데이터가 없습니다.")
                                else:
                                    # 유효한 날짜만 필터링
                                    valid_reviews = [
                                        {
                                            'date': pd.to_datetime(review['date']) if review['date'] != '날짜 없음' else None,
                                            'rating': review['rating']
                                        }
                                        for review in result['reviews']
                                        if review['date'] != '날짜 없음'
                                    ]
                                    
                                    timeline_df = pd.DataFrame([
                                        review for review in valid_reviews
                                        if review['date'] is not None
                                    ])
                                    
                                    if not timeline_df.empty:
                                        # 날짜별 리뷰 수 계산
                                        timeline_df['count'] = timeline_df.groupby('date')['rating'].transform('count')
                                        
                                        scatter = alt.Chart(timeline_df).mark_circle().encode(
                                            x=alt.X('date:T', 
                                                title='날짜',
                                                axis=alt.Axis(format='%Y-%m-%d')
                                            ),
                                            y=alt.Y('rating:Q', 
                                                title='평점', 
                                                scale=alt.Scale(domain=[0, 5])
                                            ),
                                            size=alt.Size(
                                                'count:Q',
                                                scale=alt.Scale(range=[50, 200]),
                                                legend=None
                                            ),
                                            color=alt.Color(
                                                'rating:Q',
                                                scale=alt.Scale(scheme='viridis'),
                                                legend=alt.Legend(title='평점')
                                            ),
                                            tooltip=[
                                                alt.Tooltip('date:T', title='날짜', format='%Y-%m-%d'),
                                                alt.Tooltip('rating:Q', title='평점'),
                                                alt.Tooltip('count:Q', title='리뷰 수')
                                            ]
                                        ).properties(
                                            height=300,
                                            title=alt.TitleParams(
                                                text='리뷰 트렌드',
                                                fontSize=16,
                                                color='#333'
                                            )
                                        )
                                        
                                        # 평균 평점 라인 추가
                                        line = alt.Chart(timeline_df).mark_line(
                                            color='red',
                                            strokeDash=[5,5]
                                        ).encode(
                                            x='date:T',
                                            y='mean(rating):Q'
                                        )
                                        
                                        # 차트 결합
                                        trend_chart = (scatter + line).configure_view(
                                            strokeWidth=0
                                        ).configure_axis(
                                            grid=True,
                                            gridColor='#f0f0f0'
                                        )
                                        
                                        st.altair_chart(trend_chart, use_container_width=True)

                            # 2. 키워드 트리맵 (전체 너비 사용)
                            st.subheader("주요 키워드 분석")
                            keywords_df = pd.DataFrame(analysis_result['keywords'])
                            if not keywords_df.empty:
                                # 상위 20개 키워드 선택
                                top_keywords = keywords_df.nlargest(20, 'count')
                                
                                # 격자 레이아웃 데이터 준비
                                grid_data = pd.DataFrame({
                                    'word': top_keywords['word'],
                                    'count': top_keywords['count'],
                                    'row': [i // 5 for i in range(20)],  # 4행
                                    'col': [i % 5 for i in range(20)]    # 5열
                                })
                                
                                # 격자 차트 생성
                                base = alt.Chart(grid_data).encode(
                                    x=alt.X('col:O', axis=None),
                                    y=alt.Y('row:O', axis=None),
                                    color=alt.Color(
                                        'count:Q',
                                        scale=alt.Scale(scheme='yelloworangered'),
                                        legend=alt.Legend(title='출현 빈도')
                                    ),
                                    tooltip=[
                                        alt.Tooltip('word:N', title='키워드'),
                                        alt.Tooltip('count:Q', title='출현 횟수')
                                    ]
                                ).properties(
                                    width=800,
                                    height=400
                                )
                                
                                # 사각형 그리기
                                rect = base.mark_rect(
                                    stroke='white',
                                    strokeWidth=2,
                                    opacity=0.8
                                )
                                
                                # 키워드 텍스트 추가
                                text = base.mark_text(
                                    align='center',
                                    baseline='middle',
                                    fontSize=14,
                                    color='white'
                                ).encode(
                                    text='word:N'
                                )
                                
                                # 차트 결합
                                final_chart = (rect + text).configure_view(
                                    strokeWidth=0
                                )
                                
                                st.altair_chart(final_chart, use_container_width=True)

                            # 3. 리뷰 길이 분포
                            with st.expander("리뷰 길이 분포 ▼"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    # 리뷰 길이 히스토그램 데이터 준비
                                    lengths = [len(r['content']) for r in result['reviews']]
                                    length_df = pd.DataFrame({'length': lengths})
                                    
                                    # 히스토그램 차트
                                    hist = alt.Chart(length_df).mark_bar(
                                        color='#FFB5C2',
                                        opacity=0.6
                                    ).encode(
                                        x=alt.X('length:Q',
                                            bin=alt.Bin(maxbins=30),
                                            title='리뷰 길이 (글자)'
                                        ),
                                        y=alt.Y('count()',
                                            title='리뷰 수'
                                        ),
                                        tooltip=[
                                            alt.Tooltip('length:Q', title='리뷰 길이', bin=True),
                                            alt.Tooltip('count()', title='리뷰 수')
                                        ]
                                    ).properties(
                                        height=300,
                                        title='리뷰 길이 분포'
                                    )
                                    
                                    st.altair_chart(hist, use_container_width=True)
                                
                                with col2:
                                    # 통계 정보 표시
                                    st.metric("평균 리뷰 길이", 
                                            f"{sum(len(r['content']) for r in result['reviews']) / len(result['reviews']):.1f}자")
                                    st.metric("최대 리뷰 길이",
                                            f"{max(len(r['content']) for r in result['reviews'])}자")
                                    st.metric("최소 리뷰 길이",
                                            f"{min(len(r['content']) for r in result['reviews'])}자")

                            # 4. 구매 트렌드 분석
                            with st.expander("구매 트렌드 분석 ▼"):
                                # 유효한 날짜만 필터링하여 월별 데이터 생성
                                valid_reviews = [
                                    review for review in result['reviews']
                                    if review['date'] != '날짜 없음'
                                ]
                                
                                if valid_reviews:
                                    dates = pd.to_datetime([r['date'] for r in valid_reviews])
                                    monthly_df = pd.DataFrame({
                                        'date': dates,
                                        'count': 1
                                    })
                                    
                                    # 월별 집계
                                    monthly_counts = monthly_df.groupby(monthly_df['date'].dt.month)['count'].sum().reset_index()
                                    monthly_counts['month'] = monthly_counts['date'].map({
                                        1:'1월', 2:'2월', 3:'3월', 4:'4월', 5:'5월', 6:'6월',
                                        7:'7월', 8:'8월', 9:'9월', 10:'10월', 11:'11월', 12:'12월'
                                    })
                                    
                                    # 막대 차트
                                    bar = alt.Chart(monthly_counts).mark_bar(
                                        color='#FFB5C2'
                                    ).encode(
                                        x=alt.X('month:N', title='월', sort=None),
                                        y=alt.Y('count:Q', title='리뷰 수'),
                                        tooltip=[
                                            alt.Tooltip('month:N', title='월'),
                                            alt.Tooltip('count:Q', title='리뷰 수')
                                        ]
                                    ).properties(
                                        title='월별 리뷰 수',
                                        width=600,
                                        height=300
                                    )
                                    
                                    st.altair_chart(bar, use_container_width=True) 