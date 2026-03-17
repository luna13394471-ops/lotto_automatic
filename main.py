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
from selenium.common.exceptions import TimeoutException

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
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      data={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                              data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
    except: pass

def get_driver():
    chrome_options = Options()
    # 안정적인 헤드리스 실행을 위한 기본 옵션
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 봇 감지 우회 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # 페이지 로드 전략을 정상(normal)으로 복구하여 로그인 폼이 완벽히 뜰 때까지 대기
    chrome_options.page_load_strategy = 'normal'

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 25) # 넉넉한 대기 시간
        
        # 1. 로그인 페이지 접속
        log("1. 로그인 페이지 접속 중...")
        driver.get("https://dhlottery.co.kr/login.do?method=login")
        time.sleep(3)
        
        # 2. 아이디/비밀번호 입력
        log("2. 아이디/비밀번호 입력 대기 중...")
        try:
            # presence가 아닌 visibility(화면에 실제로 보이는지)로 체크
            user_input = wait.until(EC.visibility_of_element_located((By.ID, "inpUserId")))
            user_input.send_keys(id)
            driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
            driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        except TimeoutException:
            # 요소를 못 찾았을 경우 현재 URL과 제목을 출력하여 IP 차단 여부 진단
            log(f"   🚨 로그인 폼을 찾을 수 없습니다. (현재 URL: {driver.current_url})")
            log(f"   🚨 페이지 제목: {driver.title}")
            driver.save_screenshot("lotto_error.png")
            raise Exception("로그인 폼 미노출 (봇 차단 또는 캡차 발생 가능성 높음)")

        time.sleep(4)

        # 3. 구매 페이지 이동
        log("3. 구매 페이지 이동 중...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 4. Iframe 전환
        log("4. Iframe 전환 시도...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 5. 번호 선택
        log("5. 자동 번호 선택...")
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value("1")
        
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 6. 구매하기 버튼 클릭
        log("6. 최종 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 7. 승인 팝업 처리
        log("7. 승인 확인 팝업 처리 중...")
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except: pass

        try:
            final_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", final_ok)
        except: pass

        # 8. 성공 결과 캡처
        log("8. 구매 결과 화면 대기 및 캡처 중...")
        try:
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) 
            log("   - 성공 화면 확인 완료")
        except:
            log("   - 결과 팝업 미탐지 (현재 화면 저장)")

        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver:
            driver.save_screenshot("lotto_error.png")
        return False, f"오류 발생: {str(e)}"
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 2
    for i in range(1, MAX_RETRIES + 1):
        log(f"==== 시도 {i}/{MAX_RETRIES} ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        elif i == MAX_RETRIES:
            send_telegram_message(f"🚨 최종 실패 알림\n{message}", "lotto_error.png")
        time.sleep(10)
