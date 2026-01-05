import os
import time
import requests
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

# 구매 게임 수
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """텔레그램 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    icon = "✅ 성공" if is_success else "❌ 실패"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': f"{icon} 로또 알림\n{message}"}
    try: requests.post(url, data=payload, timeout=5)
    except: pass

# Chrome 옵션 최적화 (모바일 리다이렉트 방지 및 우회)
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
# [중요] 일반적인 PC 크롬 브라우저인 척 속입니다.
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
# 자동화 탐지 방지 플래그
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=chrome_options)

# [중요] navigator.webdriver 속성 제거 (자동화 차단 우회)
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
        raise ValueError("환경 변수(ID/PW)를 확인하세요.")

    # 1. 로그인 페이지 접속
    driver.get("https://dhlottery.co.kr/user.do?method=login") # PC 버전 로그인 명시
    print(f"로그인 시도 중... (ID: {id})")

    # 개편된 로그인 ID/PW 입력
    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    # 로그인 버튼 클릭 (JavaScript로 확실하게 클릭)
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(3)
    
    # 2. 리다이렉트 확인 및 강제 교정
    if "m.dhlottery.co.kr" in driver.current_url:
        print("모바일 페이지 감지됨. PC 버전으로 강제 전환합니다.")
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(2)

    # 3. 로또 구매 페이지 접속
    # el.dhlottery 서버로 직접 이동
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")
    time.sleep(4)

    # 4. Iframe 전환
    # 동행복권 사이트는 PC 버전에서 'ifrm_answer'라는 iframe을 반드시 사용합니다.
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 전환 성공.")
    except Exception as e:
        # Iframe이 없다면 모바일 페이지로 다시 튕겼을 가능성이 큽니다.
        raise Exception(f"Iframe을 찾을 수 없습니다. 현재 URL: {driver.current_url}")

    # 5. 자동번호발급 클릭
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 6. 수량 선택 및 확인
    amount_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_select.select_by_value(str(number))
    
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 선택 완료.")

    # 7. 구매하기 클릭
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)

    # 8. 최종 확인 팝업
    final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"오류 발생: {str(e)}"
    print(error_msg)
    driver.save_screenshot("error_debug.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
