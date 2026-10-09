import os
import time
import requests
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
NOIP_2FA_SECRET = os.environ.get('NOIP_2FA_SECRET', '').replace(" ", "").strip()
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
                requests.post(url, data=data, files=files, timeout=15)
            return
        except Exception as e:
            print(f"❌ Failed to send Telegram photo: {e}")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: 
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except: 
        pass

def enter_otp_native(driver, otp_code):
    """Mô phỏng nhập OTP qua Native JS Event để kích hoạt React Form"""
    inputs = [i for i in driver.find_elements(By.TAG_NAME, "input") if i.is_displayed()]
    
    if len(inputs) >= 6:
        print(f"🧩 Đang truyền 6 số OTP ({otp_code}) vào các ô riêng biệt qua Native Event...")
        for i in range(6):
            digit = otp_code[i]
            inp = inputs[i]
            driver.execute_script("""
                var el = arguments[0];
                var val = arguments[1];
                var valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                valueSetter.call(el, val);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new KeyboardEvent('keydown', { key: val, bubbles: true }));
                el.dispatchEvent(new KeyboardEvent('keyup', { key: val, bubbles: true }));
            """, inp, digit)
            time.sleep(0.1)
        
        time.sleep(1)
        try:
            btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Verify') or contains(text(), 'Submit')]")
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            inputs[5].send_keys(Keys.ENTER)

    elif len(inputs) == 1:
        print(f"📝 Đang truyền OTP ({otp_code}) vào ô nhập dạng liền...")
        driver.execute_script("""
            var el = arguments[0];
            var val = arguments[1];
            var valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            valueSetter.call(el, val);
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, inputs[0], otp_code)
        inputs[0].send_keys(Keys.ENTER)

def renew():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    print("🤖 Khởi tạo Trình duyệt Chrome...")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1280, 1024)
    wait = WebDriverWait(driver, 30)

    try:
        # 1. MỞ TRANG ĐĂNG NHẬP
        print("Opening No-IP Login Page...")
        driver.get("https://www.noip.com/login")
        time.sleep(4)

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
        time.sleep(6)

        current_url = driver.current_url.lower()
        print(f"📍 URL hiện tại sau khi gửi tài khoản: {driver.current_url}")
        
        # 2. XỬ LÝ 2FA
        if "2fa" in current_url or "verify" in current_url:
            if not NOIP_2FA_SECRET:
                driver.save_screenshot("2fa_error.png")
                raise Exception("Phát hiện trang đòi mã xác minh nhưng thiếu NOIP_2FA_SECRET!")
                
            print("🔐 Tính toán mã OTP...")
            totp = pyotp.TOTP(NOIP_2FA_SECRET)
            
            # Kiểm tra thời gian còn lại của chu kỳ 30 giây hiện tại
            time_remaining = 30 - (int(time.time()) % 30)
            if time_remaining < 5:
                print(f"⏳ Mã OTP sắp hết hạn (còn {time_remaining}s), tạm dừng {time_remaining + 1}s chờ mã mới...")
                time.sleep(time_remaining + 1)
                
            otp_code = str(totp.now())
            print(f"🔑 Mã OTP khởi tạo: {otp_code}")
            
            enter_otp_native(driver, otp_code)
            print("⏳ Đã gửi OTP, đang chờ hệ thống duyệt phiên và tự chuyển hướng...")

        # 3. TỰ ĐỘNG CHỜ ĐIỀU HƯỚNG TỚI MY.NOIP.COM
        print("🚀 Đang đợi hệ thống cấp Token và chuyển tới Dashboard...")
        wait.until(EC.url_contains("my.noip.com"))
        time.sleep(8)

        # Chuyển tiếp vào danh mục Dynamic DNS trên Dashboard nếu chưa tới hẳn
        if "dynamic-dns" not in driver.current_url:
            driver.get("https://my.noip.com/dynamic-dns")
            time.sleep(6)

        print(f"📍 URL hiện tại: {driver.current_url}")

        if "login" in driver.current_url.lower() and "my.noip.com" not in driver.current_url:
            driver.save_screenshot("dashboard_failed.png")
            raise Exception("Bị đá về trang đăng nhập! Phiên làm việc không được chấp nhận.")

        # 4. GIA HẠN HOST
        print("Checking for hosts to renew...")
        time.sleep(3)
        confirm_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Confirm')]")
        
        if len(confirm_buttons) > 0:
            count = 0
            for btn in confirm_buttons:
                driver.execute_script("arguments[0].click();", btn)
                count += 1
                time.sleep(2)
            success_msg = f"🎉 Success! Đã tự động gia hạn thành công {count} tên miền trên No-IP."
            print(success_msg)
            send_telegram(success_msg) 
        else:
            success_msg = "✅ Đăng nhập thành công. Không có tên miền nào cần bấm gia hạn hôm nay."
            print(success_msg)
            send_telegram(success_msg)
            
    except Exception as e:
        error_msg = f"⚠️ No-IP Bot Thất Bại!\nLỗi: {str(e)}"
        print(error_msg)
        driver.save_screenshot("error.png")
        send_telegram(error_msg, photo_path="error.png")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
