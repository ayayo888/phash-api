from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO

app = Flask(__name__)

# --- 自定义 dHash 算法 (无需依赖重型库) ---
def calculate_dhash(image, hash_size=8):
    # 1. 转为灰度图
    image = image.convert("L")
    # 2. 调整大小 (宽度比高度多1像素，用于对比)
    # 使用 LANCZOS 滤镜进行高质量缩放
    image = image.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    
    pixels = list(image.getdata())
    
    # 3. 对比像素 (如果左边比右边亮，记为1，否则为0)
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            # 获取当前像素和右边一个像素的索引
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    
    # 4. 转为 16 进制字符串
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
    return "Python Lightweight Service is Running! 🚀"

@app.route('/api/phash', methods=['GET'])
def get_phash():
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({"error": "Missing url parameter"}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 下载图片
        response = requests.get(image_url, headers=headers, timeout=10)
        if response.status_code != 200:
             return jsonify({"success": False, "error": f"Download status: {response.status_code}"}), 400

        # 打开图片
        image = Image.open(BytesIO(response.content))
        
        # 调用我们手写的函数
        dhash_str = calculate_dhash(image)
        
        return jsonify({
            "success": True,
            "phash": dhash_str
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
