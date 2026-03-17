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
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 봇 감지 우회 핵심 설정
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # PC 버전 고정을 위한 최신 User-Agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # webdriver 속성 제거 (봇 감지 우회)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.set_page_load_timeout(60)
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 20)
        
        # 1. 로그인 페이지 접속
        log("1. 로그인 페이지 접속 중...")
        driver.get("https://dhlottery.co.kr/login.do?method=login")
        time.sleep(5) # 페이지 안정화 대기
        
        # 페이지 상태 확인 (차단 여부 체크)
        current_title = driver.title
        log(f"   - 현재 페이지 제목: {current_title}")
        if "Access Denied" in current_title or "차단" in current_title:
            raise Exception("🚨 사이트로부터 IP가 차단되었습니다.")

        # 2. 로그인 정보 입력
        log("2. 아이디/비밀번호 입력...")
        try:
            user_input = wait.until(EC.presence_of_element_located((By.ID, "inpUserId")))
            user_input.send_keys(id)
            driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
            driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
            log("   - 로그인 버튼 클릭 완료")
        except TimeoutException:
            driver.save_screenshot("login_timeout.png")
            raise Exception("로그인 입력창을 찾을 수 없습니다. (차단 혹은 리다이렉트 의심)")
        
        time.sleep(5)

        # 3. 구매 페이지 이동
        log("3. 구매 페이지 이동 중...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(7)

        # 4. Iframe 전환
        log("4. Iframe 전환 시도...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 5. 번호 선택 로직
        log("5. 자동 번호 선택...")
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택
        amt_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amt_select.select_by_value("1")
        
        # 번호 선택 완료
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 6. 구매하기
        log("6. 최종 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 7. 확인 팝업 승인
        log("7. 승인 확인 팝업 처리 중...")
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except: pass

        try:
            final_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", final_ok)
        except: pass

        # 8. 성공 결과 대기 및 캡처 (수정 핵심 로직)
        log("8. 구매 결과 화면 대기 및 캡처 중...")
        try:
            # 성공 팝업(pop_content)이 나타날 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) 
            log("   - 성공 화면 확인 완료")
        except:
            log("   - 결과 팝업 미탐지 (현재 화면 캡처)")

        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 프로세스 성공!")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver:
            driver.save_screenshot("lotto_error.png")
        return False, f"오류: {str(e)}"
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    for i in range(1, 3):
        log(f"==== 시도 {i}/2 ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        elif i == 2:
            send_telegram_message(f"🚨 최종 실패 알림\n{message}", "lotto_error.png")
        time.sleep(10)
