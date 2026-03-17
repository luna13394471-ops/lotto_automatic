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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def log(msg):
    now = datetime.now().strftime('%H:%M:%S')
    print(f"[{now}] {msg}")

def send_telegram_message(message: str, photo_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      data={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", 
                              data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo}, timeout=20)
    except: pass

def get_driver():
    chrome_options = Options()
    # 렌더러 타임아웃 및 메모리 부족 해결을 위한 최적화 옵션
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 모바일 리다이렉트 방지를 위해 완벽한 PC용 User-Agent 설정
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    # 자동화 탐지 방지
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 렌더러 타임아웃 방지를 위한 타임아웃 확장
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    return driver

def run_lotto_purchase():
    driver = None
    try:
        driver = get_driver()
        wait = WebDriverWait(driver, 25)
        
        # 1. 로그인 (PC 메인으로 접속 시도)
        log("1. 로그인 페이지 접속...")
        driver.get("https://dhlottery.co.kr/login.do?method=login")
        
        # 모바일로 리다이렉트 되었는지 체크 및 강제 복귀
        if "m.dhlottery" in driver.current_url:
            log("   ⚠️ 모바일 감지됨. PC 버전으로 강제 전환 시도...")
            driver.get("https://dhlottery.co.kr/common.do?method=main")
            time.sleep(2)
            driver.get("https://dhlottery.co.kr/login.do?method=login")

        log("2. 로그인 정보 입력...")
        wait.until(EC.presence_of_element_located((By.ID, "inpUserId"))).send_keys(id)
        driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnLogin"))
        time.sleep(5)

        # 3. 구매 페이지 이동
        log("3. 구매 페이지 이동...")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(5)

        # 4. Iframe 전환
        log("4. Iframe 탐색 및 전환...")
        # 페이지 로딩 대기 후 iframe 확인
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        target_frame = None
        for frame in iframes:
            fid = frame.get_attribute("id")
            if fid and "ifrm_answer" in fid:
                target_frame = frame
                break
        
        if target_frame:
            driver.switch_to.frame(target_frame)
            log("   - 지정된 Iframe 접속 성공")
        else:
            driver.switch_to.frame(0)
            log("   - 기본 Iframe(0) 강제 전환")

        # 5. 번호 선택 로직 (JS 클릭 사용으로 안정성 확보)
        log("5. 자동 번호 선택 처리...")
        auto_btn = wait.until(EC.presence_of_element_located((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택 (1개)
        amt_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amt_select.select_by_value("1")
        
        # 번호선택 완료 클릭
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnSelectNum"))
        time.sleep(1)
        
        # 6. 구매하기 버튼 클릭
        log("6. 최종 구매 버튼 클릭...")
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnBuy"))
        
        # 7. 확인 팝업 승인
        log("7. 승인 확인 중...")
        try:
            # 브라우저 Alert 대기 및 수락
            WebDriverWait(driver, 5).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
            log("   - Alert 창 수락 완료")
        except: pass

        # 레이어 팝업의 '확인' 버튼 클릭
        try:
            confirm_ok = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인']")))
            driver.execute_script("arguments[0].click();", confirm_ok)
        except: pass

        # 8. 성공 스크린샷 (요청하신 부분)
        log("8. 결과 화면 대기 및 캡처...")
        try:
            # 성공 팝업(pop_content)이 나타날 때까지 대기
            wait.until(EC.visibility_of_element_located((By.ID, "pop_content")))
            time.sleep(2) 
        except:
            log("   - 결과 팝업 미탐지 (현재 화면 캡처 진행)")

        driver.save_screenshot("lotto_result.png")
        log("🎉 모든 과정 완료!")
        return True, "✅ 로또 자동 구매 성공!"

    except Exception as e:
        log(f"❌ 오류 발생: {str(e)}")
        if driver:
            log(f"   - 최종 URL: {driver.current_url}")
            driver.save_screenshot("lotto_error.png")
        return False, f"실행 오류: {str(e)}"
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    for i in range(1, 3):
        log(f"==== 시도 {i}/2 ====")
        success, message = run_lotto_purchase()
        if success:
            send_telegram_message(message, "lotto_result.png")
            break
        elif i == 2:
            send_telegram_message(f"🚨 최종 실패 알림\n{message}", "lotto_error.png")
        time.sleep(5)
