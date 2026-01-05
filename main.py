import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ⭐ 환경 변수(GitHub Secrets) 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 구매횟수 (최대 5개)
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """텔레그램 알림 전송 함수"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: 텔레그램 설정이 없습니다.")
        return

    icon = "✅ 성공" if is_success else "❌ 실패"
    full_message = f"{icon} 로또 자동 구매 알림\n\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': full_message, 'parse_mode': 'Markdown'}

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("텔레그램 알림 전송 완료.")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless") # GitHub Actions 필수
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    print(f"로그인 시도 ID: {id}")
    
    # 1. 로그인 페이지 접속
    driver.get("https://dhlottery.co.kr/login")
    
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

    # 아이디/비밀번호 입력 (셀렉터 최신화)
    wait.until(EC.presence_of_element_located((By.ID, "userId"))).send_keys(id)
    driver.find_element(By.NAME, "password").send_keys(password)
    
    # 로그인 버튼 클릭
    login_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_common.l_gradient")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(2)
    print("로그인 프로세스 완료.")

    # 2. 로또 구매 페이지 이동
    # 사용자가 제공한 최신 URL 사용
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")

    # 3. Iframe 전환 (매우 중요)
    # 동행복권 구매 화면은 보통 'ifrm_answer' 등의 ID를 가진 iframe 안에 있습니다.
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
    except TimeoutException:
        print("Iframe을 찾을 수 없습니다. 메인 컨텐츠에서 계속합니다.")

    # 4. 자동 번호 선택 및 구매 로직
    # '자동번호발행' 버튼 클릭
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    auto_btn.click()
    
    # 수량 선택 (Select Box)
    amount_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_select.select_by_value(str(number))
    
    # '확인' 버튼 클릭
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 자동 선택 완료.")

    # 5. 구매하기 버튼 클릭
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    buy_btn.click()

    # 6. 최종 확인 팝업 (Alert 또는 Layer)
    # 브라우저 기본 Alert일 경우와 레이어 팝업일 경우를 모두 대비
    try:
        # 10년차의 팁: 레이어 팝업 내 확인 버튼 처리
        confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#popupLayerConfirm input.btn_common_mid.blue")))
        confirm_btn.click()
    except:
        # 브라우저 Alert인 경우 처리
        alert = driver.switch_to.alert
        alert.accept()

    success_msg = f"로또 자동 구매 성공! (수량: {number})"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"에러 발생: {str(e)}"
    print(error_msg)
    driver.save_screenshot("error_debug.png") # 디버깅용 스크린샷
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
