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

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

number = 1 

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {msg}")

def send_telegram_message(message: str, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try: requests.post(url, data=payload, timeout=10)
    except: pass
    if photo_path and os.path.exists(photo_path):
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        try:
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

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15) # 요소를 기다리는 시간 단축 (빠른 실패 확인)
    
    try:
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        
        log("2. 로그인 정보 입력 및 클릭...")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        # 공지사항 팝업 등이 있다면 모두 닫기 (메인 페이지 방해 요소 제거)
        log("3. 메인 팝업 제거 및 세션 정리...")
        driver.get("https://dhlottery.co.kr/common.do?method=main") # 메인으로 재접속하여 세션 안정화
        time.sleep(2)
        driver.execute_script("const popups = document.querySelectorAll('.popupLayer'); popups.forEach(p => p.style.display='none');")

        log("4. 구매 페이지로 강제 이동...")
        purchase_url = "https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40"
        driver.get(purchase_url)
        time.sleep(5)

        log("5. Iframe 확인 중...")
        # 페이지 로딩이 완료될 때까지 대기
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        # 구매 페이지 접속 실패 시(메인으로 튕겼을 경우) 재시도
        if "TotalGame.jsp" not in driver.current_url:
            log("   ⚠️ 구매 페이지 접속 실패. 다시 시도합니다.")
            driver.get(purchase_url)
            time.sleep(5)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")

        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            log("   - Iframe 전환 성공")
        else:
            raise Exception("구매 화면(Iframe)을 찾을 수 없습니다.")
        
        log("6. 자동 번호 선택...")
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        
        log("7. 수량 선택 및 번호 선택...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(number))
        driver.find_element(By.ID, "btnSelectNum").click()
        
        log("8. 구매하기 버튼 클릭...")
        driver.find_element(By.ID, "btnBuy").click()
        
        log("9. 최종 확인 팝업 승인...")
        # '확인' 버튼이 뜰 때까지 대기 후 클릭
        final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]")))
        final_confirm_btn.click()
        
        log("10. 결과 화면 캡처 중...")
        # 결과 창(pop_content)이 나타날 때까지 대기
        try:
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            log("    ⚠️ 결과 팝업을 찾지 못했습니다. 스크린샷으로 확인합니다.")
            
        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 과정 성공!")
        return True, "✅ 로또 자동 구매 성공!"
        
    except Exception as e:
        log(f"❌ 에러 발생: {str(e)}")
        driver.save_screenshot("lotto_error.png")
        return False, f"❌ 오류 발생: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 2 # 총 시도 횟수를 줄여 전체 시간 단축
    attempt = 1
    while attempt <= MAX_RETRIES:
        log(f"==== 시도 {attempt}/{MAX_RETRIES} ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        else:
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
            else:
                log("10초 후 재시도...")
                time.sleep(10)
        attempt += 1
