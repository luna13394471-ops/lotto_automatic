import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

number = 1 

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

    # Selenium 4.6+ 내장 매니저 사용 (자동으로 최적 드라이버 매칭)
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20) # 대기 시간을 20초로 약간 조정
    
    try:
        print("1. 로그인 페이지 접속 중...")
        driver.get("https://dhlottery.co.kr/login")
        
        print("2. 아이디/비밀번호 입력 중...")
        wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(3)

        print("3. 구매 페이지 이동 중...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        print("4. Iframe 전환 시도...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])
            print("   - Iframe 전환 완료")
        
        print("5. 자동 번호 및 수량 선택 중...")
        wait.until(EC.element_to_be_clickable((By.ID, "num2"))).click()
        Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))).select_by_value(str(number))
        driver.find_element(By.ID, "btnSelectNum").click()
        
        print("6. 구매 버튼 클릭...")
        driver.find_element(By.ID, "btnBuy").click()
        
        print("7. 최종 확인 팝업 승인 중...")
        final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath))).click()
        
        print("8. 구매 결과 확인 및 스크린샷 저장 중...")
        try:
            # 결과 팝업이 나타날 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(1)
        except:
            print("   - 결과 팝업 대기 타임아웃 (강제 진행)")
            
        driver.save_screenshot("lotto_result.png")
        print("9. 모든 프로세스 완료!")
        
        return True, "✅ 로또 자동 구매 성공!"
        
    except Exception as e:
        print(f"❗ 오류 발생 위치 확인: {str(e)}")
        driver.save_screenshot("lotto_error.png")
        return False, f"❌ 구매 중 오류 발생: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    MAX_RETRIES = 3
    attempt = 1
    
    while attempt <= MAX_RETRIES:
        print(f"\n==== [{attempt}/{MAX_RETRIES}] 구매 시도 시작 ====")
        success, message = run_lotto_purchase()
        
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        else:
            print(f"   - 시도 실패: {message}")
            if attempt == MAX_RETRIES:
                send_telegram_message(f"🚨 최종 실패\n{message}", "lotto_error.png")
            else:
                print("   - 10초 후 재시도합니다...")
                time.sleep(10) # 재시도 간격 단축
        attempt += 1
