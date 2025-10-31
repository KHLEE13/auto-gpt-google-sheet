#!/usr/bin/env python
# coding: utf-8
# ===============================================================
# 🚗 GPT 자동차 추천 자동화 (월별 시트 분할 + 실시간 저장, GitHub Actions 호환)
# ===============================================================

import os
import openai
import gspread
import time
import json
import requests
from datetime import datetime
from google.oauth2.service_account import Credentials

# ===============================================================
# 🔧 설정
# ===============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
DELAY = 2
MAX_RETRY = 3
MODELS = ["gpt-4o-mini", "gpt-4o"]

# ===============================================================
# 🔐 인증 (로컬 or GitHub 자동 감지)
# ===============================================================
if os.getenv("GOOGLE_SERVICE_JSON"):
    # GitHub Actions 환경에서 JSON을 Secret으로 로드
    service_info = json.loads(os.getenv("GOOGLE_SERVICE_JSON"))
    creds = Credentials.from_service_account_info(
        service_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
else:
    # 로컬 실행용
    SERVICE_ACCOUNT_FILE = "service_account.json"
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)

# ===============================================================
# 🗓️ 월별 시트 자동 생성
# ===============================================================
def get_monthly_worksheet():
    now = datetime.now()
    sheet_name = f"Answers_{now.year}_{now.month:02d}"
    headers = ["Timestamp", "Model", "Category", "Attribute", "Prompt", "Answer", "BatchDate"]

    try:
        ws = spreadsheet.worksheet(sheet_name)
        if len(ws.get_all_values()) == 0:
            ws.append_row(headers)
            print(f"⚙️ 기존 시트에 헤더 추가됨: {sheet_name}")
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols=str(len(headers)))
        ws.append_row(headers)
        print(f"✅ 새 시트 생성됨: {sheet_name}")
    return ws

ws = get_monthly_worksheet()

# ===============================================================
# 💬 GPT 호출 함수 (재시도 포함)
# ===============================================================
def call_gpt(model, prompt):
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "input": prompt,
        "temperature": 0.3,
        "max_output_tokens": 800
    }

    for attempt in range(MAX_RETRY):
        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                if "output_text" in data:
                    return data["output_text"].strip()
                else:
                    text_blocks = []
                    for o in data.get("output", []):
                        for c in o.get("content", []):
                            if "text" in c:
                                text_blocks.append(c["text"])
                    return "\n\n".join(text_blocks).strip()
            else:
                print(f"[{model}] 오류 코드: {res.status_code}")
                print(res.text)
        except Exception as e:
            print(f"[{model}] 요청 실패: {e}")
        time.sleep(2 * (attempt + 1))
    return "[오류: 응답 실패]"

# -------------------------------
# 🧾 예시 프롬프트 데이터 (테스트용)
# -------------------------------
prompts = [
    {"No": 1, "Category": "소형 세단", "Attribute": "주행감/승차감", "Prompt": "승차감 좋은 소형 세단 추천"},
    {"No": 2, "Category": "소형 세단", "Attribute": "연비·경제성", "Prompt": "연비 좋은 소형 세단 추천"},
    {"No": 3, "Category": "소형 세단", "Attribute": "디자인/스타일", "Prompt": "디자인이 세련된 소형 세단 추천"},
    {"No": 4, "Category": "소형 세단", "Attribute": "안전성/신뢰성", "Prompt": "안전한 소형 세단 추천"},
    {"No": 5, "Category": "소형 세단", "Attribute": "공간/편의성", "Prompt": "실내공간이 넉넉한 소형 세단 추천"},
    {"No": 6, "Category": "준중형 세단", "Attribute": "주행감/승차감", "Prompt": "주행 안정성이 좋은 준중형 세단 추천"},
    {"No": 7, "Category": "준중형 세단", "Attribute": "연비·경제성", "Prompt": "유지비 절약되는 준중형 세단 추천"},
    {"No": 8, "Category": "준중형 세단", "Attribute": "디자인/스타일", "Prompt": "젊은 층에게 어울리는 준중형 세단 추천"},
    {"No": 9, "Category": "준중형 세단", "Attribute": "안전성/신뢰성", "Prompt": "충돌 안전성이 높은 준중형 세단 추천"},
    {"No": 10, "Category": "준중형 세단", "Attribute": "기술/커넥티드", "Prompt": "스마트 기능이 편리한 준중형 세단 추천"},
    {"No": 11, "Category": "중형 세단", "Attribute": "주행감/승차감", "Prompt": "장거리 운전에 편한 중형 세단 추천"},
    {"No": 12, "Category": "중형 세단", "Attribute": "연비·경제성", "Prompt": "출퇴근용으로 효율적인 중형 세단 추천"},
    {"No": 13, "Category": "중형 세단", "Attribute": "디자인/스타일", "Prompt": "외관이 고급스러운 중형 세단 추천"},
    {"No": 14, "Category": "중형 세단", "Attribute": "안전성/신뢰성", "Prompt": "A/S가 좋은 중형 세단 추천"},
    {"No": 15, "Category": "중형 세단", "Attribute": "성능/파워", "Prompt": "가속력이 좋은 중형 세단 추천"},
    {"No": 16, "Category": "대형 세단", "Attribute": "주행감/승차감", "Prompt": "정숙한 대형 세단 추천"},
    {"No": 17, "Category": "대형 세단", "Attribute": "디자인/스타일", "Prompt": "디자인이 고급스러운 대형 세단 추천"},
    {"No": 18, "Category": "대형 세단", "Attribute": "공간/편의성", "Prompt": "뒷좌석이 넓은 대형 세단 추천"},
    {"No": 19, "Category": "대형 세단", "Attribute": "성능/파워", "Prompt": "엔진 출력이 강한 대형 세단 추천"},
    {"No": 20, "Category": "대형 세단", "Attribute": "안전성/신뢰성", "Prompt": "고속 주행 시 안정적인 대형 세단 추천"},
    {"No": 21, "Category": "하이브리드 세단", "Attribute": "연비·경제성", "Prompt": "연비 좋은 하이브리드 세단 추천"},
    {"No": 22, "Category": "하이브리드 세단", "Attribute": "기술/커넥티드", "Prompt": "하이브리드 시스템이 뛰어난 세단 추천"},
    {"No": 23, "Category": "하이브리드 세단", "Attribute": "주행감/승차감", "Prompt": "주행이 부드러운 하이브리드 세단 추천"},
    {"No": 24, "Category": "하이브리드 세단", "Attribute": "디자인/스타일", "Prompt": "감각적인 디자인의 하이브리드 세단 추천"},
    {"No": 25, "Category": "하이브리드 세단", "Attribute": "안전성/신뢰성", "Prompt": "신뢰할 수 있는 하이브리드 세단 추천"},
    {"No": 26, "Category": "하이브리드 세단", "Attribute": "성능/파워", "Prompt": "가속이 부드러운 하이브리드 세단 추천"},
    {"No": 27, "Category": "전기 세단", "Attribute": "연비·경제성", "Prompt": "전비가 좋은 전기 세단 추천"},
    {"No": 28, "Category": "전기 세단", "Attribute": "기술/커넥티드", "Prompt": "OTA 업데이트가 편리한 전기 세단 추천"},
    {"No": 29, "Category": "전기 세단", "Attribute": "주행감/승차감", "Prompt": "정숙하고 승차감 좋은 전기 세단 추천"},
    {"No": 30, "Category": "전기 세단", "Attribute": "디자인/스타일", "Prompt": "미래적인 디자인의 전기 세단 추천"},
    {"No": 31, "Category": "전기 세단", "Attribute": "성능/파워", "Prompt": "가속 성능이 좋은 전기 세단 추천"},
    {"No": 32, "Category": "전기 세단", "Attribute": "기술/커넥티드", "Prompt": "충전이 빠른 전기 세단 추천"},
    {"No": 33, "Category": "전기 세단", "Attribute": "연비·경제성", "Prompt": "전기 효율이 높은 세단 추천"},
    {"No": 34, "Category": "전기 세단", "Attribute": "기술/커넥티드", "Prompt": "첨단 인포테인먼트가 적용된 전기 세단 추천"},
    {"No": 35, "Category": "럭셔리 세단", "Attribute": "디자인/스타일", "Prompt": "고급스러운 외관의 럭셔리 세단 추천"},
    {"No": 36, "Category": "럭셔리 세단", "Attribute": "주행감/승차감", "Prompt": "조용하고 편안한 럭셔리 세단 추천"},
    {"No": 37, "Category": "럭셔리 세단", "Attribute": "기술/커넥티드", "Prompt": "첨단 기술이 적용된 럭셔리 세단 추천"},
    {"No": 38, "Category": "럭셔리 세단", "Attribute": "성능/파워", "Prompt": "엔진 출력이 뛰어난 럭셔리 세단 추천"},
    {"No": 39, "Category": "럭셔리 세단", "Attribute": "안전성/신뢰성", "Prompt": "신뢰성 높은 럭셔리 세단 추천"},
    {"No": 40, "Category": "스포츠 세단", "Attribute": "성능/파워", "Prompt": "가속 성능이 강력한 스포츠 세단 추천"},
    {"No": 41, "Category": "스포츠 세단", "Attribute": "디자인/스타일", "Prompt": "스포티한 디자인의 스포츠 세단 추천"},
    {"No": 42, "Category": "스포츠 세단", "Attribute": "주행감/승차감", "Prompt": "코너링이 좋은 스포츠 세단 추천"},
    {"No": 43, "Category": "스포츠 세단", "Attribute": "기술/커넥티드", "Prompt": "첨단 운전자 보조 시스템이 탑재된 스포츠 세단 추천"},
    {"No": 44, "Category": "스포츠 세단", "Attribute": "안전성/신뢰성", "Prompt": "고속 안정성이 우수한 스포츠 세단 추천"},
    {"No": 45, "Category": "스포츠 세단", "Attribute": "성능/파워", "Prompt": "스포츠 주행이 가능한 스포츠 세단 추천"},
    {"No": 46, "Category": "소형 SUV", "Attribute": "공간/편의성", "Prompt": "패밀리카로 적합한 소형 SUV 추천"},
    {"No": 47, "Category": "소형 SUV", "Attribute": "연비·경제성", "Prompt": "연비 좋은 소형 SUV 추천"},
    {"No": 48, "Category": "소형 SUV", "Attribute": "디자인/스타일", "Prompt": "감각적인 디자인의 소형 SUV 추천"},
    {"No": 49, "Category": "소형 SUV", "Attribute": "주행감/승차감", "Prompt": "승차감 좋은 소형 SUV 추천"},
    {"No": 50, "Category": "소형 SUV", "Attribute": "안전성/신뢰성", "Prompt": "안전한 소형 SUV 추천"},
    {"No": 51, "Category": "컴팩트 SUV", "Attribute": "공간/편의성", "Prompt": "트렁크 활용도가 높은 컴팩트 SUV 추천"},
    {"No": 52, "Category": "컴팩트 SUV", "Attribute": "연비·경제성", "Prompt": "효율적인 컴팩트 SUV 추천"},
    {"No": 53, "Category": "컴팩트 SUV", "Attribute": "디자인/스타일", "Prompt": "도심형 디자인의 컴팩트 SUV 추천"},
    {"No": 54, "Category": "컴팩트 SUV", "Attribute": "성능/파워", "Prompt": "가속이 부드러운 컴팩트 SUV 추천"},
    {"No": 55, "Category": "컴팩트 SUV", "Attribute": "안전성/신뢰성", "Prompt": "주행 보조 기능이 잘 적용된 컴팩트 SUV 추천"},
    {"No": 56, "Category": "중형 SUV", "Attribute": "주행감/승차감", "Prompt": "장거리 주행에 편한 중형 SUV 추천"},
    {"No": 57, "Category": "중형 SUV", "Attribute": "성능/파워", "Prompt": "견인력이 우수한 중형 SUV 추천"},
    {"No": 58, "Category": "중형 SUV", "Attribute": "공간/편의성", "Prompt": "3열 좌석이 편한 중형 SUV 추천"},
    {"No": 59, "Category": "중형 SUV", "Attribute": "디자인/스타일", "Prompt": "고급스러운 디자인의 중형 SUV 추천"},
    {"No": 60, "Category": "중형 SUV", "Attribute": "안전성/신뢰성", "Prompt": "충돌 안전성이 높은 중형 SUV 추천"},
    {"No": 61, "Category": "중형 SUV", "Attribute": "공간/편의성", "Prompt": "트렁크가 넓은 중형 SUV 추천"},
    {"No": 62, "Category": "대형 SUV", "Attribute": "성능/파워", "Prompt": "출력이 강한 대형 SUV 추천"},
    {"No": 63, "Category": "대형 SUV", "Attribute": "공간/편의성", "Prompt": "가족이 타기 좋은 대형 SUV 추천"},
    {"No": 64, "Category": "대형 SUV", "Attribute": "디자인/스타일", "Prompt": "프리미엄 감성의 대형 SUV 추천"},
    {"No": 65, "Category": "대형 SUV", "Attribute": "안전성/신뢰성", "Prompt": "고속 주행 안정성이 높은 대형 SUV 추천"},
    {"No": 66, "Category": "대형 SUV", "Attribute": "기술/커넥티드", "Prompt": "첨단 기술이 적용된 대형 SUV 추천"},
    {"No": 67, "Category": "대형 SUV", "Attribute": "공간/편의성", "Prompt": "7인 가족이 타기 좋은 대형 SUV 추천"},
    {"No": 68, "Category": "프리미엄 SUV", "Attribute": "디자인/스타일", "Prompt": "럭셔리한 디자인의 프리미엄 SUV 추천"},
    {"No": 69, "Category": "프리미엄 SUV", "Attribute": "주행감/승차감", "Prompt": "정숙하고 편안한 프리미엄 SUV 추천"},
    {"No": 70, "Category": "프리미엄 SUV", "Attribute": "성능/파워", "Prompt": "강력한 출력의 프리미엄 SUV 추천"},
    {"No": 71, "Category": "프리미엄 SUV", "Attribute": "기술/커넥티드", "Prompt": "첨단 인포테인먼트가 뛰어난 프리미엄 SUV 추천"},
    {"No": 72, "Category": "프리미엄 SUV", "Attribute": "안전성/신뢰성", "Prompt": "안전 기술이 우수한 프리미엄 SUV 추천"},
    {"No": 73, "Category": "프리미엄 SUV", "Attribute": "디자인/스타일", "Prompt": "세련된 인테리어의 프리미엄 SUV 추천"},
    {"No": 74, "Category": "전기 SUV", "Attribute": "연비·경제성", "Prompt": "전비 효율이 좋은 전기 SUV 추천"},
    {"No": 75, "Category": "전기 SUV", "Attribute": "기술/커넥티드", "Prompt": "OTA 기능이 뛰어난 전기 SUV 추천"},
    {"No": 76, "Category": "전기 SUV", "Attribute": "디자인/스타일", "Prompt": "미래지향적 디자인의 전기 SUV 추천"},
    {"No": 77, "Category": "전기 SUV", "Attribute": "성능/파워", "Prompt": "가속이 빠른 전기 SUV 추천"},
    {"No": 78, "Category": "전기 SUV", "Attribute": "공간/편의성", "Prompt": "넓은 적재공간을 가진 전기 SUV 추천"},
    {"No": 79, "Category": "전기 SUV", "Attribute": "기술/커넥티드", "Prompt": "충전 인프라가 잘 갖춰진 전기 SUV 추천"},
    {"No": 80, "Category": "전기 SUV", "Attribute": "디자인/스타일", "Prompt": "미니멀한 외관의 전기 SUV 추천"},
    {"No": 81, "Category": "하이브리드 SUV", "Attribute": "연비·경제성", "Prompt": "연비 좋은 하이브리드 SUV 추천"},
    {"No": 82, "Category": "하이브리드 SUV", "Attribute": "성능/파워", "Prompt": "출력이 부드러운 하이브리드 SUV 추천"},
    {"No": 83, "Category": "하이브리드 SUV", "Attribute": "공간/편의성", "Prompt": "패밀리카로 인기 있는 하이브리드 SUV 추천"},
    {"No": 84, "Category": "하이브리드 SUV", "Attribute": "안전성/신뢰성", "Prompt": "신뢰성 높은 하이브리드 SUV 추천"},
    {"No": 85, "Category": "하이브리드 SUV", "Attribute": "디자인/스타일", "Prompt": "감각적인 디자인의 하이브리드 SUV 추천"},
    {"No": 86, "Category": "쿠페형 SUV", "Attribute": "디자인/스타일", "Prompt": "스포티한 디자인의 쿠페형 SUV 추천"},
    {"No": 87, "Category": "쿠페형 SUV", "Attribute": "성능/파워", "Prompt": "주행 성능이 우수한 쿠페형 SUV 추천"},
    {"No": 88, "Category": "쿠페형 SUV", "Attribute": "디자인/스타일", "Prompt": "젊은 감성의 쿠페형 SUV 추천"},
    {"No": 89, "Category": "쿠페형 SUV", "Attribute": "기술/커넥티드", "Prompt": "스마트 기능이 탑재된 쿠페형 SUV 추천"},
    {"No": 90, "Category": "쿠페형 SUV", "Attribute": "연비·경제성", "Prompt": "효율적인 쿠페형 SUV 추천"},
    {"No": 91, "Category": "픽업트럭", "Attribute": "성능/파워", "Prompt": "견인력 좋은 픽업트럭 추천"},
    {"No": 92, "Category": "픽업트럭", "Attribute": "성능/파워", "Prompt": "오프로드 주행에 강한 픽업트럭 추천"},
    {"No": 93, "Category": "픽업트럭", "Attribute": "공간/편의성", "Prompt": "적재공간 활용성이 좋은 픽업트럭 추천"},
    {"No": 94, "Category": "픽업트럭", "Attribute": "디자인/스타일", "Prompt": "남성적인 디자인의 픽업트럭 추천"},
    {"No": 95, "Category": "픽업트럭", "Attribute": "안전성/신뢰성", "Prompt": "튼튼하고 안전한 픽업트럭 추천"},
    {"No": 96, "Category": "패밀리카", "Attribute": "공간/편의성", "Prompt": "가족이 타기 좋은 패밀리카 추천"},
    {"No": 97, "Category": "패밀리카", "Attribute": "안전성/신뢰성", "Prompt": "아이 동반 시 안전한 패밀리카 추천"},
    {"No": 98, "Category": "패밀리카", "Attribute": "편의성/기술", "Prompt": "패밀리 전용 편의기능이 많은 패밀리카 추천"},
    {"No": 99, "Category": "패밀리카", "Attribute": "연비·경제성", "Prompt": "유지비가 적은 패밀리카 추천"},
    {"No": 100, "Category": "패밀리카", "Attribute": "디자인/스타일", "Prompt": "가족 친화적인 디자인의 패밀리카 추천"}
]
print(f"✅ Loaded {len(prompts)} prompts")


# In[8]:


# -------------------------------
# 🚀 실행 (실시간 저장)
# -------------------------------
today = datetime.now().strftime("%Y-%m-%d")

for i, row in enumerate(prompts):
    for model in MODELS:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{i+1}/{len(prompts)}] {model} 실행 중 → {row['Category']} / {row['Attribute']}")
        
        answer = call_gpt(model, row["Prompt"])

        # ✅ 실시간 저장
        ws.append_row([
            ts,
            model,
            row["Category"],
            row["Attribute"],
            row["Prompt"],
            answer,
            today
        ], value_input_option="USER_ENTERED")

        print(f"→ 저장 완료 ({i+1}/{len(prompts)})")
        time.sleep(DELAY)

print("✅ 모든 프롬프트 처리 완료!")

