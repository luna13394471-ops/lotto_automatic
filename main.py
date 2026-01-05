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

# --- 브라우저 설정 (PC 버전 강제 최적화) ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
# 창 크기를 크게 설정하여 모바일 리다이렉트를 방지합니다.
chrome_options.add_argument("--window-size=1920,1080")

# 봇 탐지 우회 및 PC 유저로 위장
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# [중요] 모바일 버전으로의 자동 전환을 막기 위해 확실한 PC용 User-Agent 사용
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# navigator.webdriver 속성 무력화
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

wait = WebDriverWait(driver, 20)

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

    # 1. 로그인 페이지 접속 (이미 성공한 경로 유지)
    print(f"로그인 페이지 접속 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/login")
    time.sleep(random.uniform(2, 3))

    # 2. 로그인 수행
    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(5) 
    print("로그인 단계 통과.")

    # [추가] 모바일 페이지로 튕겼는지 확인하고 PC 메인으로 강제 리다이렉트
    if "m.dhlottery" in driver.current_url:
        print("모바일 페이지 감지됨. PC 버전으로 재접속합니다.")
        driver.get("https://dhlottery.co.kr/common.do?method=main")
        time.sleep(2)

    # 3. 로또 구매 페이지 접속 (PC 전용 URL)
    print("구매 페이지 접속 시도...")
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    time.sleep(random.uniform(3, 5))

    # [중요] 다시 한번 모바일 체크 (구매 페이지 이동 시 또 튕길 수 있음)
    if "m.dhlottery" in driver.current_url:
        print("구매 페이지가 모바일로 튕겼습니다. 다시 시도합니다.")
        driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
        time.sleep(4)

    # 4. Iframe 전환 및 구매
    # PC 버전에서만 존재하는 iframe을 기다립니다.
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 진입 완료.")
    except:
        # Iframe이 안 보인다면 현재 화면의 스크린샷을 찍어 원인 파악
        driver.save_screenshot("frame_error.png")
        raise Exception(f"PC용 구매 화면(Iframe)을 찾을 수 없습니다. 현재 URL: {driver.current_url}")

    # 5. 구매 로직 (자동번호발급 -> 수량선택 -> 확인 -> 구매)
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_sel.select_by_value(str(number))
    
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 선택 완료.")
    time.sleep(1)
    
    driver.find_element(By.ID, "btnBuy").click()
    time.sleep(1)

    # 최종 확인 팝업 (XPath)
    final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"에러 발생: {str(e)}\n종료 시점 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("lotto_mobile_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
