import os
import time
import requests
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
# 버전 불일치 해결을 위한 추가 임포트
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

number = 1 

def send_telegram_message(message: str, photo_path=None):
    """텔레그램 메시지 및 스크린샷 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    
    # 1. 텍스트 메시지 전송
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

    # 2. 스크린샷이 있으면 전송 (시각적 확인용)
    if photo_path and os.path.exists(photo_path):
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
        except: pass

def run_lotto_purchase():
    """실제 로또 구매 메인 로직"""
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    # ChromeDriver 버전을 자동으로 관리하도록 수정된 부분
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"})
    
    wait = WebDriverWait(driver, 30)
    
    try:
        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(5)

        # 2. 구매 페이지 이동
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(7)

        # 3. Iframe 전환
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
        
        # 4. 자동번호발급 및 수량 선택
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(number))
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 5. 구매하기
        driver.find_element(By.ID, "btnBuy").click()
        
        # 6. 최종 확인 팝업
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath))).click()
        
        # 7. 성공 스크린샷 저장 (수정된 로직)
        try:
            # 구매 완료 레이어(pop_content)가 뜰 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1) # 화면 안정화 대기
        except:
            time.sleep(3) # 요소를 찾지 못할 경우 기본 대기
            
        driver.save_screenshot("lotto_result.png")
        
        return True, "✅ 로또 자동 구매 성공!"
        
    except Exception as e:
        driver.save_screenshot("lotto_error.png")
        return False, f"❌ 구매 중 오류 발생: {str(e)}"
    finally:
        driver.quit()

# --- 메인 실행부 (재시도 로직 포함) ---
if __name__ == "__main__":
    MAX_RETRIES = 3
    attempt = 1
    success = False
    
    while attempt <= MAX_RETRIES:
        print(f"[{attempt}/{MAX_RETRIES}] 로또 구매 시도 중...")
        success, message = run_lotto_purchase()
        
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        else:
            print(f"시도 실패: {message}")
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패 알림\n{message}", "lotto_error.png")
            else:
                time.sleep(60) # 1분 후 재시도
        attempt += 1
