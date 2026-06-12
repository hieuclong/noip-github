import os
import time
import requests
# Thay thế webdriver mặc định bằng undetected_chromedriver
import undetected_chromedriver as uc 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message, photo_path=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    if photo_path and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
                requests.post(url, data=data, files=files)
            return
        except Exception as e:
            print(f"❌ Failed to send Telegram photo: {e}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except: pass

def renew():
    # Cấu hình Options riêng cho undetected_chromedriver
    options = uc.ChromeOptions()
    options.add_argument("--headless") # Chạy ngầm không giao diện
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    
    print("🤖 Khởi tạo Trình duyệt Ẩn danh (Undetected Chromedriver)...")
    # Khởi tạo driver tự động tương thích phiên bản mà không cần ChromeDriverManager
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 1024)

    try:
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        
        wait = WebDriverWait(driver, 25)

        print("Filling login form...")
        # Đợi ô username thực sự mở khóa để tương tác
        username_field = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        username_field.clear()
        
        # Mô phỏng gõ phím như người thật bằng cách gửi chuỗi dữ liệu
        username_field.send_keys(USERNAME)
        print("🎯 Đã điền xong Username")
        
        password_field = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
        password_field.clear()
        password_field.send_keys(PASSWORD)
        print("🎯 Đã điền xong Password")
        
        print("Submitting login form via Enter key...")
        password_field.send_keys(Keys.ENTER)
        time.sleep(12) 

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(8)

        if "login" in driver.current_url or "geoblock" in driver.current_url:
            driver.save_screenshot("error.png")
            raise Exception("Đăng nhập thất bại! Vẫn bị giữ lại ở trang đăng nhập.")

        print("Checking for hosts to renew...")
        confirm_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Confirm')]")
        
        if len(confirm_buttons) > 0:
            count = 0
            for btn in confirm_buttons:
                btn.click()
                count += 1
                time.sleep(2)
            success_msg = f"✅ Success! Bạn Trung Hiếu đã tự động gia hạn thành công {count} tên miền trên No-IP."
            print(success_msg)
            send_telegram(success_msg) 
        else:
            print("✅ Đăng nhập thành công. Không có tên miền nào cần bấm gia hạn hôm nay.")
            
    except Exception as e:
        error_msg = f"⚠️ No-IP Bot Thất Bại!\nLỗi: {str(e)}"
        print(error_msg)
        driver.save_screenshot("error.png")
        if os.path.exists("error.png"):
            send_telegram(error_msg, photo_path="error.png")
        else:
            send_telegram(error_msg)
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
