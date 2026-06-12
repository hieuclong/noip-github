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

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram secrets missing. Skipping alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
        print("📲 Telegram notification sent!")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

def renew():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        time.sleep(4)

        print("Filling login form...")
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        
        # Điền mật khẩu và giả lập nhấn phím ENTER để đăng nhập
        from selenium.webdriver.common.keys import Keys
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(PASSWORD)
        
        print("Submitting login form via Enter key...")
        password_field.send_keys(Keys.ENTER)
        time.sleep(8) # Đợi 8 giây để trang web xử lý đăng nhập và chuyển hướng hoàn toàn

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(5)

        if "login" in driver.current_url:
            raise Exception("Đăng nhập thất bại! Khả năng cao bị kẹt Captcha hoặc sai tài khoản/mật khẩu.")

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
            success_idle_msg = "✅ Đăng nhập thành công. Không có tên miền nào cần bấm gia hạn hôm nay."
            print(success_idle_msg)
            # Bạn có thể bật dòng dưới nếu muốn Telegram báo về hằng ngày kể cả khi không có tên miền nào cần gia hạn
            # send_telegram(success_idle_msg)
            
    except Exception as e:
        error_msg = f"⚠️ No-IP Bot Thất Bại!\nLỗi: {str(e)}\nVui lòng kiểm tra lại tài khoản."
        print(error_msg)
        send_telegram(error_msg)
        raise e

    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
