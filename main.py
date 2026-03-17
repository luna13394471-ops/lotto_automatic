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

# ⭐ 환경 변수 설정
ID = os.environ.get("LOTTO_ID")
PASSWORD = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NUMBER = 1 # 구매 게임 수

def send_telegram_message(message: str, photo_path=None):
    """텔레그램 메시지 및 스크린샷 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload, timeout=10)
        if photo_path and os.path.exists(photo_path):
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def run_lotto_purchase():
    """로또 구매 메인 로직"""
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # PC 버전 유저 에이전트 고정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(options=chrome_options)
    
    # CDP 명령으로 Win32 플랫폼 고정 (모바일 리다이렉트 방지 핵심)
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent, "platform": "Win32"})
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    wait = WebDriverWait(driver, 30)
    
    try:
        if not ID or not PASSWORD:
            raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

        # 1. 로그인 단계
        print(f"로그인 페이지 접속 중... (ID: {ID})")
        driver.get("https://dhlottery.co.kr/login")
        time.sleep(random.uniform(2, 4))

        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(ID)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        
        # [중요] 로그인 후 세션 안착을 위한 메인 페이지 경유
        time.sleep(5)
        print("세션 안정화 중...")
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(3)

        # 2. 구매 페이지 이동
        print("구매 페이지 접속 시도...")
        driver.execute_script("location.href='https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40'")
        time.sleep(7)

        # 3. Iframe 전환 및 세션 만료 팝업 체크
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            print("Iframe 진입 성공.")
            
            # [추가] 스크린샷에 나온 '시간 초과' 팝업이 있는지 확인
            try:
                # 팝업의 확인 버튼을 찾아 클릭 시도
                timeout_btn = driver.find_elements(By.XPATH, "//input[@value='확인' or @value='닫기']")
                if timeout_btn and timeout_btn[0].is_displayed():
                    print("세션 만료 팝업 감지. 재시도가 필요합니다.")
                    driver.save_screenshot("session_timeout_debug.png")
                    return False, "세션 만료 팝업 발생"
            except:
                pass
        else:
            raise Exception("구매 Iframe을 찾을 수 없습니다.")

        # 4. 구매 로직 수행
        # 자동번호발급 버튼 클릭
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(NUMBER))
        
        # 확인 버튼
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기 버튼
        buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
        driver.execute_script("arguments[0].click();", buy_btn)
        
        # 최종 확인 팝업 (XPath)
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath)))
        driver.execute_script("arguments[0].click();", final_confirm_btn)

        time.sleep(3)
        driver.save_screenshot("success_result.png")
        return True, f"✅ 로또 자동 구매 성공! ({NUMBER}게임)"

    except Exception as e:
        driver.save_screenshot("error_capture.png")
        return False, f"❌ 오류 발생: {str(e)}"
    finally:
        driver.quit()

# --- 메인 실행부 (Retry 로직) ---
if __name__ == "__main__":
    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[{attempt}/{MAX_RETRIES}] 구매 시도 시작...")
        success, message = run_lotto_purchase()
        
        if success:
            print(message)
            send_telegram_message(message, "success_result.png")
            break
        else:
            print(f"실패: {message}")
            if attempt < MAX_RETRIES:
                wait_time = 60 * attempt # 실패할수록 대기 시간을 늘림
                print(f"{wait_time}초 후 다시 시도합니다.")
                time.sleep(wait_time)
            else:
                send_telegram_message(f"🚨 로또 자동 구매 최종 실패\n사유: {message}", "error_capture.png")
