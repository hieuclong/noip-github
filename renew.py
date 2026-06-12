import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# Khai báo thêm các thư viện hỗ trợ Đợi tường minh (Explicit Waits)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message, photo_path=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram secrets missing. Skipping alert.")
        return
    
    if photo_path and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
                requests.post(url, data=data, files=files)
            print("📲 Telegram photo alert sent!")
            return
        except Exception as e:
            print(f"❌ Failed to send Telegram photo: {e}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
        print("📲 Telegram text notification sent!")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

def renew():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_size(1280, 1024) 

    try:
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        
        # Thiết lập bộ đợi tối đa 20 giây cho các phần tử trên trang
        wait = WebDriverWait(driver, 20)

        print("Filling login form...")
        # Đợi cho đến khi ô username thực sự hiển thị và tương tác được
        username_field = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
        username_field.clear() # Xóa trắng ô trước khi điền đề phòng dữ liệu rác
        username_field.send_keys(USERNAME)
        print("🎯 Đã điền xong Username")
        
        # Đợi ô password sẵn sàng
        password_field = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
        password_field.clear()
        password_field.send_keys(PASSWORD)
        print("🎯 Đã điền xong Password")
        
        print("Submitting login form via Enter key...")
        password_field.send_keys(Keys.ENTER)
        
        # Đợi 10 giây để hệ thống xử lý sau khi nhấn Enter
        time.sleep(10) 

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(6)

        if "login" in driver.current_url or "geoblock" in driver.current_url:
            screenshot_path = "error.png"
            driver.save_screenshot(screenshot_path)
            raise Exception("Đăng nhập thất bại! Xem ảnh chụp màn hình đính kèm để biết lý do cụ thể.")

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
        
        if os.path.exists("error.png"):
            send_telegram(error_msg, photo_path="error.png")
        else:
            # Nếu lỗi xảy ra ngay bước điền form, chụp ảnh lại tại thời điểm đó để kiểm tra
            driver.save_screenshot("error.png")
            send_telegram(error_msg, photo_path="error.png")
        raise e

    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
