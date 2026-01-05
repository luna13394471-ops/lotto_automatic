import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options

# ⭐ 환경 변수 설정 (GitHub Secrets 등에서 가져옴)
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 구매 게임 수 (1~5)
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """지정된 텔레그램 봇으로 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("경고: 텔레그램 환경 변수가 설정되지 않았습니다.")
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
        print(f"텔레그램 알림 전송 실패: {e}")

# Chrome 브라우저 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless") # 헤드리스 모드 (GitHub Actions 필수)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    if not id or not password:
        raise ValueError("LOTTO_ID 또는 LOTTO_PASSWORD 환경 변수가 설정되지 않았습니다.")

    # 1. 로그인 페이지 접속
    driver.get("https://dhlottery.co.kr/login")
    print(f"로그인 페이지 접속 (ID: {id})")

    # 아이디/비밀번호 입력 (개편된 ID 적용)
    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    
    # 로그인 버튼 클릭
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(3)
    print("로그인 완료.")

    # 2. 로또 구매 페이지 접속
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 중...")
    time.sleep(3)

    # 3. Iframe 전환 (동행복권 구매 창은 iframe 내부에 위치함)
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
        print("구매 Iframe 진입 성공.")
    except:
        print("Iframe 전환 실패 또는 필요 없음. 계속 진행합니다.")

    # 4. 자동번호발급 클릭
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    print("자동번호발급 선택.")

    # 5. 수량 선택 (Select Box)
    select_el = wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))
    select = Select(select_el)
    select.select_by_value(str(number))
    
    # 6. 확인 버튼 (선택번호 적용)
    confirm_num_btn = driver.find_element(By.ID, "btnSelectNum")
    driver.execute_script("arguments[0].click();", confirm_num_btn)
    print(f"구매 수량 {number}개 적용.")

    # 7. 구매하기 버튼 클릭
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)
    print("구매하기 버튼 클릭.")

    # 8. 최종 구매 확인 팝업 버튼 클릭
    # ID가 없으므로 XPath를 통해 '확인' 글자와 onclick 함수명을 가진 요소를 찾음
    final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    # 최종 결과 출력
    success_msg = f"로또 자동 구매 성공!\n구매 게임 수: {number}개"
    print(success_msg)
    send_telegram_message(success_msg, True)
    time.sleep(2)

except Exception as e:
    error_msg = f"스크립트 실행 중 오류 발생: {e}"
    print(error_msg)
    # 디버깅을 위한 스크린샷 저장
    driver.save_screenshot("lotto_error.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
