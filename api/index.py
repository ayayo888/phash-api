from flask import Flask, request, jsonify
from PIL import Image
import imagehash
import requests
from io import BytesIO

app = Flask(__name__)

# 根路径测试，方便你点开链接确认服务是不是活的
@app.route('/', methods=['GET'])
def home():
    return "Python pHash Service is Running! 🚀"

# 核心计算接口
@app.route('/api/phash', methods=['GET'])
def get_phash():
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        # 设置 User-Agent 伪装成浏览器，防止被某些图床拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 下载图片，超时时间设置为10秒
        response = requests.get(image_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
             return jsonify({"success": False, "error": f"Download failed, status: {response.status_code}"}), 400

        # 打开图片并计算
        image = Image.open(BytesIO(response.content))
        
        # hash_size=8 是标准设置
        phash_obj = imagehash.phash(image, hash_size=8)
        
        return jsonify({
            "success": True,
            "phash": str(phash_obj)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
