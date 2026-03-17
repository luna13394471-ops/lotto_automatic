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
    chrome_options.add_argument("--headless=new") # 최신 헤드리스 모드 사용
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # --- [렌더러 타임아웃 해결을 위한 끝판왕 옵션] ---
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor") # 렌더링 가속 기능 강제 종료
    chrome_options.add_argument("--disable-renderer-backgrounding") # 렌더러 백그라운드 처리 방지
    chrome_options.add_argument("--force-device-scale-factor=1") # 화면 배율 고정
    chrome_options.page_load_strategy = 'none' # 페이지가 다 로드되지 않아도 즉시 제어권 획득
    # --------------------------------------------
    
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = None
    try:
        log("0. 드라이버 최신 버전 강제 매칭 중...")
        # 146 버전에 맞는 드라이버를 경로와 함께 명시적으로 지정
        driver_path = ChromeDriverManager().install()
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 렌더러 타임아웃을 방지하기 위해 대기 시간을 넉넉히 설정
        wait = WebDriverWait(driver, 30)
        
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        time.sleep(5) # page_load_strategy='none'이므로 수동 대기 추가

        log("2. 로그인 정보 입력...")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(5)

        log("3. 구매 페이지 이동...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(7)

        log("4. Iframe 전환...")
        # Iframe이 존재할 때까지 기다린 후 전환
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        
        log("5. 자동 번호 선택 및 구매...")
        # 자동선택 버튼 (ID가 나타날 때까지 대기)
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        
        # 수량 1개 선택
        amt_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amt_select.select_by_value("1")
        
        # 번호선택 완료 버튼
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기 버튼
        driver.find_element(By.ID, "btnBuy").click()
        
        log("6. 최종 확인 팝업 승인...")
        # 확인 버튼이 나타날 때까지 대기 후 클릭
        confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
        confirm_btn.click()
        
        log("7. 성공 결과 대기 및 스크린샷...")
        # 결과 창(pop_content)이 뜰 때까지 최대 10초 대기
        try:
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) # 결과 창 애니메이션 대기
        except:
            log("결과 창을 찾을 수 없어 현재 화면을 찍습니다.")
            
        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 과정 성공!")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 에러 발생: {str(e)}")
        if driver:
            driver.save_screenshot("lotto_error.png")
        return False, f"실행 오류: {str(e)}"
    finally:
        if driver:
            driver.quit()

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
