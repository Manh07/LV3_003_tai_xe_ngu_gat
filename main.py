import cv2
from ultralytics import YOLO
import time
import threading
import tkinter as tk
from tkinter import ttk
import logging

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
BUZZER_PIN = 17  # GPIO17 (Physical pin 11) - Thay doi theo hardware cua ban
BUZZER_DURATION = 2  # Bat coi 2 giay

if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)  # Dung BCM numbering
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.LOW)  # Tat coi ban dau
    print(f"[OK] GPIO initialized - Buzzer on GPIO{BUZZER_PIN}")

# Load model YOLO
# Thay doi duong dan model neu can
model = YOLO("best.pt")  # Model da train voi 5 classes
print("[OK] Model loaded: best.pt")

# Ánh xạ class ID sang tên nhãn (CHỈ HOẠT ĐỘNG KHI DÙNG MODEL ĐÃ TRAIN)
class_names = {
    0: "awake",
    1: "drowsy",
    2: "texting_phone",
    3: "turning",
    4: "talking_phone",
}

# Cấu hình cảnh báo
alert_cooldowns = {"drowsy": 15, "texting_phone": 10, "talking_phone": 8, "turning": 5}

# Thời gian yêu cầu hành vi kéo dài để phát cảnh báo
DETECTION_DURATION_THRESHOLD = 3

# Từ điển lưu thời gian và số lần phát hiện
detection_start_times = {class_name: None for class_name in alert_cooldowns.keys()}
last_alert_times = {class_name: 0 for class_name in alert_cooldowns.keys()}
detection_counts = {class_name: 0 for class_name in alert_cooldowns.keys()}


# ======================== HAM DIEU KHIEN COI (GPIO) ========================
def trigger_buzzer(class_name):
    """Bat coi canh bao qua GPIO"""
    print(f"[ALERT] Phat hien {class_name}!")

    if GPIO_AVAILABLE:
        try:
            # Bat coi
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            print(f"[BUZZER ON] GPIO{BUZZER_PIN}")

            # Giu coi bat trong BUZZER_DURATION giay
            time.sleep(BUZZER_DURATION)

            # Tat coi
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            print(f"[BUZZER OFF]")
        except Exception as e:
            print(f"[ERROR GPIO] {e}")
    else:
        print("[WARNING] GPIO khong kha dung - Chi hien thi canh bao")


# Da bo: speak_alert(), record_video(), Telegram, Weather API

# Thoi gian bat dau lai xe
start_time = time.time()

# Khoi tao GUI bang tkinter
root = tk.Tk()
root.title("Driver Monitoring System")
root.geometry("400x300")
root.resizable(False, False)

# Cac nhan hien thi trang thai
status_label = ttk.Label(root, text="Trang thai: Dang chay", font=("Arial", 12))
status_label.pack(pady=10)

behavior_label = ttk.Label(root, text="Hanh vi: Chua phat hien", font=("Arial", 10))
behavior_label.pack(pady=5)

time_label = ttk.Label(root, text="Thoi gian: Dang cap nhat", font=("Arial", 10))
time_label.pack(pady=5)

driving_time_label = ttk.Label(root, text="Thoi gian lai: 0 phut", font=("Arial", 10))
driving_time_label.pack(pady=5)


# Ham cap nhat GUI voi mau sac (da bo weather)
def update_gui(behavior, current_time_str, driving_time):
    behavior_label.config(text=f"Hanh vi: {behavior}")
    if behavior == "awake":
        behavior_label.config(foreground="green")  # Xanh la cho trang thai tinh tao
    elif behavior in alert_cooldowns:  # Cac hanh vi nguy hiem
        behavior_label.config(foreground="red")  # Do cho hanh vi nguy hiem
    else:
        behavior_label.config(foreground="black")  # Den cho "Chua phat hien"

    time_label.config(text=f"Thoi gian: {current_time_str}")
    driving_time_label.config(text=f"Thoi gian lai: {driving_time:.0f} phut")
    root.update()


# Mo webcam
cap = cv2.VideoCapture(0)

# Bien dieu khien vong lap
running = True


def process_camera():
    """Xu ly camera trong thread rieng"""
    global running

    while cap.isOpened() and running:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Khong the lay du lieu tu webcam!")
            running = False
            break

        # Du doan bang YOLO voi verbose=False de tat thong bao
        results = model(frame, conf=0.65, verbose=False)
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
        detected_behavior = "Chua phat hien"  # Gia tri mac dinh

        if detected_classes:  # Neu co hanh vi duoc phat hien
            detected_behavior = list(detected_classes)[0]

        # Xu ly canh bao va ghi video cho cac hanh vi nguy hiem
        for class_name in alert_cooldowns:
            if class_name in detected_classes:
                if detection_start_times[class_name] is None:
                    detection_start_times[class_name] = current_time
                else:
                    elapsed_time = current_time - detection_start_times[class_name]
                    if elapsed_time >= DETECTION_DURATION_THRESHOLD:
                        cooldown = alert_cooldowns[class_name]
                        last_time = last_alert_times[class_name]

                        if current_time - last_time > cooldown:
                            detection_counts[class_name] += 1
                            # Kich hoat coi canh bao
                            trigger_buzzer(class_name)
                            last_alert_times[class_name] = current_time
                            detection_start_times[class_name] = None
            else:
                detection_start_times[class_name] = None

        # Hien thi thong tin tren khung hinh OpenCV
        current_time_str = time.strftime("%H:%M:%S %d/%m/%Y")
        cv2.putText(
            annotated_frame,
            current_time_str,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            annotated_frame,
            f"Hanh vi: {detected_behavior}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        # Lap lich cap nhat GUI tu thread chinh
        root.after(
            0, lambda: update_gui(detected_behavior, current_time_str, driving_time)
        )

        # Hien thi frame OpenCV
        cv2.imshow("Driver Monitoring", annotated_frame)

        # Nhan 'q' de thoat
        if cv2.waitKey(1) & 0xFF == ord("q"):
            running = False
            break


# Ham don dep khi thoat
def on_closing():
    global running
    running = False
    cap.release()
    cv2.destroyAllWindows()
    root.quit()
    root.destroy()


# Xu ly su kien dong cua so
root.protocol("WM_DELETE_WINDOW", on_closing)

# Khoi tao va chay camera thread
camera_thread = threading.Thread(target=process_camera, daemon=True)
camera_thread.start()

# Chay GUI tren main thread
try:
    root.mainloop()
except KeyboardInterrupt:
    print("\n[WARNING] Thoat chuong trinh...")
finally:
    on_closing()

# Cleanup GPIO
if GPIO_AVAILABLE:
    GPIO.cleanup()
    print("[OK] GPIO cleanup completed")

print("[OK] Chuong trinh ket thuc")
