import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 환경 변수에서 SerpApi 및 Imgur API 키 로드
load_dotenv()
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')

# 지원되는 이미지 파일 형식 (Imgur에서 지원하는 파일 형식)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff'}

# 파일 확장자 확인 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Imgur에 이미지 업로드
def upload_image_to_imgur(image_path):
    url = "https://api.imgur.com/3/upload"
    headers = {
        "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
    }
    with open(image_path, 'rb') as image_file:
        files = {'image': image_file}
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json()['data']['link']  # 업로드된 이미지 URL 반환
    else:
        return None

# Google Lens API를 통해 이미지 검색
def search_with_google_lens(image_url):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_lens",  # Google Lens API 엔진
        "url": image_url,         # 검색할 이미지 URL
        "api_key": SERPAPI_KEY    # SerpApi API 키
    }

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()  # 전체 JSON 결과 반환
    else:
        return None

# 홈 페이지 라우트 추가
@app.route('/')
def home():
    return render_template('test.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "파일이 제공되지 않았습니다."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400

    # 파일 형식 확인
    if not allowed_file(file.filename):
        return jsonify({"error": "지원되지 않는 파일 형식입니다. PNG, JPG, JPEG, GIF, TIFF만 지원됩니다."}), 400

    # 이미지 업로드
    try:
        filename = secure_filename(file.filename)
        image_path = os.path.join("uploads", filename)
        file.save(image_path)

        # Imgur에 이미지 업로드 후 URL 가져오기
        image_url = upload_image_to_imgur(image_path)
        if not image_url:
            return jsonify({"error": "이미지 업로드에 실패했습니다."}), 500

        # Google Lens를 사용하여 이미지 검색
        search_result = search_with_google_lens(image_url)
        if not search_result:
            return jsonify({"error": "이미지에서 유사한 결과를 찾을 수 없습니다."}), 400

        # 'visual_matches'에서 'title'만 추출
        visual_matches = search_result.get('visual_matches', [])
        titles = [match.get('title') for match in visual_matches if 'title' in match]

        # 첫 번째 타이틀만 반환
        if titles:
            first_title = titles[0]
        else:
            first_title = "유사한 제품을 찾을 수 없습니다."

        return jsonify({"message": "이미지 분석 완료", "image_url": image_url, "first_title": first_title})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
