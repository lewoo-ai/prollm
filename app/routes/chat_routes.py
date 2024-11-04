# chat_routes.py
from flask import Blueprint, jsonify, request, Response
from app.services.naver_shopping_service import get_naver_shopping_data, format_product_info
from app.services.trend_service import get_related_topics  # 트렌드 서비스 추가
from app.llm_config import llm, prompt
from app.redis_handler import RedisChatMemory
import json

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    session_id = request.json.get("session_id", "default_session")  # 세션 ID를 요청에서 받아오거나 기본값 사용
    redis_memory = RedisChatMemory(session_id)

    # "트렌드"라는 키워드가 포함된 메시지 감지
    if "트렌드" in user_message:
        # 예시 키워드로 사용자가 입력한 메시지를 그대로 전달
        keyword = user_message.replace("트렌드 알려줘", "").strip()
        trend_data = get_related_topics(keyword)

        # 트렌드 데이터를 스트리밍 응답 형태로 전달
        def generate_trend_response():
            trend_response = json.dumps({"trend_data": trend_data}, ensure_ascii=False)
            yield f"data: {trend_response}\n\n"
            
            # Redis에 트렌드 관련 요청 기록 저장
            redis_memory.save_context(user_message, trend_response)

        return Response(generate_trend_response(), content_type='text/event-stream')

    # 네이버 쇼핑 API로 상품 정보 가져오기
    items = get_naver_shopping_data(user_message)
    product_info = format_product_info(items)

    # Redis에서 대화 기록 불러오기
    history = redis_memory.load_memory_variables()["history"]

    # 프롬프트 생성
    messages = prompt.format_messages(
        product_info=product_info,
        history=history,
        human_input=user_message
    )

    def generate():
        full_response = ""
        for chunk in llm.stream(messages):
            if chunk.content:
                full_response += chunk.content
                yield f"data: {json.dumps({'response': full_response})}\n\n"
        
        # Redis에 채팅 기록 업데이트
        redis_memory.save_context(user_message, full_response)

    return Response(generate(), content_type='text/event-stream')
