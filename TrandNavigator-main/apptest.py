import os
import requests
from dotenv import load_dotenv
from PIL import Image
import io
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda

# API 키 설정
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

# 네이버 쇼핑 API 데이터 가져오기
def get_naver_shopping_data(query, display=5):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json().get('items', [])

# 상품 정보 포맷팅
def format_product_info(items):
    formatted_items = []
    for item in items:
        formatted_item = (
            f"상품명: {item['title']}\n"
            f"가격: {item['lprice']}원\n"
            f"URL: {item['link']}\n"
        )
        formatted_items.append(formatted_item)
    return "\n".join(formatted_items)

# 이미지 분석 함수 (디버깅 메시지 추가)
def analyze_image(image_path):
    print(f"이미지 경로: {image_path}")
    
    # 이미지 열기 시도
    try:
        image = Image.open(image_path)
        print("이미지 파일 열기 성공")
    except Exception as e:
        print(f"이미지 파일 열기 실패: {e}")
        return "이미지 파일을 열 수 없습니다."
    
    # 이미지 데이터를 바이트 형태로 변환
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        buffered.seek(0)
        print("이미지 바이트 변환 성공")
    except Exception as e:
        print(f"이미지 바이트 변환 실패: {e}")
        return "이미지 데이터를 처리할 수 없습니다."
    
    # OpenAI API 요청
    try:
        # multipart/form-data 형식으로 파일을 전송
        files = {
            'file': ('image.jpg', buffered, 'image/jpeg')
        }
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": "이 이미지에 있는 제품을 설명해주세요. 제품의 종류, 색상, 특징 등을 간단히 설명해주세요."
                }
            ],
            "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=payload, files=files)
        print(f"API 응답 상태 코드: {response.status_code}")
        
        # 응답 상태 코드가 200일 경우만 성공 처리
        if response.status_code == 200:
            result = response.json()
            print("API 응답 성공:", result)
            return result['choices'][0]['message']['content']
        else:
            print(f"API 요청 실패, 상태 코드: {response.status_code}")
            print("API 응답 내용:", response.text)
            return "이미지 분석 요청에 실패했습니다."
    except Exception as e:
        print(f"API 요청 실패: {e}")
        return "이미지 분석 요청에 실패했습니다."


# LLM 모델 초기화
llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")

# 프롬프트 템플릿 설정
template = """
너는 네이버 쇼핑 도우미야. 사용자의 질문이나 이미지에 대해 제공된 상품 정보를 바탕으로 답변해줘. 
상품 정보에 없는 내용은 추측하지 말고, 정보가 부족하다고 말해줘.
필요하다면 상품 링크를 제공해 주고, 여러 상품을 비교해서 설명해줘.

상품 정보:
{product_info}

대화 기록:
{history}

사용자: {human_input}
AI 도우미:
"""

prompt = ChatPromptTemplate.from_template(template)

# 메모리 설정
memory = ConversationBufferMemory(memory_key="history", input_key="human_input")

# RunnableSequence 설정
def get_product_info(input_dict):
    query = input_dict["human_input"]
    if query.startswith("(이미지:"):
        image_path = query[8:-1].strip()  # "(이미지: path)" 형식에서 경로 추출
        image_description = analyze_image(image_path)
        items = get_naver_shopping_data(image_description)
    else:
        items = get_naver_shopping_data(query)
    return format_product_info(items)

chain = (
    RunnablePassthrough.assign(
        product_info=RunnableLambda(get_product_info),
        history=RunnableLambda(lambda x: memory.load_memory_variables({})["history"])
    )
    | prompt
    | llm
    | StrOutputParser()
)

# 챗봇 함수
def chatbot():
    print("챗봇: 안녕하세요! 네이버 쇼핑 관련 질문에 답변해 드리겠습니다. 이미지로 검색하려면 '(이미지: 파일경로)'와 같이 입력해주세요. 종료하려면 '종료'를 입력하세요.")
    while True:
        user_input = input("사용자: ")
        if user_input.lower() == '종료':
            print("챗봇: 감사합니다. 좋은 하루 되세요!")
            break
        
        # LLM을 통한 응답 생성
        response = chain.invoke({"human_input": user_input})
        print("챗봇:", response)
        
        # 메모리 업데이트
        memory.save_context({"human_input": user_input}, {"output": response})

# 챗봇 실행
if __name__ == "__main__":
    chatbot()

