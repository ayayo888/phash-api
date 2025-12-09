from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# 1. 下载并解码图片
def download_and_decode(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 设置 10秒超时，防止卡死
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        
        # 转换为 OpenCV 格式
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return img
    except:
        return None

# 2. 核心算法：提取图片特征向量 (DNA)
def get_image_vector(img):
    try:
        # A. 统一缩放 (300x300 是速度和精度的平衡点)
        img = cv2.resize(img, (300, 300))
        
        # B. 转为 HSV 颜色空间 (抗光照干扰)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # C. 计算颜色直方图
        # H(色调)分30份，S(饱和度)分32份 -> 共 30*32 = 960 个特征点
        # 这个精度足够区分同款，又不会让数据量太大塞爆表格
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        
        # D. 归一化 (0到1之间)
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        # E. 展平数组并保留4位小数 (减少 JSON 体积)
        vector = hist.flatten().tolist()
        vector = [round(x, 4) for x in vector]
        
        return vector
    except:
        return None

@app.route('/', methods=['GET'])
def home():
    return "OpenCV Vector Service is Running! 🚀"

# --- 你的表格脚本调用的就是这个接口 ---
@app.route('/api/vector', methods=['GET'])
def get_vector():
    url = request.args.get('url')
    
    if not url:
        return jsonify({"error": "Missing url"}), 400

    try:
        # 下载
        img = download_and_decode(url)
        if img is None:
             return jsonify({"success": False, "error": "Download failed"}), 400

        # 计算
        vector = get_image_vector(img)
        
        if vector:
            # 成功返回数组
            return jsonify({
                "success": True, 
                "vector": vector 
            })
        else:
            return jsonify({"success": False, "error": "CV processing failed"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
