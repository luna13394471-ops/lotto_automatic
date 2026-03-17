import os
import time
import requests
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수
ID = os.environ.get("LOTTO_ID")
PASSWORD = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NUMBER = 1 

def send_telegram_message(message: str, photo_path=None):
    """텔레그램 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
        if photo_path and os.path.exists(photo_path):
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
    except: pass

def run_lotto_purchase():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 기본 봇 차단 우회만 유지
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        # 드라이버 버전 이슈 해결을 위한 Service 설정만 유지
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        wait = WebDriverWait(driver, 30)

        # 1. 로그인 (가장 단순한 직접 접속)
        driver.get("https://dhlottery.co.kr/login")
        time.sleep(2)
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)

        # 2. 구매 페이지 이동
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 3. Iframe 전환 (기존 방식)
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))

        # 4. 자동번호발급 및 구매 로직 (기본 ID 사용)
        # 자동번호발급
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        
        # 수량 선택
        amount_sel = Select(driver.find_element(By.ID, "amoundApply"))
        amount_sel.select_by_value(str(NUMBER))
        
        # 확인 버튼
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기
        driver.find_element(By.ID, "btnBuy").click()
        time.sleep(1)

        # 5. 최종 확인 팝업 (가장 단순한 XPath)
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
        confirm_btn.click()
        
        time.sleep(3)
        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 시도 완료!"

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("lotto_error.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    photo = "lotto_result.png" if success else "lotto_error.png"
    send_telegram_message(message, photo)
