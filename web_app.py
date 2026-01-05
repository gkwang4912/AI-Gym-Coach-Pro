
import os
print("Starting web_app.py...")
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sys, cv2, time, base64, io
import numpy as np
import mediapipe as mp
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from PIL import Image, ImageDraw, ImageFont

# ---------- 初始化 Flask & SocketIO ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ---------- 字型準備 ----------
FONT_CANDIDATES = ["msjh.ttc","msjhbd.ttc","NotoSansCJK-Regular.ttc"]
COMMON_FONT_DIRS = [r"C:\Windows\Fonts","/usr/share/fonts","/usr/local/share/fonts","/Library/Fonts"]
def find_font():
    for d in COMMON_FONT_DIRS:
        for f in FONT_CANDIDATES:
            path = os.path.join(d,f)
            if os.path.isfile(path): return path
    return None
_FONT_PATH = find_font()

def cv2_add_chinese_text(img,text,pos,color=(255,255,255),size=30):
    img_pil = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try: font = ImageFont.truetype(_FONT_PATH,size) if _FONT_PATH else ImageFont.load_default()
    except: font = ImageFont.load_default()
    b,g,r = color
    draw.text(pos,text,font=font,fill=(r,g,b))
    return cv2.cvtColor(np.array(img_pil),cv2.COLOR_RGB2BGR)

# ---------- MediaPipe 準備 ----------
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose_model = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# ---------- 全域狀態 ----------
hands = {
    "Left":{"count":0,"top":False,"py":None,"pt":time.time()},
    "Right":{"count":0,"top":False,"py":None,"pt":time.time()}
}
ARM_UP_ANGLE = 140
ARM_DOWN_ANGLE = 130
SPEED_LIMIT = 1.8

def calculate_angle(a,b,c):
    a,b,c = np.array(a),np.array(b),np.array(c)
    ba = a-b; bc = c-b
    cos = np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc)+1e-8)
    cos = np.clip(cos,-1.0,1.0)
    return np.degrees(np.arccos(cos))

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('process_frame')
def handle_frame(data):
    global hands
    
    # 1. 解碼圖片
    image_data = data['image'].split(',')[1] # 去掉 data:image/jpeg;base64,
    img_bytes = base64.b64decode(image_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None: return

    # 2. MediaPipe 處理
    # 注意: 前端已經做過鏡像翻轉，這裡收到的就是鏡像後的，所以不需要再 flip，除非邏輯需要
    # 這裡假設前端顯示正確，後端只負責畫圖和算數據
    image = frame # 已經是 RGB 格式了嗎？ cv2.imdecode 讀出來是 BGR
    # MP 需要 RGB
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    results = pose_model.process(rgb)
    image.flags.writeable = True

    h,w,_ = image.shape
    debug_image = image.copy()
    
    stats_output = {}

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        mp_drawing.draw_landmarks(debug_image,results.pose_landmarks,mp_pose.POSE_CONNECTIONS,
                                  mp_drawing.DrawingSpec(color=(200,200,200),thickness=2),
                                  mp_drawing.DrawingSpec(color=(0,255,0),thickness=2))
        
        nose_y = int(lm[mp_pose.PoseLandmark.NOSE].y*h)
        cv2.line(debug_image,(0,nose_y),(w,nose_y),(255,255,0),2)
        # debug_image = cv2_add_chinese_text(debug_image,"目標高度線（鼻子）",(w-400,max(0,nose_y-40)),(255,255,0),30)

        for side,ids in {
            "Left": (mp_pose.PoseLandmark.RIGHT_SHOULDER,mp_pose.PoseLandmark.RIGHT_ELBOW,mp_pose.PoseLandmark.RIGHT_WRIST),
            "Right":(mp_pose.PoseLandmark.LEFT_SHOULDER,mp_pose.PoseLandmark.LEFT_ELBOW,mp_pose.PoseLandmark.LEFT_WRIST)
        }.items():
            sh,el,wr = [lm[i] for i in ids]
            state = hands[side]
            angle = calculate_angle([sh.x,sh.y],[el.x,el.y],[wr.x,wr.y])
            now = time.time()
            speed = 0
            if state["py"] is not None:
                dt = now - state["pt"]
                if dt>0: speed = abs(wr.y - state["py"])/dt
            state["py"]=wr.y
            state["pt"]=now
            high = wr.y < lm[mp_pose.PoseLandmark.NOSE].y
            if angle>ARM_UP_ANGLE and high: state["top"]=True
            if state["top"] and angle<ARM_DOWN_ANGLE: state["count"]+=1; state["top"]=False

            # y=100 if side=="Left" else 300
            # debug_image = cv2_add_chinese_text(debug_image,f"{side} 次數: {state['count']}",(20,y),(255,255,255),36)
            # debug_image = cv2_add_chinese_text(debug_image,f"角度: {int(angle)}°",(20,y+40),(255,255,255),24)
            # 狀態文字提示
            msg = "請放下" if state['top'] else "請舉起"
            # color_msg = (255,255,0)
            if speed > SPEED_LIMIT: msg += " (太快!)"; # color_msg = (255,0,0)
            elif not high: msg += " (太低!)"; # color_msg = (0,0,255)
            
            # debug_image = cv2_add_chinese_text(debug_image, msg, (20,y+70), color_msg, 24)

            stats_output[side] = {
                "count": state["count"],
                "angle": int(angle),
                "speed": f"{speed:.2f}",
                "feedback": msg,
                "is_active": True # 可以用來處裡 UI 顯示
            }

    # 3. 回傳
    # 壓縮圖片回傳
    _, buffer = cv2.imencode('.jpg', debug_image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    img_str = base64.b64encode(buffer).decode('utf-8')
    response_data = "data:image/jpeg;base64," + img_str
    
    emit('response', {'image': response_data, 'stats': stats_output})

if __name__ == '__main__':
    print("啟動 Web AI Gym Coach on port 5001...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
