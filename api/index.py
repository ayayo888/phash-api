from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# 1. 下载并解码
def download_and_decode(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return img
    except:
        return None

# 2. 核心算法升级：三维全彩特征提取
def get_image_vector(img):
    try:
        # A. 统一缩放
        img = cv2.resize(img, (300, 300))
        
        # B. 转为 HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # C. 计算 3D 直方图 (Hue, Saturation, Value)
        # H(色调)分16级: 区分红橙黄绿青蓝紫
        # S(饱和度)分8级: 区分鲜艳程度
        # V(亮度)分8级: ⚠️关键！区分黑、白、灰、暗色
        # 总特征数: 16 * 8 * 8 = 1024 维
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [16, 8, 8], [0, 180, 0, 256, 0, 256])
        
        # D. 归一化 (防止大图数值大，小图数值小)
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        # E. 展平并保留4位小数
        vector = hist.flatten().tolist()
        vector = [round(x, 4) for x in vector]
        
        return vector
    except:
        return None

@app.route('/', methods=['GET'])
def home():
    return "OpenCV 3D-Color Service is Running! 🚀"

@app.route('/api/vector', methods=['GET'])
def get_vector():
    url = request.args.get('url')
    if not url: return jsonify({"error": "Missing url"}), 400

    try:
        img = download_and_decode(url)
        if img is None:
             return jsonify({"success": False, "error": "Download failed"}), 400

        vector = get_image_vector(img)
        
        if vector:
            return jsonify({"success": True, "vector": vector})
        else:
            return jsonify({"success": False, "error": "CV processing failed"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
