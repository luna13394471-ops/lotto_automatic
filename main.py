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
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException

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
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = None
    try:
        log("0. 드라이버 최신화 및 실행")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 30) # 대기 시간을 넉넉히 30초로 설정
        
        # 1. 로그인
        log("1. 로그인 시도 중...")
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        # 2. 구매 페이지 이동
        log("2. 구매 페이지로 이동...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 3. Iframe 전환 (안전한 방식)
        log("3. 구매 Iframe 접속 중...")
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 4. 자동번호발급 및 수량 선택
        log("4. 번호 선택 로직 실행...")
        # '자동번호발급' 라디오 버튼 클릭
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 1개 선택
        select_amt = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        select_amt.select_by_value("1")
        
        # '번호선택' 버튼 클릭
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 5. 구매하기 클릭
        log("5. 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 6. 최종 확인 팝업 (Layer 팝업 처리)
        log("6. 최종 승인 팝업 처리...")
        try:
            # 브라우저 알림창(Alert)이 뜰 경우 자동 수락 (예: 이미 구매함 등)
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            log(f"   - 알림창 감지 및 닫기: {alert_text}")
        except:
            pass
            
        # 실제 '확인' 버튼 클릭
        final_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
        driver.execute_script("arguments[0].click();", final_ok)
        
        # 7. 성공 스크린샷 (수정된 핵심 로직)
        log("7. 구매 결과 확인 및 성공 캡처...")
        try:
            # 구매 결과 레이어(pop_content)가 나타날 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) # 애니메이션 안정화
            log("   - 성공 화면 감지 완료")
        except TimeoutException:
            log("   - 성공 팝업 대기 중 타임아웃 (이미지 우선 저장)")
            
        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 성공!"
        
    except UnexpectedAlertPresentException as e:
        log(f"🚨 예상치 못한 알림창 발생: {e.alert_text}")
        driver.save_screenshot("lotto_error.png")
        return False, f"차단 알림: {e.alert_text}"
    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver:
            driver.save_screenshot("lotto_error.png")
        return False, f"오류: {str(e)}"
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 2
    for attempt in range(1, MAX_RETRIES + 1):
        log(f"==== [{attempt}/{MAX_RETRIES}] 로또 구매 시도 ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        elif attempt == MAX_RETRIES:
            send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
        time.sleep(5)
