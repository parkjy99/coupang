from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from collections import Counter
import re
import time
from webdriver_manager.chrome import ChromeDriverManager
import platform
import os

class ReviewAnalyzer:
    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--start-maximized')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

    def extract_product_id(self, url):
        match = re.search(r'products/(\d+)', url)
        return match.group(1) if match else None

    def get_reviews(self, product_id, max_pages=10, progress_callback=None):
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=self.chrome_options
            )
            
            # navigator.webdriver 비활성화
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false
                    })
                """
            })
            
            url = f'https://www.coupang.com/vp/products/{product_id}'
            print(f"상품 페이지 접속: {url}")
            driver.get(url)
            # 동적 대기로 변경
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'prod-buy-header__title'))
                )
            except:
                pass

            # 제품 정보 가져오기
            product_info = {}
            try:
                # XPath와 CSS 셀렉터 모두 시도
                description_selectors = [
                    '//*[@id="contents"]/div[2]/div[1]/div[3]/div[16]/ul/li',  # XPath
                    'ul.prod-description-attribute li.prod-attr-item',  # CSS 셀렉터
                    '//ul[contains(@class, "prod-description-attribute")]/li'  # 대체 XPath
                ]
                
                product_info['attributes'] = []
                
                for selector in description_selectors:
                    try:
                        if selector.startswith('//'):
                            items = driver.find_elements(By.XPATH, selector)
                        else:
                            items = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        if items:
                            for item in items:
                                text = item.text.strip()
                                if text and 'style="display: none"' not in item.get_attribute('outerHTML'):
                                    product_info['attributes'].append(text)
                            print(f"제품 정보 {len(product_info['attributes'])}개 수집 완료")
                            break
                    except Exception as e:
                        print(f"셀렉터 {selector} 시도 중 오류: {str(e)}")
                        continue
                
                if not product_info['attributes']:
                    print("제품 정보를 찾을 수 없습니다.")
                
            except Exception as e:
                print(f"제품 정보 수집 중 오류: {str(e)}")
                product_info['attributes'] = []

            # 디버깅을 위한 출력
            if product_info['attributes']:
                print("수집된 제품 정보:")
                for attr in product_info['attributes']:
                    print(f"- {attr}")
            else:
                print("수집된 제품 정보가 없습니다.")

            # 상품 제목 가져오기
            try:
                title_selectors = [
                    'h1.prod-buy-header__title',  # 새로운 셀렉터
                    'h2.prod-buy-header__title',  # 기존 셀렉터
                    '//*[@id="productTitle"]',  # XPath
                    '//h1[contains(@class, "prod-buy-header__title")]'  # 대체 XPath
                ]
                
                product_title = None
                for selector in title_selectors:
                    try:
                        if selector.startswith('//'):
                            title_element = driver.find_element(By.XPATH, selector)
                        else:
                            title_element = driver.find_element(By.CSS_SELECTOR, selector)
                        
                        product_title = title_element.text.strip()
                        if product_title:
                            print(f"상품 제목 찾음: {product_title}")
                            break
                    except:
                        continue
                
                if not product_title:
                    print("상품 제목을 찾을 수 없습니다.")
                    product_title = "제목을 가져올 수 없음"
                
            except Exception as e:
                print(f"상품 제목 수집 중 오류: {str(e)}")
                product_title = "제목을 가져올 수 없음"

            # 리뷰 수 가져오기
            total_reviews = 0
            review_count_selectors = [
                'span.count',  # 기존 셀렉터
                'span.product-tab-review-count',  # 새로운 셀렉터
                '//*[@id="btfTab"]/ul[1]/li[2]/span',  # XPath
                '//li[@name="review"]/span'  # 대체 XPath
            ]
            
            for selector in review_count_selectors:
                try:
                    if selector.startswith('//'):
                        count_element = driver.find_element(By.XPATH, selector)
                    else:
                        count_element = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    count_text = count_element.text.strip()
                    # 숫자만 추출 (괄호, 쉼표 등 제거)
                    count_number = re.sub(r'[^\d]', '', count_text)
                    if count_number:
                        total_reviews = int(count_number)
                        print(f"총 리뷰 수 찾음: {total_reviews}개")
                        break
                except:
                    continue
            
            if total_reviews == 0:
                print("리뷰 수를 찾을 수 없습니다.")

            # navigator.webdriver 값 체크
            webdriver_value = driver.execute_script("return navigator.webdriver")
            print(f"navigator.webdriver 값: {webdriver_value}")
            
            try:
                # 리뷰 탭 찾기 및 클릭
                print("리뷰 탭 찾는 중...")
                review_tab = None
                
                # 여러 선택자로 시도
                selectors = [
                    'a[href="#productReview"]',
                    '#btfTab > ul.tab-titles > li:nth-child(2)',
                    '//a[contains(text(), "상품평")]',
                    '//a[contains(@href, "productReview")]'
                ]
                
                for selector in selectors:
                    try:
                        if selector.startswith('//'):
                            review_tab = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            review_tab = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        if review_tab:
                            break
                    except:
                        continue
                
                if review_tab:
                    print("리뷰 탭 발견, 클릭 시도...")
                    driver.execute_script("arguments[0].click();", review_tab)
                    time.sleep(3)
                    
                    # 최신순 버튼 찾기 시도
                    print("최신순 버튼 찾는 중...")
                    newest_btn = None
                    
                    # 여러 선택자로 시도
                    newest_selectors = [
                        'button.sdp-review__article__order__sort__newest-btn',
                        'button[data-order="DATE_DESC"]',
                        '.js_reviewArticleNewListBtn',
                        '//*[@id="btfTab"]/ul[2]/li[2]/div/div[6]/section[2]/div[1]/button[2]',
                        '//button[contains(@class, "newest-btn")]',
                        '//button[contains(text(), "최신순")]'
                    ]
                    
                    for selector in newest_selectors:
                        try:
                            if selector.startswith('//'):
                                newest_btn = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            else:
                                newest_btn = WebDriverWait(driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            if newest_btn:
                                print(f"최신순 버튼 발견 (선택자: {selector})")
                                break
                        except:
                            continue
                    
                    if newest_btn:
                        print("최신순 버튼 발견, 클릭 시도...")
                        # 버튼이 보이도록 스크롤
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", newest_btn)
                        time.sleep(2)
                        
                        try:
                            driver.execute_script("arguments[0].click();", newest_btn)
                            print("최신순 버튼 클릭 성공")
                            time.sleep(3)
                        except Exception as e:
                            print(f"최신순 버튼 클릭 실패: {str(e)}")
                    else:
                        print("최신순 버튼을 찾을 수 없습니다")

                    # 전체 리뷰 수 가져오기 시도
                    review_count_selectors = [
                        '//div[@class="sdp-review__average__total-star__info-count"]',  # 새로운 XPath
                        '/html/body/div[2]/section/div[2]/div[2]/div[7]/ul[2]/li[2]/div/div[4]/section[1]/div[1]/div[2]',  # 전체 XPath
                        'div.sdp-review__average__total-star__info-count'  # CSS 선택자
                    ]

                    for selector in review_count_selectors:
                        try:
                            if selector.startswith('//'):
                                count_element = driver.find_element(By.XPATH, selector)
                            else:
                                count_element = driver.find_element(By.CSS_SELECTOR, selector)
                            
                            count_text = count_element.text.strip()
                            # 숫자만 추출 (쉼표 제거)
                            count_number = re.sub(r'[^\d]', '', count_text)
                            if count_number:
                                total_reviews = int(count_number)
                                print(f"총 리뷰 수 찾음: {total_reviews}개")
                                break
                        except:
                            continue

                    if total_reviews == 0:
                        print("리뷰 수를 찾을 수 없습니다.")

            except Exception as e:
                print(f"처리 중 오류 발생: {str(e)}")

            reviews = []
            page = 1
            while page <= max_pages:
                try:
                    if progress_callback:
                        progress_callback(page)
                    print(f"페이지 {page}/{max_pages} 처리 중...")
                    
                    # 1. 현재 페이지의 리뷰 수집
                    review_elements = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article.sdp-review__article__list'))
                    )
                    
                    if not review_elements:
                        print("더 이상 리뷰가 없습니다.")
                        break
                    
                    print(f"페이지 {page}에서 {len(review_elements)}개의 리뷰 발견")
                    
                    # 리뷰 파싱 및 저장
                    for review in review_elements:
                        try:
                            # 평점 (별점) 계산
                            rating_div = review.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__info__product-info__star-orange')
                            rating_style = rating_div.get_attribute('style')
                            if rating_style:
                                width_percent = int(re.search(r'width:\s*(\d+)%', rating_style).group(1))
                                rating = round(width_percent / 20)  # 100% -> 5점
                            else:
                                rating = 0
                            
                            content = ""
                            
                            # 제목 수집 시도
                            try:
                                headline = review.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__headline').text.strip()
                                if headline:
                                    content += headline + "\n"
                            except:
                                pass
                                
                            # 내용 수집 시도
                            try:
                                review_text = review.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__review').text.strip()
                                if review_text:
                                    content += review_text
                            except:
                                pass
                                
                            # 날짜
                            try:
                                date = review.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__info__product-info__reg-date').text.strip()
                            except:
                                date = "날짜 없음"
                                
                            # 모든 리뷰 저장 (내용이 비어있어도 저장)
                            reviews.append({
                                'rating': rating,
                                'content': content.strip(),
                                'date': date
                            })
                            
                        except Exception as e:
                            print(f"리뷰 파싱 중 오류: {str(e)}")
                            continue

                    # 2. 다음 페이지로 이동
                    if page % 10 == 0:  # 10, 20, 30... 페이지일 때
                        try:
                            next_group_button = driver.find_element(By.CSS_SELECTOR, 'button.sdp-review__article__page__next')
                            if next_group_button.is_enabled():
                                driver.execute_script("arguments[0].click();", next_group_button)
                                print(f"다음 페이지 그룹으로 이동 (현재 페이지: {page})")
                                time.sleep(0.5)
                            else:
                                print("마지막 페이지 그룹입니다.")
                                break
                        except Exception as e:
                            print(f"다음 페이지 그룹 버튼을 찾을 수 없음: {str(e)}")
                            break

                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, f'button.sdp-review__article__page__num[data-page="{page + 1}"]')
                        if not next_button.is_enabled():
                            print("다음 페이지 버튼이 비활성화 상태")
                            break
                        driver.execute_script("arguments[0].click();", next_button)
                        print(f"페이지 {page + 1}로 이동")
                        time.sleep(0.5)  # 대기 시간 감소
                        page += 1
                    except Exception as e:
                        print(f"다음 페이지 버튼을 찾을 수 없음: {str(e)}")
                        break  # 다음 페이지 버튼을 찾을 수 없을 때만 break

                except Exception as e:
                    print(f"페이지 처리 중 오류: {str(e)}")
                    break

            print(f"총 {len(reviews)}개의 리뷰 수집 완료 (처리된 페이지: {page-1})")
            driver.quit()
            return {
                'product_info': {
                    'title': product_title,
                    'total_reviews': total_reviews,
                    'attributes': product_info['attributes']
                },
                'reviews': reviews
            }
            
        except Exception as e:
            print("리뷰 수집 중 오류 발생:", str(e))
            if 'driver' in locals():
                driver.quit()
            return None

    def analyze_reviews(self, reviews):
        print("Analyzing reviews:", len(reviews))  # 디버깅 로그
        try:
            # 평점 분포 계산
            rating_dist = {str(i): 0 for i in range(1, 6)}
            for review in reviews:
                rating = str(review.get('rating', 0))
                if rating in rating_dist:
                    rating_dist[rating] += 1
            
            print("Rating distribution:", rating_dist)  # 디버깅 로그
            
            # 리뷰 트렌드 분석
            review_trends = {'dates': [], 'counts': []}
            try:
                df = pd.DataFrame(reviews)
                df['date'] = pd.to_datetime(df['date'])
                daily_counts = df.groupby(df['date'].dt.date).size()
                review_trends = {
                    'dates': [str(date) for date in daily_counts.index],
                    'counts': [int(count) for count in daily_counts.values]
                }
            except Exception as e:
                print(f"리뷰 트렌드 분석 중 오류: {str(e)}")
            
            # 키워드 분석
            keywords = []
            try:
                words = []
                for review in reviews:
                    content = str(review.get('content', ''))
                    # 한글 단어만 추출 (2글자 이상)
                    korean_words = re.findall(r'[가-힣]{2,}', content)
                    words.extend(korean_words)
                
                # 불용어 설정
                stop_words = ['있는', '없는', '같은', '이런', '저런', '그런', '이거', '저거', '그거']
                
                # 유효한 단어만 필터링
                valid_words = [word for word in words if word not in stop_words]
                
                # 키워드 카운트
                keyword_counts = Counter(valid_words)
                
                # 상위 10개 키워드 선택
                keywords = [
                    {'word': word, 'count': count}
                    for word, count in keyword_counts.most_common(10)
                ]
            except Exception as e:
                print(f"키워드 분석 중 오류: {str(e)}")
            
            # 평균 평점 계산
            total_rating = sum(int(k) * v for k, v in rating_dist.items())
            total_reviews = sum(rating_dist.values())
            avg_rating = total_rating / total_reviews if total_reviews > 0 else 0
            
            print("Average rating:", avg_rating)  # 디버깅 로그
            
            return {
                'totalReviews': total_reviews,
                'averageRating': avg_rating,
                'ratingDistribution': rating_dist,
                'reviewTrends': review_trends,
                'keywords': keywords
            }
            
        except Exception as e:
            print(f"Error in analyze_reviews: {str(e)}")  # 디버깅 로그
            return None

    def analyze_recommendations(self, reviews):
        """리뷰 내용을 기반으로 추천/비추천 분석"""
        try:
            # 긍정적인 키워드
            positive_words = [
                '좋아요', '만족', '추천', '최고', '굿', '좋은', '훌륭', 
                '괜찮', '완벽', '강추', '좋다', '맘에들어', '맘에듬'
            ]
            
            # 부정적인 키워드
            negative_words = [
                '별로', '실망', '비추', '안좋', '후회', '구리', '별루',
                '안맘에들', '그닥', '최악', '형편없', '나쁨', '싫어'
            ]
            
            recommendations = {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'total': len(reviews)
            }
            
            for review in reviews:
                content = review.get('content', '').lower()
                rating = review.get('rating', 0)
                
                # 긍정/부정 점수 계산
                positive_score = sum(1 for word in positive_words if word in content)
                negative_score = sum(1 for word in negative_words if word in content)
                
                # 별점도 고려 (4-5점은 긍정, 1-2점은 부정)
                if rating >= 4:
                    positive_score += 1
                elif rating <= 2:
                    negative_score += 1
                
                # 최종 판단
                if positive_score > negative_score:
                    recommendations['positive'] += 1
                elif negative_score > positive_score:
                    recommendations['negative'] += 1
                else:
                    recommendations['neutral'] += 1
            
            # 백분율 계산
            total = len(reviews)
            recommendations['positive_percent'] = round((recommendations['positive'] / total) * 100, 1)
            recommendations['negative_percent'] = round((recommendations['negative'] / total) * 100, 1)
            recommendations['neutral_percent'] = round((recommendations['neutral'] / total) * 100, 1)
            
            # 최종 추천 여부 결정
            if recommendations['positive_percent'] >= 70:
                recommendations['final_recommendation'] = '강력 추천'
            elif recommendations['positive_percent'] >= 50:
                recommendations['final_recommendation'] = '추천'
            elif recommendations['negative_percent'] >= 70:
                recommendations['final_recommendation'] = '비추천'
            elif recommendations['negative_percent'] >= 50:
                recommendations['final_recommendation'] = '약간 비추천'
            else:
                recommendations['final_recommendation'] = '중립'
            
            return recommendations
            
        except Exception as e:
            print(f"추천 분석 중 오류: {str(e)}")
            return None

    def analyze_sentiment_trend(self, reviews):
        """월별 감성 분석 트렌드"""
        df = pd.DataFrame(reviews)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        
        monthly_sentiment = {
            'dates': [],
            'positive': [],
            'negative': [],
            'neutral': []
        }
        
        for month in sorted(df['month'].unique()):
            month_reviews = df[df['month'] == month]
            total = len(month_reviews)
            if total == 0:
                continue
            
            positive = len(month_reviews[month_reviews['rating'] >= 4])
            negative = len(month_reviews[month_reviews['rating'] <= 2])
            neutral = total - positive - negative
            
            monthly_sentiment['dates'].append(month)
            monthly_sentiment['positive'].append(round(positive/total * 100, 1))
            monthly_sentiment['negative'].append(round(negative/total * 100, 1))
            monthly_sentiment['neutral'].append(round(neutral/total * 100, 1))
        
        return monthly_sentiment

    def analyze_review_length(self, reviews):
        """리뷰 길이 분포 분석"""
        lengths = [len(review['content']) for review in reviews]
        return {
            'average_length': round(sum(lengths) / len(lengths), 1),
            'max_length': max(lengths),
            'min_length': min(lengths),
            'distribution': {
                '짧은 리뷰 (50자 미만)': len([l for l in lengths if l < 50]),
                '중간 리뷰 (50-200자)': len([l for l in lengths if 50 <= l < 200]),
                '긴 리뷰 (200자 이상)': len([l for l in lengths if l >= 200])
            }
        }

    def analyze_rating_keywords(self, reviews):
        """평점별 주요 키워드 분석"""
        df = pd.DataFrame(reviews)
        
        # 긍정 리뷰 (4-5점)
        positive_reviews = ' '.join(df[df['rating'] >= 4]['content'])
        # 부정 리뷰 (1-2점)
        negative_reviews = ' '.join(df[df['rating'] <= 2]['content'])
        
        # 불용어 설정
        stop_words = ['있는', '없는', '같은', '이런', '저런', '그런', '이거', '저거', '그거']
        
        def extract_keywords(text):
            words = [word for word in text.split() 
                    if len(word) >= 2 and word not in stop_words]
            return Counter(words).most_common(10)
        
        return {
            'positive': [{'word': word, 'count': count} 
                        for word, count in extract_keywords(positive_reviews)],
            'negative': [{'word': word, 'count': count} 
                        for word, count in extract_keywords(negative_reviews)]
        }

    def analyze_purchase_trends(self, reviews):
        """계절별/월별 구매 패턴 분석"""
        df = pd.DataFrame(reviews)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        df['season'] = df['date'].dt.month.map({
            1: '겨울', 2: '겨울', 3: '봄',
            4: '봄', 5: '봄', 6: '여름',
            7: '여름', 8: '여름', 9: '가을',
            10: '가을', 11: '가을', 12: '겨울'
        })
        
        season_counts = df['season'].value_counts()
        month_counts = df['month'].value_counts().sort_index()
        
        return {
            'seasonal': {
                'labels': ['봄', '여름', '가을', '겨울'],
                'data': [
                    int(season_counts.get('봄', 0)),
                    int(season_counts.get('여름', 0)),
                    int(season_counts.get('가을', 0)),
                    int(season_counts.get('겨울', 0))
                ]
            },
            'monthly': {
                'labels': ['1월', '2월', '3월', '4월', '5월', '6월', 
                          '7월', '8월', '9월', '10월', '11월', '12월'],
                'data': [int(month_counts.get(m, 0)) for m in range(1, 13)]
            }
        }

    def analyze_review_authenticity(self, reviews):
        """리뷰의 진정성을 분석하는 함수"""
        total_reviews = len(reviews)
        if total_reviews == 0:
            return None
            
        authenticity_scores = {
            'verified_purchase': 0,  # 구매 인증
            'detailed_review': 0,    # 상세 리뷰
            'media_attached': 0,     # 사진/동영상 첨부
            'helpful_votes': 0       # 도움이 돼요
        }
        
        for review in reviews:
            # 구매 인증 확인
            if review.get('is_verified_purchase', False):
                authenticity_scores['verified_purchase'] += 1
                
            # 상세 리뷰 확인 (50자 이상)
            if len(review.get('content', '')) >= 50:
                authenticity_scores['detailed_review'] += 1
                
            # 사진/동영상 첨부 확인
            if review.get('has_media', False):
                authenticity_scores['media_attached'] += 1
                
            # 도움이 돼요 확인
            if review.get('helpful_votes', 0) > 0:
                authenticity_scores['helpful_votes'] += 1
        
        # 백분율 계산
        percentages = {
            key: round((value / total_reviews) * 100, 1)
            for key, value in authenticity_scores.items()
        }
        
        # 총점 계산 (가중치 적용)
        weights = {
            'verified_purchase': 0.4,  # 40%
            'detailed_review': 0.3,    # 30%
            'media_attached': 0.2,     # 20%
            'helpful_votes': 0.1       # 10%
        }
        
        total_score = sum(
            percentages[key] * weights[key]
            for key in authenticity_scores.keys()
        )
        
        # 결과 반환
        return {
            'total_score': round(total_score, 1),
            'factors': percentages,
            'conclusion': self._get_authenticity_conclusion(total_score)
        }
        
    def _get_authenticity_conclusion(self, score):
        """진정성 점수에 따른 결론 생성"""
        if score >= 80:
            return "매우 신뢰할 수 있는 리뷰들입니다. 구매 인증과 상세한 리뷰가 많습니다."
        elif score >= 60:
            return "대체로 신뢰할 수 있는 리뷰들입니다. 일부 개선의 여지가 있습니다."
        elif score >= 40:
            return "보통 수준의 신뢰도입니다. 더 많은 상세 리뷰가 있으면 좋겠습니다."
        else:
            return "신뢰도가 다소 낮습니다. 더 많은 구매 인증과 상세 리뷰가 필요합니다." 