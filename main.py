import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {msg}")

def send_telegram_message(message: str, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
    except: pass
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                              data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
        except: pass

def run_lotto_purchase():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # 봇 감지 우회를 위한 설정 강화
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    try:
        log("0. 드라이버 버전 체크 및 설치 중...")
        # 시스템의 /usr/bin/chromedriver를 무시하도록 경로를 명시적으로 지정
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 타임아웃 설정 (브라우저 응답 대기 시간)
        driver.set_page_load_timeout(30)
        wait = WebDriverWait(driver, 15)
        
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        
        log("2. 로그인 시도...")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        log("3. 구매 페이지 이동...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        log("4. Iframe 전환...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        
        log("5. 번호 선택 및 구매...")
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click() # 자동선택
        Select(driver.find_element(By.ID, "amoundApply")).select_by_value("1") # 1개
        driver.find_element(By.ID, "btnSelectNum").click() # 선택완료
        driver.find_element(By.ID, "btnBuy").click() # 구매하기
        
        log("6. 최종 확인 팝업 클릭...")
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
        confirm_btn.click()
        
        log("7. 성공 결과 대기 및 캡처...")
        try:
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            log("결과 팝업 미탐지, 현재 화면 저장")
            
        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        try: driver.save_screenshot("lotto_error.png")
        except: pass
        return False, f"실행 오류: {str(e)}"
    finally:
        try: driver.quit()
        except: pass

if __name__ == "__main__":
    MAX_RETRIES = 2
    for attempt in range(1, MAX_RETRIES + 1):
        log(f"==== 시도 {attempt}/{MAX_RETRIES} ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        elif attempt == MAX_RETRIES:
            send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
        time.sleep(5)
