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
    
    # --- [추가] 렌더러 타임아웃 해결을 위한 핵심 옵션 ---
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.page_load_strategy = 'eager' # HTML 분석이 끝나면 즉시 진행 (이미지 로딩 안 기다림)
    # -----------------------------------------------
    
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    try:
        log("0. 드라이버 설치 및 브라우저 시작...")
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 브라우저 자체 응답 대기 시간 설정
        driver.set_page_load_timeout(30)
        wait = WebDriverWait(driver, 20)
        
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        
        log("2. 로그인 정보 입력 중...")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        log("3. 구매 페이지 이동...")
        # URL 직접 이동 시도
        driver.execute_script("location.href='https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40';")
        time.sleep(5)

        log("4. Iframe 전환...")
        # Iframe이 로드될 때까지 명시적 대기
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        
        log("5. 번호 선택 및 구매 시도...")
        # 자동선택 클릭
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        # 수량 선택 (1개)
        Select(driver.find_element(By.ID, "amoundApply")).select_by_value("1")
        # 선택완료 버튼
        driver.find_element(By.ID, "btnSelectNum").click()
        # 구매하기 버튼
        driver.find_element(By.ID, "btnBuy").click()
        
        log("6. 최종 확인 팝업 승인...")
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
        confirm_btn.click()
        
        log("7. 성공 결과 확인 및 스크린샷...")
        try:
            # 결과 창이 뜰 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            log("결과 창을 찾을 수 없어 현재 상태를 저장합니다.")
            
        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        try:
            # 에러 발생 시 현재 화면을 찍어 원인 파악
            driver.save_screenshot("lotto_error.png")
        except:
            pass
        return False, f"실행 오류: {str(e)}"
    finally:
        try:
            driver.quit()
        except:
            pass

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
