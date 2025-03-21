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

id =  # 아이디

# keywords = [
#     "이혼 청구", "협의 이혼", "재판상 이혼", "이혼 소송", 
#     "이혼 사유", "이혼 조정", "이혼 판결", "이혼 위자료", 
#     "이혼 후 재산 분할", "이혼 관련 법률", "이혼 재산 분할", 
#     "부부 공동재산", "특유재산 분리", "혼인 중 재산 형성 기여도", 
#     "재산 분할 비율", "위자료와 재산 분할 차이", "퇴직금 재산 분할", 
#     "부동산 재산 분할", "사업체 재산 분할", "채무 분할", "이혼 후 양육권", 
#     "양육권 소송", "양육비 청구", "양육권 변경", "양육비 지급 의무", "친권자 변경", 
#     "비양육 부모 면접교섭권", "양육비 미지급 제재", "아이 거주지 변경"
# ]

keywords = [
    "이혼", "배우자의 부정행위", "불륜으로 인한 이혼", "가정폭력 이혼", "배우자의 폭력", "경제적 폭력 (생활비 미지급)",
    "유책 배우자의 이혼 청구 가능 여부", "정신질환으로 인한 이혼", "배우자의 도박 중독", "배우자의 알코올 중독",
    "배우자의 마약 중독", "국제결혼 이혼", "외국인 배우자 이혼", "국내/해외 이혼 절차 차이", "다문화 가정 이혼",
    "국제 양육권 분쟁", "외국인 배우자 강제 출국", "혼인 무효 및 취소", "혼인 무효 소송", "강제 결혼 취소",
    "허위 혼인신고 취소", "근친혼 이혼", "배우자의 이중결혼(중혼)", "속임수 결혼(사기 혼인)", "미성년자 혼인 무효",
    "이혼 후 성 변경", "이혼 후 재혼 문제", "이혼 후 재산 명의 변경", "이혼 후 아이 성 변경",
    "이혼 후 양육비 지급 분쟁", "이혼 후 부모 면접권", "이혼 후 주거 문제"
]

# API URL 설정
base_url = f"http://www.law.go.kr/DRF/lawSearch.do?OC={id}&target=prec&type=XML&search=2&query="

collected_data = []

# 각 키워드에 대해 크롤링을 반복
for keyword in keywords:
    query = quote(keyword)
    url = base_url + query

    response = urlopen(url).read()
    xml_data = ET.fromstring(response)

    totalCnt = int(xml_data.find('totalCnt').text)
    print(f"'{keyword}' 키워드로 총 {totalCnt}건의 판례 데이터 수집 시작")

    page = 1
    lawService = ['판시사항', '판결요지', '참조조문', '참조판례', '판례내용']

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
with open("law_data_2nd.json", "w", encoding="utf-8") as f:
    json.dump(collected_data, f, ensure_ascii=False, indent=4)

print("✅ 데이터 수집 완료. law_data_2nd.json 파일 저장됨.")
