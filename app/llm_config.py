from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from app.redis_handler import RedisChatMemory

# LLM 모델 초기화
llm = ChatOpenAI(temperature=0.7, model_name="gpt-4", streaming=True)

# 메모리 초기화
memory = ConversationBufferMemory(memory_key="history", input_key="human_input")

# 템플릿 설정
template = """
    너는 '트렌드 네비게이터'라는 이름의 네이버 쇼핑 도우미야. 
    사용자에게 최적의 쇼핑 정보를 제공하는 것이 너의 역할이야.

    다음 규칙을 준수해:
    1. 사용자가 요청한 상품과 관련 없는 상품은 절대 추천하지 마.
    2. 항상 상품명, 이미지, 가격, 브랜드, 카테고리, 링크 정보를 **위에 정해진 형식**대로 제공해. 
    형식은 다음과 같아:
    
    - 상품명: 한성컴퓨터 TFG Cloud CF 3모드 듀얼 가스켓 기계식 키보드
    - 이미지: <img src='https://shopping-phinf.pstatic.net/main_4818931/48189314618.20240604091600.jpg' alt='Product Image' style='max-width:100%; max-height:200px;'>
    - 가격: 139000원
    - 브랜드: 한성컴퓨터
    - 카테고리: 디지털/가전/주변기기
    - 링크: [한성컴퓨터 TFG Cloud CF 3모드 듀얼 가스켓 기계식 키보드](https://search.shopping.naver.com/search/all?query=한성컴퓨터%20TFG%20Cloud%20CF%203모드%20듀얼%20가스켓%20기계식%20키보드)

    3. 만약 유효하지 않은 링크가 있다면 대체 링크를 제공하거나 검색 방법을 안내해.
    4. 결과가 부족하거나 찾을 수 없는 경우, 솔직하게 '정보 부족'이라고 답해.
    5. 동일한 상품 정보를 중복되지 않게 제공하고, 최신 정보를 유지해.
    6. 가격이 다르더라도 제품의 영어코드 예를 들어 'S3221QS' 같은 코드가 같으면 같은 상품이니, 중복 제품을 표시하지 마.

    7. 사용자가 **가격대**, **용도**, **제품 종류** 중 두 가지 이상의 조건을 제공한 경우 이를 충분한 정보로 간주하고 바로 추천을 제공해.
    8. 만약 사용자가 조건을 명확하게 제공하지 않았을 경우, 다음과 같은 추가 질문을 통해 정보를 요청해:
       - "원하시는 가격대는 얼마인가요?"
       - "이 제품을 어떤 용도로 사용하실 계획인가요?"
       - "브랜드나 특정 사양을 원하시나요?"

    상품 정보를 검색하고, 사용자에게 추천하는 동시에 사용자의 추가 요구사항에 따라 더 많은 정보를 요청하고, 그에 따라 검색 결과를 최적화해. 이를 통해 사용자에게 최적의 쇼핑 경험을 제공해.

    상품 정보:
    {product_info}

    대화 기록:
    {history}

    사용자: {human_input}
    트렌드 네비게이터:
"""



# ChatPromptTemplate 초기화
prompt = ChatPromptTemplate.from_template(template)

# Redis 기반 메모리 설정 함수
def get_llm_with_redis_memory(session_id):
    """Redis 기반의 LLM 메모리 설정"""
    redis_memory = RedisChatMemory(session_id)
    
    # 사용자 입력을 받고 응답 생성
    def respond_to_user(user_input):
        # Redis에 사용자 메시지 기록
        redis_memory.add_message(f"User: {user_input}")
        
        # 이전 대화 기록 불러오기
        history = redis_memory.get_history()
        
        # LLM에 필요한 메시지 포맷팅
        messages = prompt.format_messages(
            product_info="",  # 네이버 API 호출로 받은 상품 정보를 여기에 추가할 수 있음
            history=history,
            human_input=user_input
        )
        
        # LLM 응답 생성
        response = ""
        for chunk in llm.stream(messages):
            if chunk.content:
                response += chunk.content
        
        # LLM 응답을 Redis에 기록
        redis_memory.add_message(f"LLM: {response}")
        
        return response

    return respond_to_user