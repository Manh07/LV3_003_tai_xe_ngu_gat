# 🚨 Hệ Thống Phát Hiện Buồn Ngủ Khi Lái Xe - GPIO Version

<div align="center">

![Version](https://img.shields.io/badge/version-2.0-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%204-red)
![Python](https://img.shields.io/badge/python-3.8+-green)

**Phát hiện hành vi lái xe nguy hiểm bằng AI + Cảnh báo bằng còi GPIO**

Tối ưu cho **Raspberry Pi 4** | FPS x2 | RAM -60% | Không cần Internet

</div>

---

## 📋 Tổng Quan

Hệ thống sử dụng **YOLOv8** để phát hiện 5 hành vi:
- 😊 `awake` - Tỉnh táo (bình thường)
- 😴 `drowsy` - Buồn ngủ → **⚠️ Cảnh báo**
- 📱 `texting_phone` - Nhắn tin → **⚠️ Cảnh báo**
- 📞 `talking_phone` - Nói điện thoại → **⚠️ Cảnh báo**
- 🔄 `turning` - Quay đầu không an toàn → **⚠️ Cảnh báo**

Khi phát hiện hành vi nguy hiểm → **Còi GPIO bật 2 giây**

---

## ⚡ Hiệu Năng

### Raspberry Pi 4 (4GB RAM):
```
FPS:        8-12 fps (tăng gấp đôi so với phiên bản cũ)
RAM:        300MB (giảm 60%)
CPU:        65-80% (giảm 25%)
Nhiệt độ:   56-60°C
Alert:      <0.2s (realtime)
```

### PC (i5, 8GB RAM):
```
FPS:        28-30 fps
RAM:        280MB
CPU:        30-40%
```

---

## 📦 Cài Đặt

### **Trên Raspberry Pi 4:**

```bash
# 1. Update hệ thống
sudo apt update && sudo apt upgrade -y

# 2. Cài các package cần thiết
sudo apt install python3-opencv python3-rpi.gpio -y

# 3. Cài PyTorch và YOLO (mất ~10 phút)
pip3 install ultralytics torch torchvision

# 4. Kiểm tra
python3 -c "import cv2, RPi.GPIO; print('OK')"
```

### **Trên PC (để test code):**

```bash
pip install -r requirements_minimal.txt
# Sẽ skip GPIO tự động, code vẫn chạy bình thường
```

---

## 🔌 Kết Nối Phần Cứng

### **Linh kiện cần thiết:**
- 1x Buzzer 5V (Active hoặc Passive)
- 1x Điện trở 220Ω hoặc 330Ω
- 2x Dây nối
- 1x Breadboard (tùy chọn)

### **Sơ đồ kết nối:**

```
┌─────────────────────────────────────────┐
│         RASPBERRY PI 4                  │
│                                         │
│  GPIO17 (Pin 11) ──[220Ω]──► Buzzer (+)│
│  GND (Pin 6) ──────────────► Buzzer (-) │
└─────────────────────────────────────────┘
```

### **Chi tiết pinout:**

```
Raspberry Pi GPIO Header (40 pins)

    3.3V [ 1] [ 2] 5V
   GPIO2 [ 3] [ 4] 5V
   GPIO3 [ 5] [ 6] GND ◄───── GND cho Buzzer
   GPIO4 [ 7] [ 8] GPIO14
     GND [ 9] [10] GPIO15
   GPIO17[11] [12] GPIO18 ◄─── GPIO17 cho Buzzer (Signal)
   GPIO27[13] [14] GND
     ...
```

**Kết nối:**
1. **GPIO17 (Physical Pin 11)** → Điện trở 220Ω → **Buzzer (+)**
2. **GND (Physical Pin 6)** → **Buzzer (-)**

### **Test buzzer:**

```python
# Chạy script này để test
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

print("Testing buzzer...")
GPIO.output(17, GPIO.HIGH)  # Bật
time.sleep(2)
GPIO.output(17, GPIO.LOW)   # Tắt
GPIO.cleanup()
print("Done!")
```

---

## 🚀 Chạy Chương Trình

### **Chạy thông thường:**
```bash
sudo python3 main.py
```

### **Chạy background:**
```bash
nohup sudo python3 main.py > output.log 2>&1 &
```

### **Dừng chương trình:**
- Nhấn `q` trong cửa sổ OpenCV
- Hoặc `Ctrl+C` trong terminal

### **Console output:**
```
✅ GPIO initialized - Buzzer on GPIO17
✅ Model loaded: runs/detect/train24/weights/best.pt

🚨 ALERT: Phát hiện drowsy!
🔊 Còi ON - GPIO17
🔇 Còi OFF

🚨 ALERT: Phát hiện texting_phone!
🔊 Còi ON - GPIO17
🔇 Còi OFF
```

---

## ⚙️ Cấu Hình

Mở file `main.py` để điều chỉnh:

### **1. GPIO Pin** (dòng 20):
```python
BUZZER_PIN = 17  # Đổi thành GPIO khác nếu cần (18, 22, 23, 24, 25...)
```

### **2. Thời gian còi** (dòng 21):
```python
BUZZER_DURATION = 2  # Giây (khuyến nghị 1-5s)
```

### **3. Cooldown (thời gian chờ giữa 2 lần cảnh báo)** (dòng 42-47):
```python
alert_cooldowns = {
    'drowsy': 15,         # 15 giây
    'texting_phone': 10,  # 10 giây
    'talking_phone': 8,   # 8 giây
    'turning': 5          # 5 giây
}
```

### **4. Độ nhạy phát hiện** (dòng 50):
```python
DETECTION_DURATION_THRESHOLD = 3  # Hành vi phải kéo dài 3s mới cảnh báo
```

### **5. Model confidence** (dòng 133):
```python
results = model(frame, conf=0.65, verbose=False)  # 0.65 = 65% confidence
```

### **6. Đường dẫn model** (dòng 30):
```python
model = YOLO("runs/detect/train24/weights/best.pt")
# Hoặc: model = YOLO("model_trained/best.pt")
```

---

## 🎮 Cách Hoạt Động

### **Quy trình:**

```
1. Camera capture frame
   ↓
2. YOLO phát hiện hành vi
   ↓
3. Nếu là hành vi nguy hiểm (drowsy/texting/talking/turning):
   - Đếm thời gian liên tục
   ↓
4. Nếu kéo dài > 3 giây:
   - Kiểm tra cooldown
   ↓
5. Nếu đã hết cooldown:
   → Bật GPIO17 (còi kêu 2 giây)
   → Cập nhật GUI + OpenCV display
   → Reset timer
```

### **Cooldown System:**
- Tránh còi kêu liên tục (spam)
- Mỗi hành vi có cooldown riêng
- Ví dụ: Phát hiện drowsy → Còi kêu → Chờ 15s → Mới cảnh báo lại

---

## 🐛 Xử Lý Lỗi

### **1. Lỗi GPIO permission**
```
RuntimeError: No access to /dev/mem
```
**Giải pháp:**
```bash
# Option 1: Chạy với sudo
sudo python3 main.py

# Option 2: Thêm user vào gpio group
sudo usermod -a -G gpio $USER
# Sau đó logout và login lại
```

### **2. Buzzer không kêu**

**Checklist:**
- [ ] Đã kết nối đúng GPIO17 và GND?
- [ ] Điện trở có đúng 220Ω không?
- [ ] Buzzer có hoạt động không? (test bằng pin 3V)
- [ ] Có chạy với `sudo` không?
- [ ] GPIO17 có bị dùng bởi process khác?

**Test buzzer:**
```bash
# Chạy script test ở trên để kiểm tra
```

### **3. Camera không hoạt động**
```
Không thể lấy dữ liệu từ webcam!
```
**Giải pháp:**
```bash
# Kiểm tra camera có sẵn không
ls -l /dev/video*

# Thử camera index khác
# Trong main.py dòng 118:
cap = cv2.VideoCapture(0)  # Thử 0, 1, 2...
```

### **4. Model không tìm thấy**
```
FileNotFoundError: runs/detect/train24/weights/best.pt
```
**Giải pháp:** Sửa dòng 30 với đường dẫn đúng:
```python
model = YOLO("model_trained/best.pt")
# Hoặc đường dẫn tuyệt đối
```

### **5. FPS thấp trên Pi**

**Tối ưu:**
```python
# 1. Giảm image size (dòng 133)
results = model(frame, conf=0.65, verbose=False, imgsz=320)

# 2. Hoặc skip frames
frame_count = 0
if frame_count % 2 == 0:  # Xử lý 1, bỏ 1
    results = model(frame, ...)
frame_count += 1
```

### **6. Nhiệt độ cao**
```bash
# Kiểm tra nhiệt độ
vcgencmd measure_temp

# Nếu > 70°C:
# - Gắn heatsink + fan
# - Giảm overclock
# - Giảm image size
```

---

## 💡 Tips & Tricks

### **1. Auto-start khi khởi động Pi:**
   ```bash
sudo nano /etc/rc.local

# Thêm trước dòng "exit 0":
cd /home/pi/project && sudo python3 main.py &
```

### **2. Monitor hệ thống:**
   ```bash
# CPU, RAM
htop

# Nhiệt độ realtime
watch -n 1 vcgencmd measure_temp

# RAM available
free -h
```

### **3. Kill process nếu treo:**
   ```bash
pkill -f main.py
# Hoặc
ps aux | grep main.py
sudo kill -9 <PID>
   ```

### **4. Log output ra file:**
     ```bash
sudo python3 main.py > output.log 2>&1 &
tail -f output.log  # Xem log realtime
```

### **5. Backup project:**
```bash
tar -czf project_backup_$(date +%Y%m%d).tar.gz ~/project/
```

### **6. SSH vào Pi từ xa:**
   ```bash
# Từ PC/laptop
ssh pi@192.168.x.x
cd project
sudo python3 main.py
```

---

## 📊 So Sánh Phiên Bản

| Tính năng | Phiên bản CŨ | Phiên bản MỚI (v2.0) |
|-----------|--------------|----------------------|
| **Cảnh báo** | Giọng nói (gTTS) | Còi GPIO ✅ |
| **Ghi video** | 15 giây | Không (nhẹ hơn) ✅ |
| **Telegram** | Có | Không ✅ |
| **Weather API** | Có | Không ✅ |
| **FPS (Pi 4)** | 5 fps | 10 fps ✅ (+100%) |
| **RAM** | 750MB | 300MB ✅ (-60%) |
| **CPU** | 98% | 73% ✅ (-25%) |
| **Internet** | Cần | Không cần ✅ |
| **Storage/phút** | +10MB | 0MB ✅ |
| **Phần cứng** | Không | GPIO buzzer ✅ |

**→ Nhẹ hơn, nhanh hơn, thực tế hơn!**

---

## 📁 Cấu Trúc File

```
project/
├── main.py                    # ⭐ File chính (200 dòng)
├── best.pt                    # Model YOLO
├── requirements_minimal.txt   # Dependencies (9 packages)
├── README.md                  # ⭐ File này (tài liệu duy nhất)
└── HARDWARE_DIAGRAM.txt       # Sơ đồ phần cứng (tùy chọn)
   ```

---

## 🔧 Tối Ưu Thêm (Nếu Cần)

### **1. Headless mode (không GUI):**
Comment các dòng Tkinter trong `main.py`:
```python
# root = tk.Tk()
# ...
# root.mainloop()
```

### **2. Không hiển thị OpenCV:**
Comment dòng:
```python
# cv2.imshow("Driver Monitoring", annotated_frame)
```

### **3. Export model sang ONNX (nhanh hơn):**
```bash
yolo export model=best.pt format=onnx imgsz=320
```
Sửa main.py:
```python
model = YOLO("best.onnx")
```

### **4. Pattern còi khác nhau:**
```python
def trigger_buzzer(class_name):
    patterns = {
        'drowsy': [(0.5, 0.5), (0.5, 0.5)],     # 2 tiếng dài
        'texting_phone': [(0.2, 0.1)] * 4,      # 4 tiếng ngắn
        'talking_phone': [(0.3, 0.2)] * 3,
        'turning': [(0.1, 0.1)] * 2
    }
    
    if GPIO_AVAILABLE:
        for on_time, off_time in patterns.get(class_name, [(2, 0)]):
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(on_time)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(off_time)
```

---

## ❓ FAQ

### **Q: Có chạy được trên PC không?**
A: Có! Code tự động skip GPIO nếu không phải Pi. Chỉ in warning, vẫn chạy bình thường.

### **Q: Cần internet không?**
A: Không! 100% offline. Chỉ cần internet khi cài đặt dependencies.

### **Q: Buzzer nào tốt nhất?**
A: Passive Buzzer 5V (~10k VNĐ). Active cũng được nhưng âm thanh đơn điệu hơn.

### **Q: Tôi có thể dùng GPIO khác không?**
A: Có! Đổi `BUZZER_PIN = 17` thành GPIO bất kỳ (18, 22, 23, 24, 25, 27).

### **Q: Làm sao thêm LED cảnh báo?**
A: Kết nối LED vào GPIO18, thêm vào `trigger_buzzer()`:
```python
LED_PIN = 18
GPIO.setup(LED_PIN, GPIO.OUT)

def trigger_buzzer(class_name):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(LED_PIN, GPIO.HIGH)  # LED sáng
    time.sleep(2)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(LED_PIN, GPIO.LOW)   # LED tắt
```

### **Q: Model của tôi có tên khác?**
A: Sửa dòng 30:
```python
model = YOLO("ten_model_cua_ban.pt")
```

### **Q: Làm sao xem log khi chạy background?**
A:
   ```bash
nohup sudo python3 main.py > output.log 2>&1 &
tail -f output.log
   ```

---

## 🎓 Thông Tin Dự Án

- **Tên**: Hệ Thống Phát Hiện Buồn Ngủ Khi Lái Xe
- **Phiên bản**: v2.0 (GPIO Buzzer)
- **Đơn vị**: AIoTLab - Khoa Công Nghệ Thông Tin
- **Trường**: Đại Học Đại Nam
- **Năm**: 2024
- **License**: Educational Use Only

---

## 🌟 Credits

**Công nghệ sử dụng:**
- YOLOv8 (Ultralytics)
- PyTorch
- OpenCV
- Raspberry Pi GPIO
- Python 3.11

**Developed with ❤️ by AIoTLab**

---

## 📞 Liên Hệ & Hỗ Trợ

- 🏫 **AIoTLab** - Đại Học Đại Nam
- 🌐 Website: https://fit.dainam.edu.vn
- 📧 Email: fit@dainam.edu.vn

---

<div align="center">

**🎉 Chúc bạn thành công! 🎉**

Made with 💻 by AIoTLab | Đại Học Đại Nam

[⬆ Về đầu trang](#-hệ-thống-phát-hiện-buồn-ngủ-khi-lái-xe---gpio-version)

</div>
