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

# 구매횟수 (최대 5개)
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """텔레그램 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: 텔레그램 설정 누락")
        return
    icon = "✅ 성공" if is_success else "❌ 실패"
    full_message = f"{icon} 로또 자동 구매 알림\n\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': full_message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload).raise_for_status()
        print("텔레그램 알림 전송 완료.")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

    # 1. 로그인 페이지 접속
    driver.get("https://dhlottery.co.kr/login")
    print(f"로그인 페이지 접속 완료 (ID: {id})")

    # 2. 개편된 HTML 기준 아이디/비번 입력
    # visibility_of_element_located를 사용하여 상호작용 가능할 때까지 대기
    user_id_field = wait.until(EC.visibility_of_element_located((By.ID, "inpUserId")))
    password_field = wait.until(EC.visibility_of_element_located((By.ID, "inpUserPswdEncn")))
    
    user_id_field.clear()
    user_id_field.send_keys(id)
    password_field.clear()
    password_field.send_keys(password)
    
    # 3. 로그인 버튼 클릭
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnLogin")))
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(3)
    print("로그인 시도 완료.")

    # 4. 로또 구매 페이지 이동
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")
    time.sleep(3)

    # 5. Iframe 전환 (동행복권 구매창은 iframe 구조임)
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("Iframe 내 컨텐츠 접근 성공.")
    except Exception as e:
        print("Iframe 전환 건너뜀 (이미 메인이거나 구조가 다름)")

    # 6. 자동 번호 선택 및 수량 설정
    # '자동번호발행' 버튼
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    
    # 수량 선택
    amount_select = Select(wait.until(EC.presence_of_element_located((By.ID, "amoundApply"))))
    amount_select.select_by_value(str(number))
    
    # '확인' 버튼
    driver.find_element(By.ID, "btnSelectNum").click()
    print(f"{number}게임 자동 선택 완료.")

    # 7. 구매하기 및 최종 승인
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)

    # 최종 확인 팝업 (CSS 셀렉터 보강)
    confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#popupLayerConfirm input.btn_common_mid.blue, #popupLayerConfirm .btns input:nth-child(1)")))
    driver.execute_script("arguments[0].click();", confirm_btn)

    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)

except Exception as e:
    error_msg = f"스크립트 실행 중 오류 발생: {e}"
    print(error_msg)
    driver.save_screenshot("error_screenshot.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저를 종료합니다.")
