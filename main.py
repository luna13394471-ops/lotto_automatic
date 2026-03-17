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
    
    # PC 환경을 완벽히 흉내내기 위한 UA 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 봇 탐지 우회
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        wait = WebDriverWait(driver, 30)

        # 1. 로그인 (메인 도메인)
        print(f"로그인 시도 중... (ID: {ID})")
        driver.get("https://dhlottery.co.kr/login")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        # [중요] 로그인 후 쿠키가 브라우저에 완전히 구워질 때까지 넉넉히 대기
        time.sleep(10) 
        print("로그인 세션 안정화 완료.")

        # 2. 구매 서버로의 안전한 전환 (Referer 유지)
        print("구매 페이지로 이동 중...")
        # 직접 이동 대신 자바스크립트로 세션 정보를 물고 이동하도록 유도
        driver.execute_script("location.href='https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40'")
        time.sleep(10) # 게임 서버 세션 동기화 대기

        # 3. Iframe 전환 및 '시간 초과' 팝업 적극 대응
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            print("Iframe 진입 성공.")
            
            # 스크린샷에 뜬 팝업 처리: '확인' 버튼이 있는지 5초간 수색
            try:
                # 팝업의 '확인' 버튼을 찾아 클릭 (ID가 없으므로 텍스트와 클래스로 추적)
                popup_close_btn = driver.find_elements(By.XPATH, "//input[@value='확인' or @value='닫기']")
                if popup_close_btn and popup_close_btn[0].is_displayed():
                    print("세션 만료 팝업 감지! 닫기 버튼 클릭 중...")
                    driver.execute_script("arguments[0].click();", popup_close_btn[0])
                    time.sleep(3)
            except:
                print("세션 팝업이 발견되지 않았습니다. 계속 진행합니다.")
        else:
            raise Exception("구매 Iframe을 찾을 수 없습니다.")

        # 4. 자동번호발급 및 수량 선택
        # 버튼이 활성화될 때까지 기다림
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택 (amoundApply)
        amount_sel_el = wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))
        Select(amount_sel_el).select_by_value(str(NUMBER))
        
        # '확인' 버튼 클릭
        driver.find_element(By.ID, "btnSelectNum").click()
        print(f"{NUMBER}게임 선택 완료.")
        time.sleep(2)
        
        # 5. 구매하기 클릭 및 최종 승인
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # 최종 확인 팝업 버튼 (XPath)
        final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath)))
        driver.execute_script("arguments[0].click();", final_confirm_btn)

        # 6. 결과 검증 (성공 메시지 확인)
        time.sleep(5)
        if "완료" in driver.page_source or "구매내역" in driver.page_source:
            driver.save_screenshot("lotto_final_success.png")
            return True, f"✅ 로또 자동 구매 성공! ({NUMBER}게임)"
        else:
            driver.save_screenshot("lotto_result_fail.png")
            return False, "❌ 구매 후 결과 확인 실패 (예치금 부족 여부 확인 필요)"

    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("session_error_debug.png")
        return False, f"❌ 에러 발생: {str(e)}"
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    # 세션 오류 대응을 위해 최대 3번까지 재시도합니다.
    MAX_RETRIES = 3
    for i in range(1, MAX_RETRIES + 1):
        print(f"[{i}/{MAX_RETRIES}] 시도 중...")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_final_success.png")
            break
        else:
            if i == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패: {message}", "session_error_debug.png")
            else:
                print(f"실패하여 1분 후 다시 시도합니다... ({message})")
                time.sleep(60)
