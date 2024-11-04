from flask import Blueprint, jsonify, request, Response
from werkzeug.utils import secure_filename
from app.utils.helpers import allowed_file
from app.services.imgur_service import upload_image_to_imgur
from app.services.google_lens_service import search_with_google_lens
from app.services.naver_shopping_service import get_naver_shopping_data, format_product_info
from app.llm_config import llm, memory, prompt
import json
import os

image_bp = Blueprint('image', __name__)

@image_bp.route('/upload', methods=['POST'])
def upload_image():
    print("이미지 업로드 요청을 수신했습니다.")  # 진행 상황 확인

    # 'uploads' 디렉터리가 없다면 생성
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"'{upload_folder}' 디렉터리가 생성되었습니다.")  # 디렉터리 생성 확인 로그

    if 'file' not in request.files:
        print("오류: 파일이 제공되지 않았습니다.")  # 오류 로그
        return jsonify({"error": "파일이 제공되지 않았습니다."}), 400

    file = request.files['file']
    if file.filename == '':
        print("오류: 파일이 선택되지 않았습니다.")  # 오류 로그
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

    if not allowed_file(file.filename):
        print(f"오류: 지원되지 않는 파일 형식입니다 - {file.filename}")  # 파일 형식 오류 로그
        return jsonify({"error": "지원되지 않는 파일 형식입니다."}), 400

    try:
        filename = secure_filename(file.filename)
        image_path = os.path.join(upload_folder, filename)
        file.save(image_path)
        print(f"파일이 저장되었습니다: {image_path}")  # 파일 저장 완료 로그

        # Imgur 업로드
        image_url = upload_image_to_imgur(image_path)
        if not image_url:
            print("오류: 이미지 업로드에 실패했습니다.")  # Imgur 업로드 실패 로그
            return jsonify({"error": "이미지 업로드에 실패했습니다."}), 500

        print(f"이미지가 Imgur에 업로드되었습니다: {image_url}")  # 이미지 URL 로그

        # Google Lens API 호출 및 결과 확인
        print("Google Lens API 호출 중...")  # API 호출 로그
        search_result = search_with_google_lens(image_url)
        
        # API 응답 데이터 출력
        print("Google Lens 검색 결과:", search_result)  # 응답 데이터 전체 출력
        if not search_result:
            print("오류: 이미지에서 유사한 결과를 찾을 수 없습니다.")  # Google Lens 실패 로그
            return jsonify({"error": "이미지에서 유사한 결과를 찾을 수 없습니다."}), 400

        # 시각적 일치 항목 확인
        visual_matches = search_result.get('visual_matches', [])
        titles = [match.get('title') for match in visual_matches if 'title' in match]

        print(f"Google Lens에서 시각적 일치 항목이 발견되었습니다: {titles}")  # Google Lens 결과 로그

        if titles:
            first_title = titles[0]
            print(f"첫 번째 타이틀을 사용하여 검색: {first_title}")  # 네이버 검색 키워드 로그
            items = get_naver_shopping_data(first_title)
            product_info = format_product_info(items)

            # 메모리와 프롬프트 구성
            history = memory.load_memory_variables({})["history"]
            messages = prompt.format_messages(
                product_info=product_info,
                history=history,
                human_input=first_title
            )

            def generate():
                full_response = ""
                for chunk in llm.stream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        yield f"data: {json.dumps({'response': full_response})}\n\n"
                memory.save_context({"human_input": first_title}, {"output": full_response})
                print("LLM 응답이 생성되었습니다.")  # LLM 응답 생성 완료 로그

            return Response(generate(), content_type='text/event-stream')

        print("오류: 이미지에서 적절한 타이틀을 찾을 수 없습니다.")  # 타이틀 찾기 실패 로그
        return jsonify({"message": "이미지에서 적절한 타이틀을 찾을 수 없습니다."})

    except Exception as e:
        print(f"예외 발생: {str(e)}")  # 예외 발생 로그
        return jsonify({"error": str(e)}), 500
