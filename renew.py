import os
import time
import requests
import pyotp
import undetected_chromedriver as uc 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
USERNAME = os.environ['NOIP_USERNAME']
PASSWORD = os.environ['NOIP_PASSWORD']
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
    # Ép driver chạy phiên bản 149 để khớp với trình duyệt hệ thống
    driver = uc.Chrome(options=options, version_main=149)

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
        
        print("⏳ Đang đợi trang bảo mật phản hồi (15s)...")
        time.sleep(15) 

        current_url = driver.current_url.lower()
        print(f"📍 URL hiện tại sau khi đăng nhập: {driver.current_url}")
        
        # XỬ LÝ KHU VỰC XÁC THỰC THIẾT BỊ / 2FA
        if "2fa/verify" in current_url:
            if not NOIP_2FA_SECRET:
                driver.save_screenshot("2fa_error.png")
                raise Exception("Phát hiện trang đòi mã xác minh nhưng thiếu NOIP_2FA_SECRET!")
                
            print("🔐 Đang tự động tính toán mã số OTP từ Secret Key...")
            clean_secret = NOIP_2FA_SECRET.replace(" ", "").strip()
            totp = pyotp.TOTP(clean_secret)
            otp_code = str(totp.now())
            print(f"🔑 Mã OTP khởi tạo thành công: {otp_code}")
            
            # Lấy toàn bộ ô nhập văn bản/số trong form
            all_inputs = driver.find_elements(By.XPATH, "//form//input[@type='text' or @type='number' or not(@type)]")
            # LỌC SẠCH: Chỉ giữ lại các ô thực sự hiển thị trên màn hình để tương tác
            visible_inputs = [inp for inp in all_inputs if inp.is_displayed()]
            
            print(f"📊 Tìm thấy {len(visible_inputs)} ô nhập hiển thị thực tế trên màn hình.")

            if len(visible_inputs) >= 6:
                print("🧩 Tiến hành rải chính xác 6 ký tự OTP vào các ô số rời...")
                for i in range(6):
                    try:
                        visible_inputs[i].clear()
                        visible_inputs[i].send_keys(otp_code[i])
                        time.sleep(0.1)
                    except Exception as input_err:
                        print(f"⚠️ Không thể gõ vào ô thứ {i+1}: {input_err}")
                
                # Tìm nút bấm xanh mang chữ "Verify" (Bất kể nó là thẻ gì: a, button, input)
                print("🖱️ Đang kích hoạt nút Verify...")
                time.sleep(1)
                try:
                    verify_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Verify') or @value='Verify']")
                    verify_btn.click()
                except:
                    print("⚠️ Không click được nút bằng Xpath, thử gửi lệnh Enter trực tiếp từ ô cuối...")
                    visible_inputs[5].send_keys(Keys.ENTER)
            else:
                print("📝 Phát hiện giao diện 1 ô nhập OTP liền chuỗi. Tiến hành điền thẳng...")
                try:
                    otp_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='mfa-code' or @name='code' or contains(@class, 'form-control')]")))
                    otp_field.clear()
                    otp_field.send_keys(otp_code)
                    otp_field.send_keys(Keys.ENTER)
                except Exception as e:
                    driver.save_screenshot("otp_field_error.png")
                    raise Exception("Không tìm thấy cấu hình ô nhập mã OTP phù hợp.")
            
            print("⏳ Đang đợi hệ thống duyệt quyền truy cập (15s)...")
            time.sleep(15)

        print("Navigating to Dynamic DNS Dashboard...")
        driver.get("https://my.noip.com/dynamic-dns")
        time.sleep(8)

        if "login" in driver.current_url:
            driver.save_screenshot("dashboard_failed.png")
            raise Exception("Bị đá về trang đăng nhập! Có thể mã OTP sinh ra bị lệch chu kỳ thời gian hoặc sai Secret Key.")

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
        send_telegram(error_msg, photo_path="error.png")
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    renew()
