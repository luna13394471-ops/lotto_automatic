import os
import time
import requests # ⭐️ 텔레그램 알림을 위한 requests 라이브러리 추가
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options

# ⭐ 환경 변수(GitHub Secrets)에서 ID와 Password를 가져옵니다.
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
# ⭐️ 텔레그램 알림을 위한 환경 변수를 가져옵니다.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 구매횟수 (5개까지 가능)
number = 1 

# ⭐️ 텔레그램 메시지를 전송하는 함수
def send_telegram_message(message: str, is_success: bool):
    """지정된 봇 토큰과 채팅 ID로 텔레그램 메시지를 전송합니다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: 텔레그램 환경 변수(TOKEN/CHAT_ID)가 설정되지 않아 알림을 보낼 수 없습니다.")
        return

    # 메시지 포맷팅
    icon = "✅ 성공" if is_success else "❌ 실패"
    full_message = f"{icon} 로또 자동 구매 알림\n\n{message}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': full_message,
        'parse_mode': 'Markdown' # Markdown 포맷 사용 가능 (선택 사항)
    }

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생
        print("텔레그램 알림 전송 완료.")
    except requests.exceptions.RequestException as e:
        print(f"텔레그램 알림 전송 중 오류 발생: {e}")

# Chrome 옵션 설정
chrome_options = Options()
# GitHub Actions 환경에서 필수: 헤드리스 모드 및 리소스 최적화
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080") # 화면 크기 지정 (headless에서 안정성↑)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

# WebDriver 객체 생성 (Selenium Manager가 드라이버를 자동 관리)
# GitHub Actions 환경에서는 경로 지정 없이 Options만 전달합니다.
driver = webdriver.Chrome(options=chrome_options)

log_message = f"로그인 시도 ID: {id}\n구매 횟수: {number} 게임"
print(log_message)


try:
    # 1. 웹 페이지 접속 및 로그인
    driver.get("https://dhlottery.co.kr/user.do?method=login&returnUrl=")

    # 아이디와 비밀번호 입력 필드가 나타날 때까지 대기
    username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userId")))
    password_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#article > div:nth-child(2) > div > form > div > div.inner > fieldset > div.form > input[type=password]:nth-child(2)")))
    
    # 🚨 NoneType 체크: 환경 변수가 제대로 전달되지 않은 경우 에러 방지
    if not id or not password:
        raise ValueError("LOTTO_ID 또는 LOTTO_PASSWORD가 환경 변수로 설정되지 않았습니다.")

    username_field.send_keys(id)
    password_field.send_keys(password)
    
    # 로그인 버튼 클릭
    login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="article"]/div[2]/div/form/div/div[1]/fieldset/div[1]/a')))
    login_button.click()

    time.sleep(3) # 로그인 후 페이지 전환 대기
    print("로그인 완료.")

    # 2. 로또 구매 페이지 접속
    driver.get('https://ol.dhlottery.co.kr/olotto/game/game645.do')
    time.sleep(3)
    
    # 간혹 뜨는 팝업창 닫기 (자바스크립트 실행)
    driver.execute_script('javascript:closepopupLayerAlert();')
    
    # '자동번호 발행' 버튼 클릭 (ID: num2)
    auto_generate_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "num2")))
    auto_generate_button.click()
    
    print("자동 번호 발행 선택 완료.")

    # 3. 구매 횟수 선택
    # <select> 요소가 나타날 때까지 대기 (ID: amoundApply)
    select_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "amoundApply")))
    select = Select(select_element)
    
    # number 변수에 설정된 횟수 옵션을 선택 (문자열로 변환 필요)
    select.select_by_value(str(number))

    # '확인' (선택번호 적용) 버튼 클릭 (ID: btnSelectNum)
    apply_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "btnSelectNum")))
    apply_button.click()
    
    print(f"구매 횟수 {number}개 적용 완료.")
    time.sleep(1)

    # 4. 구매 및 최종 확인
    # '구매하기' 버튼 클릭 (ID: btnBuy)
    buy_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "btnBuy")))
    buy_button.click()
    
    # 최종 구매 확인 팝업의 '확인' 버튼 클릭
    final_confirm_button = WebDriverWait(driver, 10).until((EC.presence_of_element_located((By.CSS_SELECTOR, "#popupLayerConfirm > div > div.btns > input:nth-child(1)"))))
    final_confirm_button.click()
    
    success_message = f"로또 구매 성공!\n구매 횟수: {number} 게임"
    print(success_message)
    # ⭐️ 성공 알림 전송
    send_telegram_message(success_message, is_success=True)
    time.sleep(5)
    
except ValueError as e:
    error_msg = f"구성 오류 발생: {e}"
    print(error_msg)
    # ⭐️ 실패 알림 전송
    send_telegram_message(error_msg, is_success=False)
except Exception as e:
    error_msg = f"스크립트 실행 중 오류 발생: {e}"
    print(error_msg)
    # 오류 발생 시 현재 페이지 스크린샷 저장 (디버깅용)
    driver.save_screenshot("error_screenshot.png")
    # ⭐️ 실패 알림 전송
    send_telegram_message(error_msg, is_success=False)
    
finally:
    # 웹드라이버 종료
    driver.quit()
