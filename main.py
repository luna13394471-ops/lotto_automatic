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

# --- 우회 설정 강화 ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

# 10년차 노하우: 자동화 감지 요소들을 최대한 제거
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# User-Agent를 주기적으로 바꿔주는 것이 좋으나, 일단 최신 PC 버전으로 고정
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# navigator.webdriver 값을 null로 만들어 봇 탐지를 우회
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
        raise ValueError("ID/PW 환경 변수를 설정해주세요.")

    # 1. 메인 페이지 접속 (쿠키 생성 및 정상 경로 시뮬레이션)
    print("메인 페이지 접속 중...")
    driver.get("https://dhlottery.co.kr/common.do?method=main")
    time.sleep(random.uniform(2, 4))

    # 2. 로그인 페이지로 이동 (직접 URL 입력 대신 클릭을 유도하거나 Referer 유지)
    print(f"로그인 페이지 이동 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/user.do?method=login")
    time.sleep(2)

    # 에러 페이지 체크
    if "errorPage" in driver.current_url:
        print("!!! 차단 감지 !!!: 에러 페이지로 리다이렉트되었습니다.")
        # 현재 화면 스크린샷 찍어서 원인 파악
        driver.save_screenshot("block_error.png")
        raise Exception("동행복권 서버에서 현재 접속을 차단했습니다. (WAF 감지)")

    # 3. 로그인 정보 입력 (개편된 셀렉터 적용)
    user_id_field = wait.until(EC.element_to_be_clickable((By.ID, "inpUserId")))
    user_id_field.send_keys(id)
    
    password_field = driver.find_element(By.ID, "inpUserPswdEncn")
    password_field.send_keys(password)
    
    # 로그인 버튼 클릭
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(3)
    print("로그인 완료.")

    # 4. 구매 페이지로 이동
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")
    time.sleep(random.uniform(3, 5))

    # 5. Iframe 전환 및 구매
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        
        # 자동번호발급
        auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
        driver.execute_script("arguments[0].click();", auto_btn)
        
        # 수량 선택
        amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
        amount_sel.select_by_value(str(number))
        
        # 확인 버튼
        driver.find_element(By.ID, "btnSelectNum").click()
        time.sleep(1)
        
        # 구매하기
        driver.find_element(By.ID, "btnBuy").click()
        time.sleep(1)

        # 최종 확인 팝업 (XPath)
        final_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]")))
        driver.execute_script("arguments[0].click();", final_btn)

        success_msg = f"로또 구매 성공! ({number}게임)"
        print(success_msg)
        send_telegram_message(success_msg, True)

    except Exception as e:
        print(f"구매 단계 오류: {e}")
        driver.save_screenshot("purchase_error.png")
        raise e

except Exception as e:
    error_msg = f"오류 발생: {str(e)}\n현재 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("final_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
