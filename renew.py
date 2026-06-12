import os
import time
import requests
import pyotp  # Thư viện tự động sinh mã OTP 6 số
import undetected_chromedriver as uc 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
# Lấy mã Secret để sinh OTP giải quyết vấn đề thiết bị lạ
NOIP_2FA_SECRET = os.environ.get('NOIP_2FA_SECRET') 
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
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    
    print("🤖 Khởi tạo Trình duyệt Ẩn danh (Undetected Chromedriver)...")
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 1024)

    try:
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        
        wait = WebDriverWait(driver, 25)

        print("Filling login form...")
        username_field = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        username_field.clear()
        username_field.send_keys(USERNAME)
        print("🎯 Đã điền xong Username")
        
        password_field = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
        password_field.clear()
        password_field.send_keys(PASSWORD)
        print("🎯 Đã điền xong Password")
        
        print("Submitting login form via Enter key...")
        password_field.send_keys(Keys.ENTER)
        
        print("⏳ Đang đợi kiểm tra trang xác thực thiết bị/2FA (15s)...")
        time.sleep(15) 

        current_url = driver.current_url.lower()
        print(f"📍 URL hiện tại sau khi nhấn đăng nhập: {driver.current_url}")
        
        # XỬ LÝ NẾU BỊ CHẶN BỞI TRANG ĐÒI MÃ XÁC THỰC
        if "2fa/verify" in current_url:
            if not NOIP_2FA_SECRET:
                driver.save_screenshot("2fa_error.png")
                raise Exception("Phát hiện trang đòi mã xác minh nhưng bạn chưa cấu hình NOIP_2FA_SECRET!")
                
            print("🔐 Phát hiện trang kiểm tra bảo mật! Đang tự động sinh mã OTP...")
            # Sử dụng thuật toán TOTP để tính toán mã số dựa theo thời gian thực
            totp = pyotp.TOTP(NOIP_2FA_SECRET.replace(" ", ""))
            otp_code = totp.now()
            print(f"🔑 Mã OTP vừa khởi tạo thành công: {otp_code}")
            
            # Chờ ô nhập mã xuất hiện (No-IP sử dụng ô có name="code")
            otp_field = wait.until(EC.element_to_be_clickable((By.NAME, "code")))
            otp_field.send_keys(otp_code)
            time.sleep(1)
            otp_field.send_keys(Keys.ENTER)
            
            print("⏳ Đang đợi hệ thống phê duyệt mã OTP (10s)...")
            time.sleep(10)

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(8)

        if "login" in driver.current_url:
            driver.save_screenshot("dashboard_failed.png")
            raise Exception("Bị đá về trang login khi cố vào Dashboard! Hãy chắc chắn bạn đã nhấn kích hoạt nút 2FA trên web.")

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
        
        if os.path.exists("2fa_error.png"):
            send_telegram(error_msg, photo_path="2fa_error.png")
        elif os.path.exists("dashboard_failed.png"):
            send_telegram(error_msg, photo_path="dashboard_failed.png")
        else:
            driver.save_screenshot("error.png")
            send_telegram(error_msg, photo_path="error.png")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
