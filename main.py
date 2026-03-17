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
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수
ID = os.environ.get("LOTTO_ID")
PASSWORD = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NUMBER = 1 

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
    
    # 🚨 [가장 중요] 페이지 로드 전략을 'eager'로 설정 (이미지/광고 무시하고 HTML만 뜨면 바로 진행)
    chrome_options.page_load_strategy = 'eager'
    
    # 기본 최적화 옵션
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # [렌더러 타임아웃 방지 옵션 강화]
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--proxy-server='direct://'")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # 이미지 로딩 안 함 (속도 향상)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 렌더러 응답 대기 시간 설정
        driver.set_page_load_timeout(30)
        
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        wait = WebDriverWait(driver, 20)

        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        time.sleep(3)
        # 세션 안정화를 위해 메인 이동
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(2)

        # 2. 구매 서버 이동
        driver.execute_script("location.href='https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40'")
        time.sleep(5)

        # 3. Iframe 전환
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # 팝업 체크 (간소화)
            try:
                popups = driver.find_elements(By.XPATH, "//input[@value='확인']")
                if popups: driver.execute_script("arguments[0].click();", popups[0])
            except: pass
        else:
            raise Exception("Iframe 탐색 실패")

        # 4. 자동발급 및 구매
        # eager 모드이므로 버튼이 나타날 때까지 명시적으로 기다려야 함
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        driver.find_element(By.ID, "btnSelectNum").click()
        
        # 구매하기 및 최종 확인
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # 최종 확인 팝업 (XPath)
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath))).click()

        time.sleep(3)
        driver.save_screenshot("success.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        if driver: driver.save_screenshot("error.png")
        return False, str(e)
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    photo = "success.png" if success else "error.png"
    send_telegram_message(message, photo)
