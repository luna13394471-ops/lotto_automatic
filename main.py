import os
import time
import requests
import random
import datetime
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

def log(msg):
    """타임스탬프를 포함한 로그 출력"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}")

def send_telegram_message(message: str, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}, timeout=10)
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
    
    # [강화] CI 환경에서 브라우저 멈춤 방지 옵션
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad") # 크래시 로그 생성 방지
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = None
    try:
        log("ChromeDriver 설치 및 실행 시도...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 브라우저 응답 타임아웃 설정
        driver.set_page_load_timeout(40)
        
        log("로그인 페이지 접속 중...")
        driver.get("https://dhlottery.co.kr/login")
        
        wait = WebDriverWait(driver, 20)
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        
        log("로그인 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        time.sleep(5)
        log("세션 안정화 (메인 페이지 경유)...")
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(3)

        log("구매 서버 이동 중...")
        driver.execute_script("location.href='https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40'")
        time.sleep(7)

        log("Iframe 탐색 중...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            log("Iframe 진입 성공. 팝업 체크...")
            
            # 세션 만료 팝업 즉시 대응
            timeout_popups = driver.find_elements(By.XPATH, "//input[@value='확인' or @value='닫기']")
            if timeout_popups and timeout_popups[0].is_displayed():
                log("세션 팝업 감지됨. 닫기 시도...")
                driver.execute_script("arguments[0].click();", timeout_popups[0])
                time.sleep(2)
        else:
            raise Exception("Iframe이 없습니다.")

        log("자동번호발급 선택...")
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        log("수량 선택 및 번호 확인...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(NUMBER))
        driver.find_element(By.ID, "btnSelectNum").click()
        
        log("구매하기 클릭...")
        driver.find_element(By.ID, "btnBuy").click()
        
        # 최종 확인 (Alert 차단 가능성 대비)
        log("최종 확인 팝업 처리...")
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath))).click()

        time.sleep(3)
        driver.save_screenshot("final_result.png")
        log("구매 완료!")
        return True, "✅ 로또 구매 성공!"

    except Exception as e:
        log(f"에러 발생 지점: {driver.current_url if driver else 'N/A'}")
        log(f"에러 메시지: {str(e)}")
        if driver:
            driver.save_screenshot("error_step.png")
        return False, str(e)
    finally:
        if driver:
            log("브라우저 종료.")
            driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 2 # 6분 지연 방지를 위해 재시도 횟수를 줄임
    for attempt in range(1, MAX_RETRIES + 1):
        log(f"==== [{attempt}/{MAX_RETRIES}] 차 시도 시작 ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "final_result.png")
            break
        else:
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패 알림\n사유: {message}", "error_step.png")
            else:
                log("30초 후 재시도합니다...")
                time.sleep(30)
