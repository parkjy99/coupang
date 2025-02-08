// 전역 함수로 선언
window.toggleSection = function(header) {
    const section = header.parentElement;
    section.classList.toggle('collapsed');
}

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const urlInput = document.getElementById('urlInput');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    let ratingChart = null;
    let trendChart = null;
    let lengthChart = null;
    let seasonalChart = null;
    let monthlyChart = null;
    let keywordTreemap = null;

    // 전역 변수로 EventSource 선언
    let progressEventSource;

    // 차트 초기화 함수
    function destroyCharts() {
        const charts = [ratingChart, trendChart, lengthChart, 
                       seasonalChart, monthlyChart, keywordTreemap];
        charts.forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        ratingChart = trendChart = lengthChart = 
        seasonalChart = monthlyChart = keywordTreemap = null;
    }

    function updateProgress(current, total) {
        const progressText = document.getElementById('progressText');
        if (progressText) {
            progressText.textContent = `${current} / ${total} 페이지 완료`;
        }
    }

    function resetUI() {
        // UI 초기화 함수
        destroyCharts();
        
        // 기본 통계 초기화
        const elements = {
            'totalReviews': '0',
            'averageRating': '0.0',
            'recommendation': '-',
            'positivePercent': '0%',
            'negativePercent': '0%',
            'neutralPercent': '0%',
            'avgLength': '0',
            'maxLength': '0'
        };

        // 안전하게 요소 업데이트
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // 컨테이너 초기화
        const keywordCloud = document.getElementById('keywordCloud');
        if (keywordCloud) {
            keywordCloud.innerHTML = '';
        }

        // 모든 섹션을 접힌 상태로 초기화
        document.querySelectorAll('.analysis-section').forEach(section => {
            section.classList.add('collapsed');
        });
    }

    function updateStats(data) {
        console.log("updateStats 호출됨, 제품 정보:", data.productInfo);  // 디버깅 로그
        
        // 안전하게 요소 업데이트하는 헬퍼 함수
        const updateElement = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        };

        // 상품 정보 업데이트
        updateElement('productTitle', data.productInfo.title);
        updateElement('totalReviews', data.reviewStats.totalReviews);
        updateElement('totalAllReviews', data.productInfo.totalReviews);

        // 기본 통계
        updateElement('averageRating', data.reviewStats.averageRating.toFixed(1));
        updateElement('ratingSum', data.reviewStats.ratingSum);
        updateElement('ratingCount', data.reviewStats.ratingCount);

        // 추천 결과
        if (data.recommendations) {
            updateElement('recommendation', data.recommendations.final_recommendation);
            updateElement('positivePercent', `${data.recommendations.positive_percent}%`);
            updateElement('negativePercent', `${data.recommendations.negative_percent}%`);
            updateElement('neutralPercent', `${data.recommendations.neutral_percent}%`);
        }

        // 리뷰 길이
        updateElement('avgLength', data.reviewLength.average_length);
        updateElement('maxLength', data.reviewLength.max_length);
        updateElement('shortReviews', `${data.reviewLength.distribution['짧은 리뷰 (50자 미만)']}개`);
        updateElement('mediumReviews', `${data.reviewLength.distribution['중간 리뷰 (50-200자)']}개`);
        updateElement('longReviews', `${data.reviewLength.distribution['긴 리뷰 (200자 이상)']}개`);

        // 키워드 트리맵
        const treeMapCtx = document.getElementById('keywordTreemap').getContext('2d');
        
        // 트리맵 데이터 구조화
        const treeMapData = {
            datasets: [{
                tree: data.reviewStats.keywords.map(k => ({
                    value: k.count,
                    label: `${k.word}`,
                    word: k.word,
                    count: k.count
                })),
                key: 'value',
                labels: {
                    display: true,
                    align: 'center',
                    position: 'middle',
                    font: {
                        family: 'Arial',
                        size: function(ctx) {
                            if (!ctx.raw?._data) return 14;
                            
                            const value = ctx.raw._data.value || 0;  // ctx.raw._data를 통해 접근
                            const maxValue = Math.max(...data.reviewStats.keywords.map(k => k.count));
                            const ratio = value / maxValue;
                            
                            if (ratio >= 0.8) return 24;
                            if (ratio >= 0.6) return 20;
                            if (ratio >= 0.4) return 18;
                            if (ratio >= 0.2) return 16;
                            return 14;
                        },
                        weight: 'bold'
                    },
                    color: function(ctx) {
                        if (!ctx.raw?._data) return '#4A5568';
                        
                        const value = ctx.raw._data.value || 0;  // ctx.raw._data를 통해 접근
                        const maxValue = Math.max(...data.reviewStats.keywords.map(k => k.count));
                        const ratio = value / maxValue;
                        
                        return ratio >= 0.4 ? '#FFFFFF' : '#4A5568';
                    }
                },
                backgroundColor: function(ctx) {
                    if (!ctx.raw?._data) return 'rgba(200, 200, 200, 0.3)';
                    
                    const value = ctx.raw._data.value || 0;
                    const maxValue = Math.max(...data.reviewStats.keywords.map(k => k.count));
                    
                    const ratio = value / maxValue;
                    if (ratio >= 0.8) return '#FFB5C2';  // 파스텔 핑크
                    if (ratio >= 0.6) return '#B5E5FF';  // 파스텔 블루
                    if (ratio >= 0.4) return '#FFE5B5';  // 파스텔 오렌지
                    if (ratio >= 0.2) return '#B5FFB5';  // 파스텔 그린
                    return '#E5E5B5';  // 파스텔 옐로우
                },
                borderWidth: 1,
                borderColor: '#fff',
                spacing: 3,
                captions: {
                    display: true,
                    align: 'center'
                }
            }]
        };

        // 트리맵 차트 생성
        keywordTreemap = new Chart(treeMapCtx, {
            type: 'treemap',
            data: treeMapData,
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: (items) => items[0]?.raw?.word || '',
                            label: (item) => {
                                const count = item.raw?.count || 0;
                                return `${count}회 등장`;
                            }
                        }
                    }
                }
            }
        });

        // 제품 정보 업데이트
        const attributesList = document.getElementById('productAttributes');
        console.log("attributesList 요소:", attributesList);  // 요소 확인
        console.log("제품 속성:", data.productInfo.attributes);  // 속성 데이터 확인

        if (attributesList && data.productInfo && data.productInfo.attributes) {
            attributesList.innerHTML = data.productInfo.attributes
                .map(attr => `<li class="product-attribute-item">${attr}</li>`)
                .join('');
        } else {
            console.error("제품 정보 바인딩 실패:", {
                attributesList: !!attributesList,
                productInfo: !!data.productInfo,
                attributes: data.productInfo?.attributes
            });
        }

        // 진정성 분석 결과 업데이트
        if (data.authenticity) {
            // 총점 업데이트
            document.getElementById('totalAuthenticityScore').textContent = 
                data.authenticity.total_score;
            
            // 각 요소별 진행바 업데이트
            const factors = data.authenticity.factors;
            
            // 구매 인증
            document.getElementById('verifiedPurchaseBar').style.width = 
                `${factors.verified_purchase}%`;
            document.getElementById('verifiedPurchasePercent').textContent = 
                `${factors.verified_purchase}%`;
            
            // 상세 리뷰
            document.getElementById('detailedReviewBar').style.width = 
                `${factors.detailed_review}%`;
            document.getElementById('detailedReviewPercent').textContent = 
                `${factors.detailed_review}%`;
            
            // 사진/동영상 첨부
            const mediaCount = data.reviewStats?.mediaReviews || 0;
            const totalReviews = data.reviewStats?.totalReviews || 1;
            
            // 미디어 데이터 디버깅 로그
            console.log('미디어 통계:', {
                미디어리뷰수: mediaCount,
                전체리뷰수: totalReviews,
                원본데이터: {
                    mediaReviews: data.reviewStats?.mediaReviews,
                    totalReviews: data.reviewStats?.totalReviews
                }
            });
            
            const mediaPercent = Math.round(
                (mediaCount / totalReviews) * 100
            ) || 0;
            
            console.log('미디어 비율 계산:', {
                계산식: `${mediaCount} / ${totalReviews} * 100`,
                결과: mediaPercent + '%'
            });
            
            document.getElementById('mediaAttachedBar').style.width = `${mediaPercent}%`;
            document.getElementById('mediaAttachedPercent').textContent = `${mediaPercent}%`;
            
            // 미디어 상세 정보 툴팁 추가
            const mediaDetails = `미디어 첨부 리뷰: ${mediaCount}개`;
            document.getElementById('mediaAttachedBar').title = mediaDetails;
            
            // 도움이 돼요
            document.getElementById('helpfulVotesBar').style.width = 
                `${factors.helpful_votes}%`;
            document.getElementById('helpfulVotesPercent').textContent = 
                `${factors.helpful_votes}%`;
            
            // 결론 업데이트
            document.getElementById('authenticityConclusion').textContent = 
                data.authenticity.conclusion;
        }
    }

    analyzeBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        const pages = parseInt(document.getElementById('pageInput').value);
        console.log('Selected pages:', pages);
        
        if (!url) {
            alert('URL을 입력해주세요.');
            return;
        }

        // UI 초기화
        resetUI();
        loading.classList.remove('hidden');
        results.classList.add('hidden');
        analyzeBtn.disabled = true;

        // 진행 상황 초기화 - 안전하게 처리
        const progressText = document.getElementById('progressText');
        if (progressText) {
            progressText.textContent = `0 / ${pages} 페이지 완료`;
        }
        updateProgress(0, pages);

        // 기존 EventSource 연결 종료
        if (progressEventSource) {
            progressEventSource.close();
        }

        // 진행 상황 모니터링을 위한 EventSource 연결
        progressEventSource = new EventSource('/progress');
        progressEventSource.onmessage = function(event) {
            const progress = JSON.parse(event.data);
            updateProgress(progress.current_page, pages);
        };

        fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                url: url,
                pages: pages
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("서버 응답 데이터:", data);  // 전체 응답 데이터 확인
            console.log("제품 정보:", data.productInfo);  // 제품 정보만 확인
            
            // 평점 분포 차트
            const ratingCtx = document.getElementById('ratingChart').getContext('2d');
            ratingChart = new Chart(ratingCtx, {
                type: 'bar',
                data: {
                    labels: ['1점', '2점', '3점', '4점', '5점'],
                    datasets: [{
                        label: '평점 분포',
                        data: [
                            data.reviewStats.ratingDistribution['1'] || 0,
                            data.reviewStats.ratingDistribution['2'] || 0,
                            data.reviewStats.ratingDistribution['3'] || 0,
                            data.reviewStats.ratingDistribution['4'] || 0,
                            data.reviewStats.ratingDistribution['5'] || 0
                        ],
                        backgroundColor: '#FFB5C2'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });

            // 리뷰 트렌드 차트
            const trendCtx = document.getElementById('trendChart').getContext('2d');
            trendChart = new Chart(trendCtx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: '일별 리뷰 수',
                        data: data.reviewStats.reviewTrends.dates.map((date, index) => ({
                            x: new Date(date),
                            y: data.reviewStats.reviewTrends.counts[index]
                        })),
                        backgroundColor: 'rgba(255, 181, 194, 0.7)',
                        borderColor: '#FFB5C2',
                        pointRadius: 6,
                        pointHoverRadius: 8,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const date = new Date(context.parsed.x).toLocaleDateString();
                                    return `${date}: ${context.parsed.y}개`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'YYYY-MM-DD'
                                }
                            },
                            title: {
                                display: true,
                                text: '날짜'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '리뷰 수'
                            }
                        }
                    }
                }
            });

            // 통계 업데이트 호출
            updateStats(data);

            // 리뷰 길이 분포 차트
            const lengthCtx = document.getElementById('reviewLengthChart').getContext('2d');
            lengthChart = new Chart(lengthCtx, {
                type: 'pie',
                data: {
                    labels: Object.keys(data.reviewLength.distribution),
                    datasets: [
                        {
                            data: Object.values(data.reviewLength.distribution),
                            backgroundColor: ['#FFB5C2', '#B5E5FF', '#FFE5B5']
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = Object.values(data.reviewLength.distribution).reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value}개 (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });

            // 계절별 구매 트렌드
            const seasonalCtx = document.getElementById('seasonalTrendChart').getContext('2d');
            seasonalChart = new Chart(seasonalCtx, {
                type: 'radar',
                data: {
                    labels: data.purchaseTrends.seasonal.labels,
                    datasets: [{
                        label: '구매 수',
                        data: data.purchaseTrends.seasonal.data,
                        backgroundColor: 'rgba(255, 181, 194, 0.2)',
                        borderColor: 'rgb(255, 181, 194)',
                        pointBackgroundColor: 'rgb(255, 181, 194)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgb(255, 181, 194)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true
                        }
                    }
                }
            });

            // 월별 구매 트렌드
            const monthlyCtx = document.getElementById('monthlyTrendChart').getContext('2d');
            monthlyChart = new Chart(monthlyCtx, {
                type: 'bar',
                data: {
                    labels: data.purchaseTrends.monthly.labels,
                    datasets: [{
                        label: '구매 수',
                        data: data.purchaseTrends.monthly.data,
                        backgroundColor: 'rgba(255, 181, 194, 0.7)'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '리뷰 수'
                            }
                        }
                    }
                }
            });

            // 첫 번째 섹션 자동 펼치기
            const firstSection = document.querySelector('.analysis-section');
            if (firstSection) {
                firstSection.classList.remove('collapsed');
            }
            
            results.classList.remove('hidden');
        })
        .catch(error => {
            if (progressEventSource) {
                progressEventSource.close();
            }
            alert(error.message || '분석 중 오류가 발생했습니다.');
        })
        .finally(() => {
            loading.classList.add('hidden');
            analyzeBtn.disabled = false;
        });
    });

    // 모든 섹션 헤더에 클릭 이벤트 리스너 추가
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', function() {
            const section = this.parentElement;
            section.classList.toggle('collapsed');
        });
    });
}); 