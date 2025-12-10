from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# 1. 辅助：强制提取图片中心区域 (Center Crop)
# 解决背景色干扰和自动剪裁不准的问题
def crop_center(img):
    try:
        h, w = img.shape[:2]
        # 取中间 50% 的区域
        # 即使包包有一部分在外面，中间的核心花纹/Logo一定在里面
        start_x = int(w * 0.25)
        start_y = int(h * 0.25)
        end_x = int(w * 0.75)
        end_y = int(h * 0.75)
        
        return img[start_y:end_y, start_x:end_x]
    except:
        return img

# 2. 算法A：aHash (均值哈希 - 结构指纹)
# 比 dHash 更抗干扰，适合这种角度微变的情况
def get_ahash_vector(img):
    try:
        # 转灰度
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 缩放至 8x8
        resized = cv2.resize(gray, (8, 8))
        
        # 计算平均像素值
        avg = resized.mean()
        
        vector = []
        # 大于平均值记1，小于记0
        for i in range(8):
            for j in range(8):
                if resized[i, j] > avg:
                    vector.append(1.0)
                else:
                    vector.append(0.0)
        return vector # 长度 64
    except:
        return [0.0] * 64

# 3. 算法B：HSV直方图 (颜色指纹 - 基于中心区域)
def get_color_vector(img):
    try:
        # 先切中心！只看包包，不看背景
        center_img = crop_center(img)
        
        # 缩放一下加快计算
        center_img = cv2.resize(center_img, (150, 150))
        
        hsv = cv2.cvtColor(center_img, cv2.COLOR_BGR2HSV)
        
        # H(12)*S(4)*V(4) = 192维
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        vector = hist.flatten().tolist()
        vector = [round(x, 4) for x in vector]
        return vector # 长度 192
    except:
        return [0.0] * 192

# --- 主流程 ---
@app.route('/', methods=['GET'])
def home():
    return "Center-Crop + aHash Service is Running! 🚀"

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

        # 计算特征 (注意：不用自动切边了，函数内部会强制切中心)
        vec_structure = get_ahash_vector(img) # 64维
        vec_color = get_color_vector(img)     # 192维
        
        final_vector = vec_structure + vec_color
        
        return jsonify({"success": True, "vector": final_vector})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
