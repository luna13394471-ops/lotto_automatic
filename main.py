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

# --- [핵심] 봇 방어 우회 설정 ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# 10년차의 팁: 자동화 제어 흔적을 완전히 지웁니다.
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# 실제 윈도우 PC 크롬인 것처럼 속임
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# [필수] navigator.webdriver 속성을 null로 만들어 봇 탐지 우회
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """
})

wait = WebDriverWait(driver, 20)

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 없습니다.")

    # 1. 로그인 페이지 직접 접속 (사용자 경험 기반)
    # 직접 접속하되, 서버가 '비정상'으로 느끼지 않게 헤더를 잘 꾸몄습니다.
    print(f"로그인 페이지 직접 접속 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/login")
    time.sleep(random.uniform(2, 4))

    # 차단 페이지 체크
    if "errorPage" in driver.current_url:
        print("!!! 여전히 차단 중 !!! 서버가 IP를 기억하고 있습니다.")
        driver.save_screenshot("direct_block_error.png")
        raise Exception("서버에서 직접 접속을 거부하고 있습니다. (errorPage)")

    # 2. 로그인 정보 입력
    # 가시성 확보될 때까지 대기
    user_id_el = wait.until(EC.visibility_of_element_located((By.ID, "inpUserId")))
    user_id_el.send_keys(id)
    
    password_el = driver.find_element(By.ID, "inpUserPswdEncn")
    password_el.send_keys(password)
    
    # 로그인 버튼 클릭 (JavaScript 실행으로 클릭 차단 우회)
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(5) # 로그인 후 세션 저장 대기
    print("로그인 단계 통과.")

    # 3. 구매 페이지 이동
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")
    time.sleep(random.uniform(3, 5))

    # 4. Iframe 전환 및 구매
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))

    # 자동번호발급 (id="num2")
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 설정
    amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_sel.select_by_value(str(number))
    
    # 확인 버튼
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 선택 완료.")
    
    # 구매하기 버튼
    driver.find_element(By.ID, "btnBuy").click()
    time.sleep(1)

    # 최종 확인 팝업 (XPath)
    final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"오류 발생: {str(e)}\n현재 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("final_retry_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
