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
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

number = 1 

def send_telegram_message(message: str, is_success: bool):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    icon = "✅ 성공" if is_success else "❌ 실패"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': f"{icon} 로또 알림\n{message}"}
    try: requests.post(url, data=payload, timeout=5)
    except: pass

# --- 1. 브라우저 보안 우회 설정 강화 ---
chrome_options = Options()
chrome_options.add_argument("--headless") # 실제 작동 확인 시에는 주석 처리 권장
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled") # 자동화 제어 플래그 비활성화
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# 실제 PC처럼 보이기 위한 고정 User-Agent (최신 버전으로 업데이트)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# WebDriver 속성 제거 스크립트 (중요)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """
})

wait = WebDriverWait(driver, 25) # 대기 시간을 더 늘림

try:
    if not id or not password:
        raise ValueError("ID/PW 환경변수가 설정되지 않았습니다.")

    # --- 2. 로그인 단계 ---
    # 메인 페이지를 거쳐서 쿠키를 생성한 후 로그인으로 이동
    print("메인 페이지 접속 중...")
    driver.get("https://dhlottery.co.kr/common.do?method=main")
    time.sleep(random.uniform(2, 4))
    
    print(f"로그인 페이지로 이동 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/user.do?method=login")
    time.sleep(3)

    # 현재 URL 확인 (디버깅용)
    print(f"현재 URL: {driver.current_url}")

    # 아이디 입력 필드 (여러 선택자를 시도)
    try:
        # PC용 ID: inpUserId, 모바일용 ID: userId
        user_id_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#inpUserId, #userId")))
        user_id_field.send_keys(id)
        
        password_field = driver.find_element(By.CSS_SELECTOR, "#inpUserPswdEncn, input[type='password']")
        password_field.send_keys(password)
        
        # 로그인 버튼
        login_btn = driver.find_element(By.CSS_SELECTOR, "#btnLogin, .btn_login")
        driver.execute_script("arguments[0].click();", login_btn)
    except Exception as e:
        # 요소를 못 찾으면 페이지 소스 일부 출력 (디버깅용)
        print("로그인 요소를 찾지 못했습니다. 페이지가 차단되었거나 대기열일 수 있습니다.")
        raise e

    time.sleep(5) # 로그인 처리 충분히 대기
    
    # --- 3. 구매 페이지 이동 ---
    print("구매 페이지 접속 시도...")
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    time.sleep(5)

    # Iframe 전환
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 진입 완료.")
    except:
        # 모바일 리다이렉트 시 Iframe이 없을 수 있음
        if "m.dhlottery" in driver.current_url:
            raise Exception("모바일 페이지로 리다이렉트되어 구매를 진행할 수 없습니다. (헤드리스 차단)")
        print("Iframe 없음. 메인에서 진행.")

    # --- 4. 구매 로직 수행 ---
    # 자동번호발급 버튼
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 설정
    amount_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_select.select_by_value(str(number))
    
    # 선택 완료(확인)
    driver.find_element(By.ID, "btnSelectNum").click()
    time.sleep(1)
    
    # 구매하기 버튼
    driver.find_element(By.ID, "btnBuy").click()
    time.sleep(1)

    # 최종 확인 팝업 (가장 확실한 XPath 사용)
    final_confirm = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]")))
    driver.execute_script("arguments[0].click();", final_confirm)

    msg = f"로또 구매 성공! ({number}게임)"
    print(msg)
    send_telegram_message(msg, True)

except Exception as e:
    error_msg = f"에러 발생: {str(e)}\n현재 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("lotto_debug.png") # 스크린샷 필수 확인
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
