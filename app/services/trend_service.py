# trend_service.py
import os
import requests

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_related_topics(keyword):
    """키워드에 대한 관련 주제 트렌드를 수집하여 상위 주제를 반환"""
    params = {
        "engine": "google_trends",
        "q": keyword,
        "data_type": "RELATED_TOPICS",
        "api_key": SERPAPI_KEY
    }
    
    search = GoogleSearch(params)
    results = search.get_dict()

    # 관련 주제 데이터 추출
    related_topics = results.get("related_topics", {})
    rising_topics = related_topics.get("rising", [])
    top_topics = related_topics.get("top", [])

    # 상위 3개의 상승 및 인기 주제 정렬
    sorted_rising_topics = sorted(
        rising_topics, 
        key=lambda x: int(x["value"]), 
        reverse=True
    )[:3]
    
    sorted_top_topics = sorted(
        top_topics, 
        key=lambda x: int(x["value"]), 
        reverse=True
    )[:3]

    topics_data = {
        "rising": [
            {
                "title": topic["topic"]["title"],
                "type": topic["topic"]["type"],
                "value": topic["value"],
                "link": topic["link"]
            }
            for topic in sorted_rising_topics
        ],
        "top": [
            {
                "title": topic["topic"]["title"],
                "type": topic["topic"]["type"],
                "value": topic["value"],
                "link": topic["link"]
            }
            for topic in sorted_top_topics
        ]
    }

    return topics_data
