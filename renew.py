import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message, photo_path=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram secrets missing. Skipping alert.")
        return
    
    # Gửi ảnh kèm thông báo nếu có
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

    # Gửi tin nhắn văn bản thuần túy nếu không có ảnh
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
    # Đổi User-Agent sang bản mới và phổ biến hơn để giảm bớt tỷ lệ bị kích hoạt Captcha
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_size(1280, 1024) # Đặt kích cỡ màn hình để ảnh chụp rõ ràng

    try:
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        time.sleep(5)

        print("Filling login form...")
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        
        from selenium.webdriver.common.keys import Keys
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(PASSWORD)
        
        print("Submitting login form via Enter key...")
        password_field.send_keys(Keys.ENTER)
        time.sleep(10) # Tăng thời gian đợi lên 10s đề phòng mạng GitHub chậm

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(6)

        # Nếu bị đẩy về trang login hoặc trang tài khoản bị chặn
        if "login" in driver.current_url or "geoblock" in driver.current_url:
            # Chụp ảnh màn hình lưu lại thành file error.png
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
        
        # Nếu có file ảnh lỗi thì gửi kèm qua Telegram
        if os.path.exists("error.png"):
            send_telegram(error_msg, photo_path="error.png")
        else:
            send_telegram(error_msg)
        raise e

    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
