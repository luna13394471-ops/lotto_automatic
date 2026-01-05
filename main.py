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

# ⭐ 환경 변수 설정
id = os.environ.get("LOTTO_ID")
password = os.environ.get("LOTTO_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 구매 게임 수 (1~5)
number = 1 

def send_telegram_message(message: str, is_success: bool):
    """텔레그램 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    icon = "✅ 성공" if is_success else "❌ 실패"
    full_message = f"{icon} 로또 자동 구매 알림\n\n{message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': full_message}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20) # 대기 시간을 20초로 확장

try:
    if not id or not password:
        raise ValueError("ID/PW 환경 변수가 설정되지 않았습니다.")

    # 1. 로그인 페이지 접속 및 로그인
    driver.get("https://dhlottery.co.kr/login")
    print(f"로그인 시도 중... (ID: {id})")

    wait.until(EC.visibility_of_element_located((By.ID, "inpUserId"))).send_keys(id)
    driver.find_element(By.ID, "inpUserPswdEncn").send_keys(password)
    login_btn = driver.find_element(By.ID, "btnLogin")
    driver.execute_script("arguments[0].click();", login_btn)
    
    time.sleep(3) # 로그인 처리 대기
    print("로그인 완료.")

    # 2. 로또 구매 페이지 접속
    driver.get("https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40")
    print("구매 페이지 접속 및 로딩 대기...")

    # 3. Iframe 체크 및 전환 (가장 중요한 부분)
    # 개편 후 iframe이 없을 수도 있으므로 유연하게 대처합니다.
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            # ID가 'ifrm_answer'인 프레임이 있는지 확인하고 있다면 전환
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ifrm_answer")))
            print("Iframe 전환 완료.")
        else:
            print("Iframe이 없어 메인 프레임에서 계속 진행합니다.")
    except Exception as e:
        print(f"Iframe 확인 중 알림: {e}")

    # 4. 자동번호발급 클릭
    # 페이지 내에 버튼이 로드될 때까지 충분히 대기
    auto_btn = wait.until(EC.element_to_be_clickable((By.ID, "num2")))
    driver.execute_script("arguments[0].click();", auto_btn)
    print("자동번호발급 선택 완료.")

    # 5. 수량 선택 및 확인
    amount_select_el = wait.until(EC.presence_of_element_located((By.ID, "amoundApply")))
    Select(amount_select_el).select_by_value(str(number))
    
    confirm_num_btn = driver.find_element(By.ID, "btnSelectNum")
    driver.execute_script("arguments[0].click();", confirm_num_btn)
    print(f"구매 수량 {number}개 적용 완료.")

    # 6. 구매하기 버튼 클릭
    buy_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnBuy")))
    driver.execute_script("arguments[0].click();", buy_btn)
    print("구매하기 버튼 클릭 완료.")

    # 7. 최종 구매 확인 팝업 (ID가 없으므로 XPath 사용)
    # onclick에 closepopupLayerConfirm이 포함된 '확인' 버튼을 찾음
    final_confirm_xpath = "//input[@value='확인' and contains(@onclick, 'closepopupLayerConfirm')]"
    final_confirm_btn = wait.until(EC.element_to_be_clickable((By.XPATH, final_confirm_xpath)))
    driver.execute_script("arguments[0].click();", final_confirm_btn)

    # 결과 전송
    success_msg = f"로또 자동 구매 성공! ({number}게임)"
    print(success_msg)
    send_telegram_message(success_msg, True)
    time.sleep(3)

except Exception as e:
    error_msg = f"스크립트 실행 중 오류 발생: {str(e)}"
    print(error_msg)
    # 에러 발생 시 현재 페이지 제목과 URL을 로그에 남김
    print(f"에러 시점 URL: {driver.current_url}")
    driver.save_screenshot("lotto_error_debug.png")
    send_telegram_message(error_msg, False)

finally:
    driver.quit()
    print("브라우저 종료.")
