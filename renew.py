import os
import time
import re
import subprocess
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
NOIP_2FA_SECRET = os.environ.get('NOIP_2FA_SECRET', '').replace(" ", "").strip()
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_chrome_major_version():
    """Tự động kiểm tra phiên bản Chrome chính trên runner Linux"""
    try:
        output = subprocess.check_output(["google-chrome", "--version"]).decode("utf-8")
        match = re.search(r"(\d+)\.", output)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"⚠️ Không tự lấy được Chrome version: {e}")
    return None

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

def enter_otp_human_like(driver, otp_code):
    """Mô phỏng nhập OTP bằng tương tác phím thật (isTrusted = true)"""
    inputs = [i for i in driver.find_elements(By.TAG_NAME, "input") if i.is_displayed()]
    
    if len(inputs) >= 6:
        print(f"🧩 Đang gõ 6 số OTP ({otp_code}) bằng mô phỏng phím thật...")
        for i in range(6):
            digit = otp_code[i]
            inp = inputs[i]
