from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# --- 1. 辅助：自动切除白边 (纯 OpenCV 版) ---
def trim_white_border(img):
    try:
        # 转灰度
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 二值化：把接近白色的背景(>240)变成黑色(0)，内容变成白色(255)
        # THRESH_BINARY_INV: 反转，背景变黑，内容变白，方便找轮廓
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # 寻找所有非零像素(内容)的坐标
        coords = cv2.findNonZero(thresh)
        
        # 如果全是白的(没内容)，直接返回原图
        if coords is None:
            return img
            
        # 获取最小外接矩形
        x, y, w, h = cv2.boundingRect(coords)
        
        # 裁剪
        crop = img[y:y+h, x:x+w]
        return crop
    except:
        return img

# --- 2. 算法A：dHash (结构指纹 - 纯 OpenCV 版) ---
def get_dhash_vector(img):
    try:
        # 转灰度
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 缩放至 9x8
        resized = cv2.resize(gray, (9, 8))
        
        vector = []
        # 逐像素比较：左边 > 右边 ? 1 : 0
        for i in range(8):
            for j in range(8):
                # OpenCV 像素访问: [row, col]
                if resized[i, j] > resized[i, j + 1]:
                    vector.append(1.0)
                else:
                    vector.append(0.0)
        return vector # 长度 64
    except:
        return [0.0] * 64

# --- 3. 算法B：HSV直方图 (颜色指纹) ---
def get_color_vector(img):
    try:
        img = cv2.resize(img, (300, 300))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # H(12)*S(4)*V(4) = 192维
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        vector = hist.flatten().tolist()
        vector = [round(x, 4) for x in vector]
        return vector # 长度 192
    except:
        return [0.0] * 192

# --- 主入口 ---
@app.route('/', methods=['GET'])
def home():
    return "Pure OpenCV Hybrid Service is Running! 🚀"

@app.route('/api/vector', methods=['GET'])
def get_vector():
    url = request.args.get('url')
    if not url: return jsonify({"error": "Missing url"}), 400

    try:
        # 下载
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200: return jsonify({"success": False, "error": "DL Fail"}), 400
        
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is None: return jsonify({"success": False, "error": "Decode Fail"}), 400

        # 1. 切白边 (关键修正：解决Prada和Loewe形状误判)
        crop_img = trim_white_border(img)
        
        # 2. 计算混合特征
        vec_structure = get_dhash_vector(crop_img)
        vec_color = get_color_vector(crop_img)
        
        final_vector = vec_structure + vec_color
        
        return jsonify({"success": True, "vector": final_vector})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
