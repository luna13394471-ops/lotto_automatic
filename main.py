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
    """텔레그램 알림 전송"""
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

# 봇 탐지 및 모바일 감지 무력화
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# PC 버전 유저 에이전트 고정
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

driver = webdriver.Chrome(options=chrome_options)

# [중요] CDP 명령으로 플랫폼 정보를 'Win32'로 강제 설정하여 모바일 리다이렉트 차단
driver.execute_cdp_cmd("Network.setUserAgentOverride", {
    "userAgent": user_agent,
    "platform": "Win32"
})

# navigator.webdriver 속성 제거
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

wait = WebDriverWait(driver, 25)

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

    # 1. 로그인 단계 (이미 성공한 경로 유지)
    print(f"로그인 시도 중... (ID: {id})")
    driver.get("https://dhlottery.co.kr/login")
    time.sleep(random.uniform(2, 4))

    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    # 로그인 후 세션이 구매 서버로 전파될 시간을 충분히 줍니다.
    time.sleep(6) 
    print("로그인 완료.")

    # 2. 구매 페이지 접속 전 PC 메인 경유 (Referer 생성)
    print("PC 메인 페이지 경유 중...")
    driver.get("https://dhlottery.co.kr/common.do?method=main")
    time.sleep(2)

    # 3. 로또 구매 페이지 접속 (PC 버전 전용)
    print("구매 페이지 접속 시도...")
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    time.sleep(5)

    # [핵심] 모바일로 튕겼는지 다시 한번 확인하고 강제 복구
    if "m.dhlottery" in driver.current_url:
        print("모바일 페이지 재감지. 강제 PC 버전 주소 호출...")
        driver.execute_script("location.href='https://ol.dhlottery.co.kr/olotto/game/game645.do'")
        time.sleep(5)

    # 4. Iframe 전환 및 구매 로직
    # 구매 화면은 반드시 iframe 안에 있으므로 전환이 필수입니다.
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 진입 성공.")
    except:
        # Iframe이 없다면 화면 상태를 캡처하여 분석합니다.
        driver.save_screenshot("purchase_screen_debug.png")
        raise Exception(f"구매 Iframe을 찾을 수 없습니다. (URL: {driver.current_url})")

    # 5. 자동 번호 발행 및 수량 선택
    # '자동번호발행' 버튼 클릭
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 선택 (기본 1개)
    amount_sel = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_sel.select_by_value(str(number))
    
    # 선택 완료(확인) 버튼
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 선택 완료.")
    time.sleep(1)
    
    # 6. 최종 구매 진행
    driver.find_element(By.ID, "btnBuy").click()
    time.sleep(1)

    # 최종 확인 팝업의 '확인' 버튼 (XPath 활용)
    final_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"에러 발생: {str(e)}\n최종 URL: {driver.current_url}"
    print(error_msg)
    driver.save_screenshot("final_error_debug.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
