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
from selenium.webdriver.chrome.service import Service
# ⭐ 드라이버 자동 관리를 위한 라이브러리
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수 설정
ID = os.environ.get("LOTTO_ID")
PASSWORD = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NUMBER = 1 

def send_telegram_message(message: str, photo_path=None):
    """텔레그램 알림 및 스크린샷 전송"""
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
    chrome_options.add_argument("--disable-gpu") # 스크린샷 깨짐 방지
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        # ⭐ [핵심 수정] ChromeDriver를 현재 크롬 버전에 맞춰 자동 설치 및 실행
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 브라우저 제어 타임아웃 설정 (Read timed out 방지)
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(60)
        
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        wait = WebDriverWait(driver, 40) # 대기 시간 강화
        
        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        # 세션 안착 대기
        time.sleep(5)
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(3)

        # 2. 구매 페이지 이동
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        print("구매 페이지 로딩 대기 중...")
        time.sleep(10) # 게임 엔진 로딩을 위해 넉넉히 대기

        # 3. Iframe 전환
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            print("Iframe 진입 성공.")
        else:
            raise Exception("구매 Iframe을 찾을 수 없습니다.")

        # 4. 구매 로직 (자동번호발급 -> 수량 -> 확인 -> 구매)
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(2)
        
        driver.find_element(By.ID, "btnBuy").click()
        
        # 최종 확인 팝업 (XPath)
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath))).click()

        time.sleep(3)
        driver.save_screenshot("lotto_success.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("lotto_error_capture.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if 'driver' in locals():
            driver.quit()

# --- 실행부 (재시도 로직) ---
if __name__ == "__main__":
    MAX_RETRIES = 2 # 버전 이슈 해결 후이므로 재시도 횟수 조정
    for attempt in range(1, MAX_RETRIES + 1):
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_success.png")
            break
        else:
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패 알림\n사유: {message}", "lotto_error_capture.png")
            else:
                time.sleep(30)
