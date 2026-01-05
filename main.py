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

# --- 브라우저 설정 (PC 버전 완벽 위장) ---
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# CDP 명령으로 플랫폼 정보 고정 (모바일 리다이렉트 방지)
driver.execute_cdp_cmd("Network.setUserAgentOverride", {
    "userAgent": user_agent,
    "platform": "Win32"
})

driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

wait = WebDriverWait(driver, 30) # 대기 시간을 30초로 충분히 확보

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수 설정 확인")

    # 1. 로그인 단계
    print(f"로그인 시도 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/login")
    time.sleep(random.uniform(2, 3))

    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(5) 
    print("로그인 완료.")

    # 2. 구매 페이지 접속
    print("구매 페이지 접속 시도...")
    # 사용자가 준 최신 URL로 접속
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    time.sleep(7) # 페이지 로딩 및 세션 전파 대기

    # 3. Iframe 유연한 전환 로직 (핵심 수정)
    print("Iframe 탐색 및 전환 시도...")
    try:
        # 방법 1: 기존 ID(ifrm_answer)로 시도
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe(ID: ifrm_answer) 진입 성공.")
    except:
        print("ID로 찾기 실패. 페이지 내 첫 번째 Iframe으로 자동 전환 시도...")
        try:
            # 방법 2: ID에 상관없이 첫 번째 iframe으로 전환
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                driver.switch_to.frame(iframes[0])
                print("첫 번째 Iframe으로 전환 완료.")
            else:
                raise Exception("페이지 내에 Iframe이 전혀 존재하지 않습니다.")
        except Exception as e:
            driver.save_screenshot("no_iframe_debug.png")
            raise Exception(f"Iframe 전환에 최종 실패했습니다. 현재 URL: {driver.current_url}")

    # 4. 자동 번호 발행 및 구매 (제공해주신 HTML 구조 적용)
    print("구매 로직 시작...")
    # '자동번호발급' 클릭
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 선택 (amoundApply)
    amount_sel_el = wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))
    Select(amount_sel_el).select_by_value(str(number))
    
    # '확인' 버튼 클릭 (btnSelectNum)
    confirm_num_btn = driver.find_element(By.ID, "btnSelectNum")
    driver.execute_script("arguments[0].click();", confirm_num_btn)
    print(f"{number}게임 자동 선택 완료.")
    time.sleep(1)
    
    # '구매하기' 버튼 클릭 (btnBuy)
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)
    
    # 5. 최종 확인 팝업 (closepopupLayerConfirm(true) 호출 버튼)
    print("최종 확인 팝업 처리 중...")
    final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)
    time.sleep(2)

except Exception as e:
    error_msg = f"에러 발생: {str(e)}\n현재 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("final_step_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
