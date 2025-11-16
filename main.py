import cv2
from ultralytics import YOLO
import time
import threading
import logging
from flask import Flask, render_template, Response, jsonify
import base64

# GPIO cho Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("[WARNING] RPi.GPIO khong kha dung (chay tren PC?)")
    GPIO_AVAILABLE = False

# Tat logging cua ultralytics
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# ======================== CAU HINH GPIO ========================
BUZZER_PIN = 17  # GPIO17 (Physical pin 11)

if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    print(f"[OK] GPIO initialized - Buzzer on GPIO{BUZZER_PIN}")

# Bien theo doi trang thai buzzer
buzzer_active = False

# Load model YOLO
model = YOLO("best_3.pt")
print("[OK] Model loaded: best_3.pt")

# Anh xa class ID sang ten nhan
class_names = {
    0: "awake",
    1: "drowsy",
    2: "use_phone"
}

# Cau hinh canh bao
alert_cooldowns = {"drowsy": 10, "use_phone": 10}

# Thoi gian yeu cau hanh vi keo dai de phat canh bao
DETECTION_DURATION_THRESHOLD = 3

# Tu dien luu thoi gian va so lan phat hien
detection_start_times = {class_name: None for class_name in alert_cooldowns.keys()}
last_alert_times = {class_name: 0 for class_name in alert_cooldowns.keys()}
detection_counts = {class_name: 0 for class_name in alert_cooldowns.keys()}

# Thoi gian bat dau lai xe
start_time = time.time()

# Bien toan cuc luu trang thai
current_behavior = "Chua phat hien"
current_status = {
    "behavior": "Chua phat hien",
    "time": "",
    "driving_time": 0,
    "buzzer_active": False,
    "fps": 0
}

# ======================== HAM DIEU KHIEN COI (GPIO) ========================
def set_buzzer(state):
    """Bat/Tat coi canh bao qua GPIO"""
    global buzzer_active
    
    if GPIO_AVAILABLE:
        try:
            if state and not buzzer_active:
                GPIO.output(BUZZER_PIN, GPIO.HIGH)
                buzzer_active = True
                print(f"[BUZZER ON] GPIO{BUZZER_PIN}")
            elif not state and buzzer_active:
                GPIO.output(BUZZER_PIN, GPIO.LOW)
                buzzer_active = False
                print(f"[BUZZER OFF]")
        except Exception as e:
            print(f"[ERROR GPIO] {e}")
    else:
        if state and not buzzer_active:
            buzzer_active = True
        elif not state and buzzer_active:
            buzzer_active = False

# ======================== FLASK APP ========================
app = Flask(__name__)

# Mo webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Giam buffer de giam delay

# Bien dieu khien
running = True
frame_lock = threading.Lock()
latest_frame = None
latest_frame_time = 0

def process_camera():
    """Xu ly camera trong thread rieng"""
    global running, latest_frame, current_status, latest_frame_time
    
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = 0
    frame_time_sum = 0

    while running:
        frame_start = time.time()
        
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Khong the lay du lieu tu webcam!")
            time.sleep(0.1)
            continue

        # Du doan bang YOLO - Giam image size de tang FPS
        results = model(frame, conf=0.65, verbose=False, imgsz=320)
        annotated_frame = results[0].plot()

        current_time = time.time()
        detected_classes = set()

        # Tinh thoi gian lai xe (phut)
        driving_time = (current_time - start_time) / 60

        # Lay thong tin class phat hien duoc
        for box in results[0].boxes:
            class_id = int(box.cls)
            class_name = class_names.get(class_id, "unknown")
            detected_classes.add(class_name)

        # Xu ly hanh vi va phat canh bao
        detected_behavior = "Chua phat hien"

        if detected_classes:
            detected_behavior = list(detected_classes)[0]

        # Kiem tra co hanh vi nguy hiem nao dang xay ra khong
        danger_detected = False
        
        # Xu ly canh bao cho cac hanh vi nguy hiem
        for class_name in alert_cooldowns:
            if class_name in detected_classes:
                danger_detected = True
                if detection_start_times[class_name] is None:
                    detection_start_times[class_name] = current_time
                else:
                    elapsed_time = current_time - detection_start_times[class_name]
                    if elapsed_time >= DETECTION_DURATION_THRESHOLD:
                        set_buzzer(True)
                        detection_counts[class_name] += 1
                        last_alert_times[class_name] = current_time
            else:
                detection_start_times[class_name] = None
        
        # Tat coi khi khong con hanh vi nguy hiem
        if not danger_detected:
            set_buzzer(False)

        # Tinh FPS thuc te
        frame_time = time.time() - frame_start
        frame_time_sum += frame_time
        fps_counter += 1
        
        elapsed_fps_time = current_time - fps_start_time
        if elapsed_fps_time >= 1.0:
            current_fps = int(fps_counter / elapsed_fps_time)
            avg_frame_time = frame_time_sum / fps_counter if fps_counter > 0 else 0
            fps_counter = 0
            frame_time_sum = 0
            fps_start_time = current_time
            print(f"[FPS] {current_fps} fps (avg frame time: {avg_frame_time*1000:.1f}ms)")

        # Hien thi thong tin tren khung hinh
        current_time_str = time.strftime("%H:%M:%S %d/%m/%Y")
        
        # Them thong tin status
        cv2.putText(annotated_frame, current_time_str, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"Hanh vi: {detected_behavior}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"FPS: {current_fps}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        if buzzer_active:
            cv2.putText(annotated_frame, "CANH BAO!", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)

        # Cap nhat trang thai hien tai
        current_status = {
            "behavior": detected_behavior,
            "time": current_time_str,
            "driving_time": round(driving_time, 1),
            "buzzer_active": buzzer_active,
            "fps": current_fps
        }

        # Luu frame moi nhat (chi luu neu co su thay doi)
        with frame_lock:
            latest_frame = annotated_frame
            latest_frame_time = current_time

def generate_frames():
    """Generator de stream video"""
    last_yield_time = 0
    min_interval = 0.033  # ~30 fps max
    
    while running:
        current_time = time.time()
        
        # Throttle frame rate de tranh overload
        if current_time - last_yield_time < min_interval:
            time.sleep(0.01)
            continue
            
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.01)
                continue
            frame = latest_frame
        
        # Encode frame thanh JPEG voi quality thap hon de giam size
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        last_yield_time = current_time
        
        # Yield frame theo dinh dang multipart
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Trang chu"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """API tra ve trang thai hien tai"""
    return jsonify(current_status)

def cleanup():
    """Don dep khi thoat"""
    global running
    running = False
    cap.release()
    if GPIO_AVAILABLE:
        GPIO.cleanup()
    print("[OK] Cleanup completed")

if __name__ == '__main__':
    try:
        # Bat dau camera thread
        camera_thread = threading.Thread(target=process_camera, daemon=True)
        camera_thread.start()
        
        print("[OK] Starting web server on http://0.0.0.0:5000")
        print("[INFO] Truy cap tu may khac: http://<IP_cua_Pi>:5000")
        
        # Chay Flask server
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[WARNING] Thoat chuong trinh...")
    finally:
        cleanup()
