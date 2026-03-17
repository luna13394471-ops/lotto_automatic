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
# 드라이버 버전 갈등 해결을 위한 임포트
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

number = 1 

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {msg}")

def send_telegram_message(message: str, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try: requests.post(url, data=payload, timeout=10)
    except: pass
    if photo_path and os.path.exists(photo_path):
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
        except: pass

def run_lotto_purchase():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    # --- [핵심 수정] 드라이버 자동 매칭 로직 ---
    try:
        # 시스템 PATH의 드라이버를 무시하고 146 버전에 맞는 드라이버를 즉시 설치하여 연결
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        log(f"드라이버 로드 실패: {e}")
        # 예외 상황 시 기본 드라이버 시도
        driver = webdriver.Chrome(options=chrome_options)
    # ---------------------------------------

    wait = WebDriverWait(driver, 15)
    
    try:
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        
        log("2. 로그인 정보 입력...")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        log("3. 구매 페이지 이동...")
        purchase_url = "https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40"
        driver.get(purchase_url)
        time.sleep(5)

        log("4. Iframe 전환...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
        
        log("5. 자동 번호 선택 및 구매...")
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(number))
        driver.find_element(By.ID, "btnSelectNum").click()
        driver.find_element(By.ID, "btnBuy").click()
        
        log("6. 최종 확인 팝업 승인...")
        confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, confirm_xpath))).click()
        
        log("7. 성공 스크린샷 저장 중...")
        try:
            # 구매 결과 레이어(pop_content)가 뜰 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            log("결과 팝업 대기 실패, 현재 화면 캡처")
            
        driver.save_screenshot("lotto_result.png")
        log("🎉 구매 프로세스 완료!")
        return True, "✅ 로또 자동 구매 성공!"
        
    except Exception as e:
        log(f"❌ 에러: {str(e)}")
        driver.save_screenshot("lotto_error.png")
        return False, f"❌ 오류 발생: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 2
    attempt = 1
    while attempt <= MAX_RETRIES:
        log(f"==== 시도 {attempt}/{MAX_RETRIES} ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        else:
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
            else:
                time.sleep(10)
        attempt += 1
