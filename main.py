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
    
    # 🚨 안정성을 위해 로드 전략을 다시 normal로 설정 (스크립트 꼬임 방지)
    chrome_options.page_load_strategy = 'normal'
    
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    
    # 봇 감지 우회
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
        
        wait = WebDriverWait(driver, 40)

        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        # 2. 세션 안착 (반드시 거쳐야 함)
        time.sleep(5)
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(3)

        # 3. 구매 페이지 이동
        print("구매 페이지 진입...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(10) # 전체 리소스 로딩 대기

        # 4. Iframe 전환 (정교하게 찾기)
        try:
            # URL에 LO40이 포함된 iframe을 찾음
            target_frame = wait.until(EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'LO40')]")))
            driver.switch_to.frame(target_frame)
            print("Iframe 진입 성공.")
        except:
            # 실패 시 첫 번째 iframe으로 백업
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])
            else:
                raise Exception("Iframe을 찾을 수 없습니다.")

        # [추가] 팝업 제거 (강력한 버전)
        driver.execute_script("""
            var popups = document.querySelectorAll('input[value="확인"], input[value="닫기"]');
            popups.forEach(p => p.click());
        """)
        time.sleep(2)

        # 5. 구매 로직
        # 자동번호발급 (num2)
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        # 선택 완료
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # 최종 확인 팝업 (XPath)
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath))).click()

        # 결과 확인
        time.sleep(5)
        driver.save_screenshot("lotto_final_result.png")
        
        if "완료" in driver.page_source or "구매내역" in driver.page_source:
            return True, "✅ 로또 자동 구매 성공!"
        else:
            return False, "구매 결과가 불분명합니다. 예치금을 확인하세요."

    except Exception as e:
        if driver: driver.save_screenshot("lotto_error.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    photo = "lotto_final_result.png" if success else "lotto_error.png"
    send_telegram_message(message, photo)
