from flask import Flask, request, jsonify
import cv2
import numpy as np
import requests
from PIL import Image, ImageChops # 引入 PIL 做自动剪裁，比 OpenCV 方便
from io import BytesIO

app = Flask(__name__)

# --- 1. 辅助：自动切除白边 (Auto-Crop) ---
# 这步至关重要，防止因为图片留白大小不同导致形状识别错误
def trim_white_border(cv_img):
    try:
        # OpenCV 转 PIL
        img_pil = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
        bg = Image.new(img_pil.mode, img_pil.size, img_pil.getpixel((0, 0)))
        diff = ImageChops.difference(img_pil, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            img_pil = img_pil.crop(bbox)
            # PIL 转回 OpenCV
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return cv_img
    except:
        return cv_img

# --- 2. 算法A：dHash (结构指纹) ---
# 负责识别：形状、轮廓、有没有盒子、Logo是圆的还是方的
def get_dhash_vector(img):
    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 缩放至 9x8
    resized = cv2.resize(gray, (9, 8))
    
    vector = []
    # 逐像素比较：如果左边比右边亮，记为1，否则0
    for i in range(8):
        for j in range(8):
            if resized[i, j] > resized[i, j + 1]:
                vector.append(1.0) # 用浮点数方便后续计算
            else:
                vector.append(0.0)
    return vector # 长度 64

# --- 3. 算法B：HSV直方图 (颜色指纹) ---
# 负责识别：黑色、白色、金色、红色
def get_color_vector(img):
    img = cv2.resize(img, (300, 300))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 降低一点维度，H(12)*S(4)*V(4) = 192维
    # 权重设计：让颜色信息的长度比结构信息长一点，保持平衡
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    
    vector = hist.flatten().tolist()
    vector = [round(x, 4) for x in vector]
    return vector # 长度 192

# --- 4. 主流程 ---
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
        original_img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # 关键步骤：先切除白边！
        # 这样 Loewe 的盒子和 Prada 的皮带都会撑满画面，方便比对形状
        crop_img = trim_white_border(original_img)
        
        # 计算双重 DNA
        vec_structure = get_dhash_vector(crop_img) # 64维
        vec_color = get_color_vector(crop_img)     # 192维
        
        # 拼接在一起：[结构... , 颜色...]
        # 现在的总向量长度 = 256
        final_vector = vec_structure + vec_color
        
        return jsonify({"success": True, "vector": final_vector})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
