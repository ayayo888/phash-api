from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

def download_and_decode(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 下载图片
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        
        # 将图片转换为 numpy 数组 (OpenCV 的格式)
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        # 解码图片
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return img
    except:
        return None

def calculate_opencv_similarity(img1, img2):
    try:
        # 1. 统一大小 (OpenCV 对比直方图不需要完全一样大，但为了统一处理缩放一下)
        # 缩小一点能显著提高速度，防止超时
        img1 = cv2.resize(img1, (300, 300))
        img2 = cv2.resize(img2, (300, 300))

        # 2. 转换颜色空间 BGR -> HSV
        # HSV 包含了 色调(H)、饱和度(S)、亮度(V)，比 RGB 更能抗光照干扰
        hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
        hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

        # 3. 计算直方图
        # H通道分50级，S通道分60级。忽略亮度V通道(抗光照影响)
        hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
        hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])

        # 4. 归一化 (让数据在同一量级)
        cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

        # 5. 对比直方图 (使用 CORREL 相关性方法)
        # 结果：1.0 表示完全匹配，0 表示完全不相关
        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        return score
    except Exception as e:
        print(f"Error: {e}")
        return 0

@app.route('/', methods=['GET'])
def home():
    # 检查 OpenCV 是否安装成功
    return f"OpenCV Version: {cv2.__version__} is Running! 🚀"

@app.route('/api/compare', methods=['GET'])
def compare_images():
    url1 = request.args.get('url1')
    url2 = request.args.get('url2')
    
    if not url1 or not url2:
        return jsonify({"error": "Missing url1 or url2"}), 400

    try:
        # 下载两张图
        img1 = download_and_decode(url1)
        img2 = download_and_decode(url2)

        if img1 is None or img2 is None:
             return jsonify({"success": False, "error": "Failed to download images"}), 400

        # 计算相似度
        similarity_score = calculate_opencv_similarity(img1, img2)
        
        # 转换为百分比整数
        percentage = round(similarity_score * 100, 2)

        return jsonify({
            "success": True,
            "similarity": similarity_score, # 0.0 - 1.0
            "percentage": percentage,       # 0 - 100
            "is_match": percentage > 85     # 推荐判定阈值
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
