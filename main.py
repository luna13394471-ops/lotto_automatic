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
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # 렌더러 타임아웃 방지를 위한 추가 옵션
    chrome_options.add_argument("--proxy-server='direct://'")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30) # 페이지 로드 최대 30초 제한
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 20)
        
        # 1. 로그인
        log("1. 로그인 시도...")
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        # 2. 구매 페이지 이동
        log("2. 구매 페이지 이동 및 안정화...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        
        # 3. Iframe 강제 탐색 (핵심 수정)
        log("3. 구매 창(Iframe) 찾는 중...")
        iframe_found = False
        for _ in range(10): # 최대 10초간 Iframe 발생 감시
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                # 로또 구매 창은 보통 특정 크기나 이름을 가짐
                if "answer" in iframe.get_attribute("id") or "answer" in iframe.get_attribute("name"):
                    driver.switch_to.frame(iframe)
                    iframe_found = True
                    log(f"   - Iframe 접속 성공 (Index: {i})")
                    break
            if iframe_found: break
            time.sleep(1)
        
        if not iframe_found:
            # ID로 못 찾으면 첫 번째 iframe으로 강제 시도
            if len(iframes) > 0:
                driver.switch_to.frame(0)
                log("   - ID 미매칭으로 첫 번째 Iframe 강제 전환")
            else:
                raise Exception("구매 페이지 내에 Iframe이 존재하지 않습니다.")

        # 4. 자동번호 및 수량 선택
        log("4. 번호 선택 처리...")
        # 자동선택 라디오 버튼 (JS로 강제 클릭)
        auto_radio = wait.until(EC.presence_of_element_located((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_radio)
        
        # 수량 선택
        amt_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amt_select.select_by_value("1")
        
        # 번호선택 완료 버튼
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 5. 구매하기
        log("5. 최종 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 6. 확인 팝업 (Alert 혹은 Layer)
        log("6. 승인 확인 중...")
        try:
            # 브라우저 Alert 확인
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            log("   - 브라우저 알림창 수락")
        except: pass

        # 레이어 팝업의 '확인' 버튼 클릭
        try:
            final_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", final_ok)
        except: 
            log("   - 레이어 팝업 미감지 (이미 처리됨)")

        # 7. 성공 스크린샷 (대기 시간 최적화)
        log("7. 결과 화면 대기 및 캡처...")
        try:
            # 결과창(pop_content)이 나타날 때까지 최대 15초 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            log("   - 결과 레이어 미표시 (강제 캡처)")

        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 과정 완료!")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류: {str(e)}")
        if driver:
            # 차단 여부 확인을 위해 현재 URL과 제목 로그 추가
            log(f"   - 현재 URL: {driver.current_url}")
            driver.save_screenshot("lotto_error.png")
        return False, f"오류 발생: {str(e)}"
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
