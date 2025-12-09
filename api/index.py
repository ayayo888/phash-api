from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO

app = Flask(__name__)

# --- 核心算法：dHash (无需外部数学库) ---
def calculate_dhash(image, hash_size=8):
    # 1. 转灰度
    image = image.convert("L")
    # 2. 缩放 (宽9高8)
    image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(image.getdata())
    
    # 3. 比较像素生成哈希
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    
    # 4. 转 16 进制
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2**(index % 8)
        if (index % 8) == 7:
            hex_string.append(f"{decimal_value:02x}")
            decimal_value = 0
            
    return "".join(hex_string)

@app.route('/', methods=['GET'])
def home():
    return "Python Service is Running! (Fixed libjpeg issue) 🚀"

@app.route('/api/phash', methods=['GET'])
def get_phash():
    image_url = request.args.get('url')
    if not image_url:
        return jsonify({"error": "Missing url"}), 400

    try:
        # 伪装浏览器头
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(image_url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
             return jsonify({"success": False, "error": f"Download error: {resp.status_code}"}), 400

        image = Image.open(BytesIO(resp.content))
        dhash_str = calculate_dhash(image)
        
        return jsonify({"success": True, "phash": dhash_str})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
