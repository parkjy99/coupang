def validate_url(url):
    """URL 유효성 검사"""
    if not url:
        return False, "URL이 필요합니다."
    if "coupang.com" not in url:
        return False, "쿠팡 URL이 아닙니다."
    return True, None 