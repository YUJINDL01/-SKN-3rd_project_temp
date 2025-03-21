import xml.etree.ElementTree as ET
from urllib.request import urlopen
from urllib.parse import quote
from tqdm import trange
from datetime import datetime
import re
import json
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def remove_tag(content):
    cleaned_text = re.sub('<.*?>', '', content)
    return cleaned_text

id = # 아이디
query = quote("이혼")
# API URL 설정
# url = "https://www.law.go.kr/DRF/lawSearch.do?OC=qkrdbwlsdl01&target=prec&type=XML&query=이혼"
# url = f"http://www.law.go.kr/DRF/lawSearch.do?OC=qkrdbwlsdl01&target=prec&type=XML&query={query}"
url = f"http://www.law.go.kr/DRF/lawSearch.do?OC={id}&target=prec&type=XML&search=2&query={query}"

response = urlopen(url).read()
xml_data = ET.fromstring(response)

totalCnt = int(xml_data.find('totalCnt').text)
print(f"총 {totalCnt}건의 판례 데이터 수집 시작")

page = 1
lawService = ['판시사항', '판결요지', '참조조문', '참조판례', '판례내용']

collected_data = []

for i in trange(int(totalCnt / 20)):
    try:
        prec_info = xml_data[5:]
    except:
        break
    
    print(f"페이지 {page}에서 판례 정보 처리 시작")

    for info in prec_info:
        judicPrecNum = info.find('판례일련번호').text
        case = info.find('사건명').text
        caseNum = info.find('사건번호').text
        sentence_date = datetime.strptime(info.find('선고일자').text, '%Y.%m.%d')
        court = info.find('법원명').text
        caseInfo = info.find('사건종류명').text
        caseCode = info.find('사건종류코드').text
        judgment = info.find('판결유형').text
        sentence = info.find('선고').text
        judicPrecLink = info.find('판례상세링크').text

        url_head = "https://www.law.go.kr/"
        detail_link = url_head + judicPrecLink.replace('HTML', 'XML')
        detail = urlopen(detail_link).read()
        detail_data = ET.fromstring(detail)
        
        content_list = []
        for content in lawService:
            if detail_data.find(content) is None:
                text = '내용없음'
            else:
                text = detail_data.find(content).text
                text = remove_tag(str(text))
                
            content_list.append(text)        
        
        prec_content = content_list[4]
        prec_content = prec_content.split("【")
        del prec_content[0]

        pattern = "[^【]*】"
        prec_dic = {}

        for content in prec_content:
            match = re.match(pattern, content)
            if match:
                if '이유' in prec_dic.keys():
                    prec_dic['이유'] = prec_dic['이유'] + " 【" + match.group(0).lstrip() + content.replace(match.group(0), "").strip()
                
                else:
                    key = match.group(0).replace("】", "").replace(" ", "")
                    value = content.replace(match.group(0), "").strip()
                    
                    prec_dic[key] = value
        
        result = {
            '판례일련번호': judicPrecNum,
            '사건명': case,
            '사건번호': caseNum,
            '선고일자': sentence_date.strftime("%Y-%m-%d"),
            '법원명': court,
            '사건종류명': caseInfo,
            '사건종류코드': caseCode,
            '판결유형': judgment,
            '선고': sentence,
            '판시사항': content_list[0].strip(),
            '판결요지': content_list[1].strip(),
            '참조조문': content_list[2].strip(),
            '참조판례': content_list[3].strip(),
            '판례내용': prec_dic
        }
        
        collected_data.append(result)

        # 중간중간 크롤링 상태 출력
        print(f"수집된 판례: {case} ({judicPrecNum})")

    # 페이지 증가 및 출력
    page += 1
    print(f"페이지 {page} 처리 중...")
    response = urlopen(url + '&page=' + str(page)).read()
    xml_data = ET.fromstring(response)

# 결과를 JSON 파일로 저장
with open("law_data.json", "w", encoding="utf-8") as f:
    json.dump(collected_data, f, ensure_ascii=False, indent=4)

print("✅ 데이터 수집 완료. law_data.json 파일 저장됨.")
