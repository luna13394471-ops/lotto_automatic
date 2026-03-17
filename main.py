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
    """시간과 함께 로그 출력"""
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
    chrome_options.add_argument("--disable-gpu") # 가속 비활성화 (지연 방지)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(options=chrome_options)
    # 대기 시간을 10초로 단축 (어디서 멈추는지 빨리 확인하기 위함)
    wait = WebDriverWait(driver, 10) 
    
    try:
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login")
        
        log("2. 로그인 정보 입력 중...")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        
        log("3. 로그인 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        # 로그인 성공 여부 간단 체크
        if "login" in driver.current_url.lower():
            log("   ⚠️ 아직 로그인 페이지입니다. 차단되었을 가능성이 있습니다.")
            driver.save_screenshot("check_login_failed.png")

        log("4. 구매 페이지 이동...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        log("5. Iframe 확인 및 전환...")
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            log("   - Iframe 전환 완료")
        
        log("6. 자동 번호 선택...")
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        
        log("7. 수량 선택 및 번호 선택 버튼 클릭...")
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(number))
        driver.find_element(By.ID, "btnSelectNum").click()
        
        log("8. 구매 버튼 클릭...")
        driver.find_element(By.ID, "btnBuy").click()
        
        log("9. 최종 확인 팝업 승인...")
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath))).click()
        
        log("10. 결과 대기 및 스크린샷...")
        try:
            # 결과 창이 뜰 때까지 최대 5초만 대기
            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "pop_content")))
        except:
            log("    ⚠️ 결과 팝업 요소를 찾지 못했습니다. (이미 구매되었거나 오류)")
            
        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 프로세스 종료!")
        
        return True, "✅ 로또 자동 구매 성공!"
        
    except Exception as e:
        log(f"❌ 에러 발생: {str(e)}")
        driver.save_screenshot("lotto_error.png")
        return False, f"❌ 오류 위치 확인 필요: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    # 실행 속도를 위해 재시도 횟수를 2회로 줄임
    MAX_RETRIES = 2
    attempt = 1
    
    while attempt <= MAX_RETRIES:
        log(f"==== 시도 {attempt}/{MAX_RETRIES} ====")
        success, message = run_lotto_purchase()
        
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        else:
            log(f"결과: {message}")
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
            else:
                log("5초 후 재시도...")
                time.sleep(5)
        attempt += 1
