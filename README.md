# Cài các package có sẵn từ apt
sudo apt update
sudo apt install -y python3-opencv python3-pil python3-numpy python3-yaml python3-scipy python3-tqdm

# Cài RPi.GPIO
sudo apt install -y python3-rpi.gpio

# Cài PyTorch (nhẹ, tối ưu cho Pi)
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu --break-system-packages

# Cài ultralytics
pip3 install ultralytics --break-system-packages