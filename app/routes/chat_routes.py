from flask import Blueprint, jsonify, request, Response
from app.services.naver_shopping_service import get_naver_shopping_data, format_product_info, get_price_comparison
from app.services.trend_service import get_related_topics  # 트렌드 서비스 추가
from app.llm_config import llm, prompt, trend_template, extract_keyword  # 트렌드 템플릿 및 키워드 추출 함수 추가
from app.redis_handler import RedisChatMemory
import json

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    session_id = request.json.get("session_id", "default_session")
    redis_memory = RedisChatMemory(session_id)

    # "트렌드" 또는 "유행" 키워드가 포함된 메시지 감지
    if "트렌드" in user_message or "유행" in user_message:
        # 키워드 추출
        keyword = extract_keyword(user_message)

        # 키워드가 유효한 경우에만 트렌드 데이터를 요청
        if keyword:
            trend_data = get_related_topics(keyword)

            if trend_data:  # 트렌드 데이터가 성공적으로 수집된 경우
                # 트렌드 템플릿에 데이터 포맷팅
                rising_topics = "\n".join([f"{i+1}. {topic['title']} ({topic['value']})" for i, topic in enumerate(trend_data['rising'])])
                top_topics = "\n".join([f"{i+1}. {topic['title']} ({topic['value']})" for i, topic in enumerate(trend_data['top'])])
                
                messages = trend_template.format(
                    keyword=keyword,
                    rising_topics=rising_topics,
                    top_topics=top_topics,
                    history="\n".join(redis_memory.get_recent_history(limit=5)),
                    human_input=user_message
                )

                # LLM에게 템플릿을 기반으로 응답 요청
                response = ""
                for chunk in llm.stream(messages):
                    if chunk.content:
                        response += chunk.content
                
                # Redis에 트렌드 요청 기록 저장
                redis_memory.save_context(user_message, response)

                # 응답 반환
                return jsonify({"response": response})

            else:
                # 트렌드 데이터 요청 실패 시 처리
                error_message = "트렌드 정보를 가져오는 데 실패했습니다."
                redis_memory.save_context(user_message, error_message)
                return jsonify({"response": error_message}), 500
            
             # 가격 비교 요청 처리
    if "가격 비교" in user_message:
        min_price, max_price = get_price_comparison(user_message)
        price_comparison_response = f"최저가: {min_price}원, 최고가: {max_price}원"
        redis_memory.save_context(user_message, price_comparison_response)
        return jsonify({"response": price_comparison_response})

    # 네이버 쇼핑 API로 상품 정보 가져오기
    items = get_naver_shopping_data(user_message)
    product_info = format_product_info(items)

    # 최근 대화 기록 불러오기
    recent_history = redis_memory.get_recent_history(limit=5)

    # 프롬프트 생성
    messages = prompt.format_messages(
        product_info=product_info,
        history="\n".join(recent_history),
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
