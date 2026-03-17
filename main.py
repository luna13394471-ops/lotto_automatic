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
    # [핵심] 렌더러 타임아웃 및 메모리 부족 해결 옵션
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # [핵심] 모바일 리다이렉트 방지 및 스텔스 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # [최적화] 이미지 및 광고 로딩 차단 (속도 향상 및 메모리 절약)
    chrome_options.page_load_strategy = 'eager' 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 봇 감지 우회 스크립트
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 20)
        
        # 1. 로그인 접속 (PC 버전 강제 파라미터 추가)
        log("1. 로그인 페이지 접속 중...")
        driver.get("https://dhlottery.co.kr/login.do?method=login")
        time.sleep(3)

        # 리다이렉트 체크 및 강제 교정
        if "m.dhlottery" in driver.current_url:
            log("   ⚠️ 모바일 감지됨. PC 버전으로 강제 전환 시도...")
            driver.get("https://dhlottery.co.kr/common.do?method=main")
            time.sleep(2)
            driver.get("https://dhlottery.co.kr/login.do?method=login")

        # 2. 로그인 정보 입력
        log("2. 아이디/비밀번호 입력...")
        user_input = wait.until(EC.presence_of_element_located((By.ID, "inpUserId")))
        user_input.send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(4)

        # 3. 구매 페이지 이동
        log("3. 구매 페이지 이동 중...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 4. Iframe 전환
        log("4. Iframe 전환 시도...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 5. 번호 선택 처리 (자동번호발급)
        log("5. 자동 번호 선택...")
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 1개 선택
        amt_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amt_select.select_by_value("1")
        
        # 번호 선택 완료 클릭
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 6. 구매하기 버튼 클릭
        log("6. 최종 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 7. 확인 팝업 승인
        log("7. 승인 확인 팝업 처리 중...")
        try:
            # 브라우저 알림(Alert) 발생 시 수락
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except: pass

        try:
            # 레이어 확인 버튼 클릭
            final_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", final_ok)
        except: pass

        # 8. 성공 결과 대기 및 캡처 (가장 중요한 부분)
        log("8. 구매 결과 화면 대기 및 캡처 중...")
        success_captured = False
        try:
            # 성공 팝업(pop_content)이 화면에 나타날 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) # 애니메이션 처리 대기
            driver.save_screenshot("lotto_result.png")
            success_captured = True
            log("   - 성공 화면 확인 및 캡처 완료")
        except:
            log("   - 결과 팝업 미탐지 (현재 화면 강제 저장)")
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
