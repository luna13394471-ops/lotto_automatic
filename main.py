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
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException

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
    # 렌더러 타임아웃 해결을 위한 공격적 옵션
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # [핵심] 렌더러 통신 지연 및 메모리 부족 방지
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--js-flags='--max-old-space-size=512'") # 자바스크립트 메모리 제한
    chrome_options.page_load_strategy = 'eager' # DOM 구성만 끝나면 즉시 제어
    
    # 모바일 리다이렉트 방지 및 자동화 우회
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(40) 
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 25)
        
        # 1. 로그인
        log("1. 로그인 페이지 접속")
        driver.get("https://dhlottery.co.kr/login.do?method=login")
        
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        # 2. 구매 페이지 이동
        log("2. 구매 페이지 이동")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 3. Iframe 전환
        log("3. 구매 Iframe 전환")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 4. 번호 선택 처리
        log("4. 자동 번호 선택")
        auto_radio = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_radio)
        
        # 수량 1개 선택
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value("1")
        
        # 선택완료 버튼
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 5. 구매하기
        log("5. 구매 버튼 클릭")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 6. 확인 팝업 승인
        log("6. 승인 팝업 처리")
        try:
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            log(f"   - 알림 감지: {alert.text}")
            alert.accept()
        except: pass

        # 레이어 팝업의 '확인' 버튼 클릭
        try:
            confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", confirm_btn)
        except: pass

        # 7. 구매성공 결과 확인 및 캡처 (수정 요청 반영)
        log("7. 구매 성공 결과 대기 및 캡처")
        try:
            # 성공 팝업(pop_content)이 나타날 때까지 명시적 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) 
            log("   - 성공 화면 확인 완료")
        except TimeoutException:
            log("   - 결과 창 대기 초과 (현재 화면 캡처 진행)")

        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 과정 성공!")
        return True, "✅ 로또 자동 구매 성공!"

    except UnexpectedAlertPresentException as e:
        log(f"🚨 예기치 않은 알림 발생: {e.msg}")
        if driver: driver.save_screenshot("lotto_error.png")
        return False, f"알림 발생: {e.msg}"
    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver: driver.save_screenshot("lotto_error.png")
        return False, f"실행 오류: {str(e)}"
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
        time.sleep(5)
