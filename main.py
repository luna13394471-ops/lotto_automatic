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
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

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
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        wait = WebDriverWait(driver, 30)
        
        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        time.sleep(5)
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(3)

        # 2. 구매 페이지 이동
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(7)

        # 3. Iframe 전환
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
        else:
            raise Exception("구매 Iframe을 찾을 수 없습니다.")

        # 4. 자동번호발급 및 수량 선택
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 5. 구매하기 클릭 및 예치금 체크
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # [중요] 예치금 부족 시 나타나는 Alert 체크
        try:
            alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            alert.accept() # 확인 버튼 클릭
            if "부족" in alert_text:
                driver.save_screenshot("insufficient_funds.png")
                return False, f"❌ 구매 실패 (예치금 부족): {alert_text}"
        except:
            pass # Alert이 없으면 정상 진행

        # 6. 최종 확인 팝업
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath))).click()

        # [중요] 실제 구매 결과 확인 대기
        time.sleep(5) # 결과 처리 대기
        
        # 결과 화면에 성공 메시지가 있는지 확인 (예: '정상적으로 처리되었습니다')
        # 보통 구매 후에는 #report 확인 레이어가 뜸
        try:
            result_msg = wait.until(EC.presence_of_element_located((By.ID, "pop_receipt"))).text
            if "구매가 완료되었습니다" in result_msg or "총 결제금액" in result_msg:
                driver.save_screenshot("success_result.png")
                return True, f"✅ 로또 자동 구매 성공! ({NUMBER}게임)"
            else:
                driver.save_screenshot("unknown_result.png")
                return False, "❌ 구매 성공 여부 불확실 (결과 메시지 미확인)"
        except:
            driver.save_screenshot("result_timeout.png")
            return False, "❌ 구매 후 결과 화면을 찾을 수 없습니다."

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("error_capture.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    photo = "success_result.png" if success else "error_capture.png"
    if not os.path.exists(photo):
        # 실패 상황에 따라 스크린샷 이름이 다를 수 있으므로 체크
        for f in ["insufficient_funds.png", "unknown_result.png", "result_timeout.png"]:
            if os.path.exists(f): photo = f; break
            
    send_telegram_message(message, photo)
