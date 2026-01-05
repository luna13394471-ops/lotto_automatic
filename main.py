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

# ⭐ 환경 변수(GitHub Secrets) 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 구매 게임 수 (1~5)
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """텔레그램 알림 전송 함수"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    icon = "✅ 성공" if is_success else "❌ 실패"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': f"{icon} 로또 알림\n{message}"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

# --- Chrome 브라우저 및 보안 우회 설정 ---
chrome_options = Options()
chrome_options.add_argument("--headless") # GitHub Actions 등 서버 환경 필수
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# 자동화 감지 우회 설정
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# 실제 PC 유저 에이전트 (봇 차단 방지)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# WebDriver 탐지 속성 제거
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

wait = WebDriverWait(driver, 25)

try:
    if not id or not password:
        raise ValueError("ID 또는 Password 환경 변수가 설정되지 않았습니다.")

    # 1. 메인 페이지 접속
    print("메인 페이지 접속 중...")
    driver.get("https://dhlottery.co.kr/main")
    time.sleep(random.uniform(3, 5))

    # 2. 메인 페이지의 로그인 버튼 클릭 (Referer 생성을 위해 중요)
    print("메인 화면 로그인 버튼(loginBtn) 클릭 시도...")
    main_login_btn = wait.until(EC.element_to_be_clickable((By.ID, "loginBtn")))
    driver.execute_script("arguments[0].click();", main_login_btn)
    time.sleep(random.uniform(2, 4))

    # 차단 여부 체크
    if "errorPage" in driver.current_url:
        print(f"!!! 차단 감지 !!! 현재 URL: {driver.current_url}")
        driver.save_screenshot("block_debug.png")
        raise Exception("동행복권 보안망(WAF)이 현재 접속을 차단했습니다.")

    # 3. 로그인 정보 입력
    print(f"로그인 시도 중... (ID: {id})")
    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    # 로그인 폼 내 확인 버튼 클릭
    login_execute_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_execute_btn)
    time.sleep(5) 

    # 4. 로또 구매 페이지 이동
    print("구매 페이지 접속 시도...")
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    time.sleep(random.uniform(4, 6))

    # 5. Iframe 전환 (구매 컨텐츠는 iframe 내부에 있음)
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 내 컨텐츠 접근 성공.")
    except:
        print("Iframe 전환 실패. 메인 프레임에서 계속 시도합니다.")

    # 6. 자동번호발급 및 구매 로직
    # 자동번호발급 버튼 (id="num2")
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 선택 (id="amoundApply")
    amount_select_el = wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))
    Select(amount_select_el).select_by_value(str(number))
    
    # 확인 버튼 (id="btnSelectNum")
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 자동 선택 완료.")
    time.sleep(1)

    # 7. 구매하기 및 최종 확인
    # 구매하기 버튼 (id="btnBuy")
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)
    
    # 최종 확인 팝업 (ID가 없으므로 XPath 사용)
    # onclick에 closepopupLayerConfirm이 포함된 확인 버튼 타겟팅
    final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"실행 중 오류 발생: {str(e)}\n현재 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("lotto_final_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저를 종료합니다.")
