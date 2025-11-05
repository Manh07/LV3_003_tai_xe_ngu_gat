import cv2
from ultralytics import YOLO
import time
import threading
import tkinter as tk
from tkinter import ttk
import logging

# GPIO cho Raspberry Pi - COMMENT CHO UBUNTU/PC
# try:
#     import RPi.GPIO as GPIO
#     GPIO_AVAILABLE = True
# except ImportError:
#     print("⚠️ RPi.GPIO không khả dụng (chạy trên PC?)")
#     GPIO_AVAILABLE = False

GPIO_AVAILABLE = False
print("🖥️ Chế độ TEST trên Ubuntu/PC - GPIO đã tắt")

# Tắt logging của ultralytics
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# ======================== CẤU HÌNH GPIO ========================
BUZZER_PIN = 17  # GPIO17 (Physical pin 11) - Thay đổi theo hardware của bạn
BUZZER_DURATION = 2  # Bật còi 2 giây

# COMMENT PHẦN GPIO SETUP CHO UBUNTU/PC
# if GPIO_AVAILABLE:
#     GPIO.setmode(GPIO.BCM)  # Dùng BCM numbering
#     GPIO.setup(BUZZER_PIN, GPIO.OUT)
#     GPIO.output(BUZZER_PIN, GPIO.LOW)  # Tắt còi ban đầu
#     print(f"✅ GPIO initialized - Buzzer on GPIO{BUZZER_PIN}")

# Load model YOLO
# CẢNH BÁO: Dùng pretrained tạm để test - KHÔNG phát hiện được drowsy/texting/etc
# Cần train lại model với: python train.py
model = YOLO("yolo11n.pt")  # Model tạm 80 classes COCO
print("⚠️ ĐANG DÙNG MODEL TẠM (COCO) - Không phát hiện drowsy/texting/talking/turning!")
print("⚠️ Chạy 'python train.py' để train model đúng với 5 classes")

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


# ======================== HÀM ĐIỀU KHIỂN CÒI (GPIO) ========================
def trigger_buzzer(class_name):
    """Bật còi cảnh báo qua GPIO"""
    print(f"🚨 ALERT: Phát hiện {class_name}!")

    # COMMENT PHẦN GPIO CHO UBUNTU/PC
    # if GPIO_AVAILABLE:
    #     try:
    #         # Bật còi
    #         GPIO.output(BUZZER_PIN, GPIO.HIGH)
    #         print(f"🔊 Còi ON - GPIO{BUZZER_PIN}")
    #
    #         # Giữ còi bật trong BUZZER_DURATION giây
    #         time.sleep(BUZZER_DURATION)
    #
    #         # Tắt còi
    #         GPIO.output(BUZZER_PIN, GPIO.LOW)
    #         print(f"🔇 Còi OFF")
    #     except Exception as e:
    #         print(f"❌ Lỗi GPIO: {e}")
    # else:
    #     print("⚠️ GPIO không khả dụng - Chỉ hiển thị cảnh báo")

    # Thay thế bằng console log cho Ubuntu/PC
    print("⚠️ [TEST MODE] Chỉ hiển thị cảnh báo - Không có GPIO")


# Đã bỏ: speak_alert(), record_video(), Telegram, Weather API

# Thời gian bắt đầu lái xe
start_time = time.time()

# Khởi tạo GUI bằng tkinter
root = tk.Tk()
root.title("Driver Monitoring System")
root.geometry("400x300")
root.resizable(False, False)

# Các nhãn hiển thị trạng thái
status_label = ttk.Label(root, text="Trạng thái: Đang chạy", font=("Arial", 12))
status_label.pack(pady=10)

behavior_label = ttk.Label(root, text="Hành vi: Chưa phát hiện", font=("Arial", 10))
behavior_label.pack(pady=5)

time_label = ttk.Label(root, text="Thời gian: Đang cập nhật", font=("Arial", 10))
time_label.pack(pady=5)

driving_time_label = ttk.Label(root, text="Thời gian lái: 0 phút", font=("Arial", 10))
driving_time_label.pack(pady=5)


# Hàm cập nhật GUI với màu sắc (đã bỏ weather)
def update_gui(behavior, current_time_str, driving_time):
    behavior_label.config(text=f"Hành vi: {behavior}")
    if behavior == "awake":
        behavior_label.config(foreground="green")  # Xanh lá cho trạng thái tỉnh táo
    elif behavior in alert_cooldowns:  # Các hành vi nguy hiểm
        behavior_label.config(foreground="red")  # Đỏ cho hành vi nguy hiểm
    else:
        behavior_label.config(foreground="black")  # Đen cho "Chưa phát hiện"

    time_label.config(text=f"Thời gian: {current_time_str}")
    driving_time_label.config(text=f"Thời gian lái: {driving_time:.0f} phút")
    root.update()


# Mở webcam
cap = cv2.VideoCapture(0)

# Biến điều khiển vòng lặp
running = True


def process_camera():
    """Xử lý camera trong thread riêng"""
    global running

    while cap.isOpened() and running:
        ret, frame = cap.read()
        if not ret:
            print("Không thể lấy dữ liệu từ webcam!")
            running = False
            break

        # Dự đoán bằng YOLO với verbose=False để tắt thông báo
        results = model(frame, conf=0.65, verbose=False)
        annotated_frame = results[0].plot()

        current_time = time.time()
        detected_classes = set()

        # Tính thời gian lái xe (phút)
        driving_time = (current_time - start_time) / 60

        # Lấy thông tin class phát hiện được
        for box in results[0].boxes:
            class_id = int(box.cls)
            class_name = class_names.get(class_id, "unknown")
            detected_classes.add(class_name)

        # Xử lý hành vi và phát cảnh báo
        detected_behavior = "Chưa phát hiện"  # Giá trị mặc định

        if detected_classes:  # Nếu có hành vi được phát hiện
            detected_behavior = list(detected_classes)[0]

        # Xử lý cảnh báo và ghi video cho các hành vi nguy hiểm
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
                            # Kích hoạt còi cảnh báo
                            trigger_buzzer(class_name)
                            last_alert_times[class_name] = current_time
                            detection_start_times[class_name] = None
            else:
                detection_start_times[class_name] = None

        # Hiển thị thông tin trên khung hình OpenCV
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

        # Lập lịch cập nhật GUI từ thread chính
        root.after(
            0, lambda: update_gui(detected_behavior, current_time_str, driving_time)
        )

        # Hiển thị frame OpenCV
        cv2.imshow("Driver Monitoring", annotated_frame)

        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord("q"):
            running = False
            break


# Hàm dọn dẹp khi thoát
def on_closing():
    global running
    running = False
    cap.release()
    cv2.destroyAllWindows()
    root.quit()
    root.destroy()


# Xử lý sự kiện đóng cửa sổ
root.protocol("WM_DELETE_WINDOW", on_closing)

# Khởi tạo và chạy camera thread
camera_thread = threading.Thread(target=process_camera, daemon=True)
camera_thread.start()

# Chạy GUI trên main thread
try:
    root.mainloop()
except KeyboardInterrupt:
    print("\n⚠️ Thoát chương trình...")
finally:
    on_closing()

# Cleanup GPIO - COMMENT CHO UBUNTU/PC
# if GPIO_AVAILABLE:
#     GPIO.cleanup()
#     print("✅ GPIO cleanup completed")

print("✅ Chương trình kết thúc")
