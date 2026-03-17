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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"})
        
        wait = WebDriverWait(driver, 25)

        # 1. 로그인
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(5)

        # [핵심] 세션 동기화를 위한 예치금 페이지 경유
        print("세션 확인 및 예치금 체크 중...")
        driver.get("https://dhlottery.co.kr/userSsl.do?method=myPage")
        time.sleep(3)
        
        # 예치금 정보 읽기 (로그인 여부 확인용)
        try:
            cash_info = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".my_pay_area .total_pay, .cash"))).text
            print(f"현재 예치금 상태: {cash_info}")
            if "0" in cash_info and len(cash_info) < 5: # 예치금이 진짜 0원인 경우
                 print("예치금 부족 감지.")
        except:
            print("예치금 정보를 읽을 수 없습니다. (로그인 세션 불안정)")

        # 2. 구매 페이지 접속
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(7)

        # 3. Iframe 전환 및 팝업 체크
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            
            # [수정] 스크린샷의 "시간 초과" 레이어 팝업 확인 및 처리
            try:
                # 팝업 닫기 버튼 또는 확인 버튼 (보통 .btns input 또는 특정 ID)
                timeout_popup_btn = driver.find_elements(By.XPATH, "//input[@value='확인' or @value='닫기']")
                if timeout_popup_btn and timeout_popup_btn[0].is_displayed():
                    print("시간 초과 팝업 감지. 닫기 시도...")
                    driver.execute_script("arguments[0].click();", timeout_popup_btn[0])
                    time.sleep(2)
                    # 팝업 닫은 후 다시 구매 페이지 로드 시도
                    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
                    time.sleep(5)
                    driver.switch_to.frame(iframes[0])
            except:
                pass
        else:
            raise Exception("구매 Iframe 진입 실패")

        # 4. 자동번호발급 및 구매 로직
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        driver.find_element(By.ID, "btnSelectNum").click()
        
        # 5. 구매하기 클릭 및 최종 확인
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # 브라우저 Alert(예치금 부족 등) 확인
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            if "부족" in alert_text:
                driver.save_screenshot("no_money.png")
                return False, f"❌ 구매 실패: {alert_text}"
        except:
            pass

        # 최종 확인 팝업
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath))).click()
        
        time.sleep(3)
        # 결과 화면에 '영수증' 또는 '완료' 키워드 확인
        if "완료" in driver.page_source or "구매내역" in driver.page_source:
            driver.save_screenshot("lotto_success.png")
            return True, "✅ 로또 자동 구매 성공!"
        else:
            driver.save_screenshot("lotto_result_check.png")
            return False, "❌ 구매 완료 여부를 확인할 수 없습니다."

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("error_debug.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    success, message = run_lotto_purchase()
    # 실패 시 상황별 스크린샷 전송
    photo = "lotto_success.png" if success else "error_debug.png"
    if not success and os.path.exists("no_money.png"): photo = "no_money.png"
    
    send_telegram_message(message, photo)
