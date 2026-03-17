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

# ⭐ 환경 변수 설정
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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # [추가] 렌더링 안정성 강화 옵션
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--high-dpi-support=1")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
        
        wait = WebDriverWait(driver, 30)

        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(5)

        # 2. 로또 전용 구매 페이지로 직접 이동 (더 안정적인 URL)
        print("로또 전용 구매 페이지 접속 중...")
        driver.get("https://ol.dhlottery.co.kr/olotto/game/game645.do")
        time.sleep(10)

        # 3. Iframe 탐색 및 재시도 로직 (핵심)
        success_frame = False
        for attempt in range(5):
            try:
                print(f"Iframe 탐색 시도 중... ({attempt+1}/5)")
                # 이 페이지는 보통 Iframe이 없거나 'ifrm_answer'를 사용함
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    driver.switch_to.frame(iframes[0])
                
                # 자동번호발급 버튼이 로드되었는지 확인
                wait.until(EC.presence_of_element_located((By.ID, "num2")))
                success_frame = True
                print("구매 엔진 로드 완료.")
                break
            except:
                print("엔진 로드 대기 중...")
                driver.switch_to.default_content()
                time.sleep(5)

        if not success_frame:
            raise Exception("구매 엔진(Iframe)을 끝내 로드하지 못했습니다.")

        # 4. 구매 로직
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기 클릭 전 예치금 부족 Alert 체크
        driver.find_element(By.ID, "btnBuy").click()
        
        try:
            alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept()
            return False, f"❌ 구매 실패: {alert_text}"
        except:
            pass

        # 최종 확인 팝업
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath))).click()

        time.sleep(5)
        driver.save_screenshot("lotto_result.png")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        if driver: driver.save_screenshot("lotto_error.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    photo = "lotto_result.png" if success else "lotto_error.png"
    send_telegram_message(message, photo)
