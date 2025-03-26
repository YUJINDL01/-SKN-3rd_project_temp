from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import csv

# 다운로드 경로 설정
download_path = os.path.join(os.getcwd(), "rawdata")  # 현재 작업 디렉토리 내의 'rawdata' 폴더
if not os.path.exists(download_path):
    os.makedirs(download_path)  # 폴더가 없으면 생성

# Chrome 옵션 설정
chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,  # 다운로드 팝업 비활성화
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True  # PDF 파일이 브라우저에서 열리지 않고 다운로드되도록 설정
}
chrome_options.add_experimental_option("prefs", prefs)

query_text = ["이혼"]
count = 0

# 크롬 실행 (옵션 적용)
driver = webdriver.Chrome(options=chrome_options)

# url 접근 
driver.get("https://www.law.go.kr/LSW/main.html")

# 법령 선택 
search_bar = driver.find_element(By.ID, "search").find_element(By.ID, "inner")

for value in query_text:
    search_bar.find_element(By.ID, "query").send_keys(value)
    time.sleep(0.5)
    search_button = search_bar.find_element(By.CSS_SELECTOR, "a.srchBtn")
    driver.execute_script("arguments[0].click();", search_button)

# 예정법령 선택 해제 + 클릭
driver.find_element(By.ID, "dtlSch").find_element(By.CSS_SELECTOR, "a").click()
time.sleep(0.5)

pop_up_section = driver.find_element(By.ID, "detailLawCtDiv").find_elements(By.CSS_SELECTOR, "div")

pop_up_section[1].find_elements(By.CSS_SELECTOR, "dd.dd01")[1].click()
time.sleep(0.5)

# 요소가 로드될 때까지 최대 10초 대기
search_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//a[@onclick=\"javascript:newDtlSearch('lawNm');return false;\"]"))
)

search_button.click()
time.sleep(0.5)

search_bar = driver.find_element(By.ID, "sr_area")
time.sleep(1)

driver.find_element(By.ID, "viewHeightDiv").find_element(By.CSS_SELECTOR, "tbody>tr>td.tl").find_element(By.CSS_SELECTOR, "a").click()
time.sleep(0.5)

try:
    max_laws = 5  # 최대 처리할 법령 수 (테스트용)
    processed_laws = 0
    
    while processed_laws < max_laws:  # 테스트를 위해 제한된 수의 법령만 처리
        # 전체 목록 가지고 오기
        law_list = driver.find_elements(By.XPATH, '//*[@id="listDiv"]/div/ul/li')
        
        if not law_list:
            print("더 이상 법령이 없습니다.")
            break
            
        for law in law_list:
            if processed_laws >= max_laws:
                break
                
            # 법령 제목 가져오기 (로그용)
            try:
                law_title = law.find_element(By.CSS_SELECTOR, "a").text
                print(f"처리 중: {law_title}")
            except:
                print("제목을 가져올 수 없는 법령 처리 중")
            
            # 전체 목록 중 하나
            law.find_element(By.CSS_SELECTOR, "a").click()
            time.sleep(2)

            # 법령 다운로드
            driver.find_element(By.ID, "bdySaveBtn").click()
            time.sleep(2)

            # 선택사항 조절 - 시행 예정 조문 포함 해제
            joEfOutPutYn = driver.find_element(By.ID, "joEfOutPutYn")
            if joEfOutPutYn.is_selected():
                joEfOutPutYn.click()
            time.sleep(1)

            # pdf로 저장 옵션 선택
            driver.find_element(By.ID, "FileSavePdf1").click()
            time.sleep(1)

            # 다운 버튼 클릭
            driver.find_element(By.ID, "aBtnOutPutSave").click()
            time.sleep(3)  # 다운로드 완료 대기 시간 증가
            
            processed_laws += 1
            
            # 목록으로 돌아가기
            back_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '목록으로')]"))
            )
            back_button.click()
            time.sleep(2)
        
        # 다음 페이지로 이동
        try:
            next_button = driver.find_element(By.XPATH, '//*[@id="listDiv"]/div[2]/ol/li[2]/a')
            next_button.click()
            time.sleep(2)
        except:
            print("다음 페이지가 없습니다.")
            break

except Exception as e:
    print(f"오류 발생: {e}")

finally:
    print(f"총 {processed_laws}개 법령 처리 완료. 다운로드 경로: {download_path}")
    time.sleep(3)
    driver.quit()

# PDF를 텍스트로 변환하는 코드 (앞서 작성한 코드 활용)
import glob
import json
import pickle
import PyPDF2
from pdfminer.high_level import extract_text
import pandas as pd

def convert_pdf_to_text(pdf_path, output_dir):
    """
    PDF 파일을 텍스트 파일로 변환
    PyPDF2로 처리가 안 되는 경우 pdfminer를 사용
    파일 이름은 '(' 문자 이전까지만 사용
    """
    # 원본 파일 이름에서 '(' 이전까지만 사용
    full_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    # '(' 문자가 있는 경우 그 이전까지만 사용
    if '(' in full_filename:
        filename = full_filename.split('(')[0].strip()
    else:
        filename = full_filename
    
    output_text_path = os.path.join(output_dir, f"{filename}.txt")
    
    try:
        # 먼저 PyPDF2로 시도 (속도가 빠름)
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        
        # 추출된 텍스트가 너무 적거나 없으면 pdfminer 사용
        if len(text.strip()) < 100:
            text = extract_text(pdf_path)
    
    except Exception as e:
        print(f"PyPDF2 처리 중 오류 발생: {e}")
        # 백업 방법으로 pdfminer 사용 (한글 지원이 더 좋음)
        try:
            text = extract_text(pdf_path)
        except Exception as e:
            print(f"pdfminer 처리 중 오류 발생: {e}")
            text = f"오류: {pdf_path} 파일을 처리할 수 없습니다."
    
    # 텍스트 파일로 저장
    with open(output_text_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return text, output_text_path, filename

def save_as_json(all_texts, output_dir):
    """
    모든 PDF 내용을 하나의 JSON 파일로 저장
    {'파일 이름': 텍스트 내용} 형식
    """
    json_path = os.path.join(output_dir, 'law_data.json')
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_texts, f, ensure_ascii=False, indent=2)
    
    return json_path

def save_as_pickle(all_texts, output_dir):
    """
    모든 PDF 내용을 하나의 Pickle 파일로 저장
    """
    pickle_path = os.path.join(output_dir, 'law_data.pkl')
    
    with open(pickle_path, 'wb') as f:
        pickle.dump(all_texts, f)
    
    return pickle_path

def process_all_pdfs_in_directory(data_dir='rawdata', output_dir='data'):
    """
    지정된 디렉토리의 모든 PDF 파일을 처리
    """
    # 출력 디렉토리가 없으면 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 모든 PDF 파일 찾기
    pdf_files = glob.glob(os.path.join(data_dir, '*.pdf'))
    
    if not pdf_files:
        print(f"{data_dir} 폴더에 PDF 파일이 없습니다.")
        return
        
    print(f"{len(pdf_files)}개의 PDF 파일을 처리합니다.")
    
    results = []
    all_texts = {}  # 모든 텍스트를 저장할 딕셔너리: {파일이름: 내용}
    
    for pdf_file in pdf_files:
        print(f"처리 중: {pdf_file}")
        
        # PDF를 텍스트로 변환
        text, text_path, clean_filename = convert_pdf_to_text(pdf_file, output_dir)
        
        # 모든 텍스트 내용 저장
        all_texts[clean_filename] = text
        
        results.append({
            '원본파일': pdf_file,
            '텍스트파일': text_path,
        })
    
    # 모든 내용을 JSON 파일로 저장
    json_path = save_as_json(all_texts, output_dir)
    print(f"모든 텍스트가 {json_path} JSON 파일에 저장되었습니다.")
    
    # 모든 내용을 Pickle 파일로 저장
    pickle_path = save_as_pickle(all_texts, output_dir)
    print(f"모든 텍스트가 {pickle_path} Pickle 파일에 저장되었습니다.")
    
    # 처리 결과 요약 CSV 생성
    if results:
        pd.DataFrame(results).to_csv(os.path.join(output_dir, '처리결과_요약.csv'), 
                                    index=False, encoding='utf-8')
        print(f"총 {len(results)}개 파일 처리 완료. 결과는 {output_dir} 폴더에 저장되었습니다.")

# 크롤링 후 PDF 처리 실행
if __name__ == "__main__":
    process_all_pdfs_in_directory()