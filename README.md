# Paratranz 웹 번역기 🌐

> **Gemini AI + Paratranz API**를 활용한 게임 로컬라이제이션 자동화 도구

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

**Paratranz 웹 번역기**는 게임 번역 작업을 획기적으로 가속화하는 AI 기반 도구입니다. 웹 브라우저에서 간편하게 사용하며, Gemini AI가 2가지 번역 옵션을 제공하고 사용자가 선택/편집하여 Paratranz에 바로 저장합니다.

---

## 📺 주요 특징

### 🤖 AI 기반 스마트 번역
- **Gemini AI**: 2개의 고품질 번역 옵션 동시 제공
- **컨텍스트 이해**: 게임 용어, 고유명사 자동 인식
- **음차 우선**: 지명, 코스명 등을 자연스럽게 한글 음차

### ⚡ 효율적인 작업 흐름
- **배치 번역**: 한 번에 20개씩 일괄 처리
- **실시간 편집**: 번역 결과를 즉시 수정 가능
- **단계별 필터**: 미번역/번역완료/검토필요 선택
- **키보드 단축키**: 빠른 작업을 위한 숫자 키 지원

### 🔒 다중 사용자 지원
- **세션 잠금 시스템**: 여러 사용자가 동시 작업해도 충돌 방지
- **자동 타임아웃**: 5분간 미활동 시 자동 잠금 해제
- **실시간 진행률**: 번역 진행 상황 실시간 확인

### 📚 번역 품질 관리
- **용어집 관리**: 웹에서 실시간으로 용어 추가/수정
- **일관성 유지**: 동일 용어는 항상 같은 번역 사용
- **검토 모드**: "검토됨" 상태로 저장하여 추후 확인

---

## 📦 설치 및 실행

### 필수 요구사항

| 항목 | 설명 | 링크 |
|------|------|------|
| **Python** | 3.7 이상 | [다운로드](https://www.python.org/downloads/) |
| **Paratranz API 키** | 번역 데이터 접근 | [발급하기](https://paratranz.cn/users/my) |
| **Gemini API 키** | AI 번역 서비스 | [발급하기](https://aistudio.google.com/app/apikey) |

---

### 📥 1단계: 프로젝트 다운로드

**방법 1: Git 사용**
```bash
git clone https://github.com/Ftoaster/PARAGEM.git
cd PARAGEM
```

**방법 2: GitHub에서 직접 다운로드** (Git 없이)
1. https://github.com/Ftoaster/PARAGEM 페이지 방문
2. 초록색 "Code" 버튼 클릭 → "Download ZIP" 선택
3. 다운로드한 ZIP 파일을 압축 해제

---

### ⚙️ 2단계: 설정 파일 수정

`translator_config.json` 파일을 열어서 **프로젝트 ID**를 수정하세요:

```json
{
  "paratranz": {
    "project_id": 16593  // 👈 여기에 본인의 Paratranz 프로젝트 ID 입력
  }
}
```

> **💡 프로젝트 ID 찾는 방법:**  
> Paratranz 프로젝트 페이지 URL에서 확인할 수 있어요.  
> 예: `https://paratranz.cn/projects/16593` → ID는 `16593`

---

### 🚀 3단계: 실행

```cmd
run_web_translator.bat
```

- 필요한 패키지를 자동으로 설치합니다
- 브라우저가 자동으로 `http://localhost:5000`을 엽니다

---

## 📖 사용 방법

### 🎬 빠른 시작 (5분 완성)

1. **API 키 입력**
   - 웹 페이지에서 "🔑 API 키 변경" 클릭
   - Paratranz API 키, Gemini API 키 입력
   - "💾 저장하고 시작" 클릭

2. **파일 목록 불러오기**
   - "📂 파일 목록 불러오기" 클릭
   - 번역할 파일 선택

3. **번역 단계 선택**
   - 미번역 (stage=0)
   - 번역완료 (stage=1)
   - 검토됨 (stage=5)

4. **번역 시작**
   - "🚀 번역 시작" 클릭
   - 자동으로 20개씩 번역 시작

5. **번역 선택 및 저장**
   - 첫 번째 또는 두 번째 번역 선택 (`1` or `2`)
   - 편집이 필요하면 "✏️ 편집" (`3`)
   - "💾 저장" (`1`) 또는 "📝 검토" (`2`)

---

### ⌨️ 키보드 단축키

#### 번역 선택 단계
| 키 | 동작 |
|---|------|
| `1` | 첫 번째 번역 선택 |
| `2` | 두 번째 번역 선택 |
| `3` | 용어집 관리 |
| `4` | 건너뛰기 |

#### 저장 단계
| 키 | 동작 |
|---|------|
| `1` | 저장 (번역 완료) |
| `2` | 검토됨으로 저장 |
| `3` | 편집하기 |
| `4` | 취소 |

---

### 📚 용어집 관리

**용어집이란?**
특정 단어를 항상 같은 방식으로 번역하도록 지정하는 기능입니다.

**예시:**
```json
{
  "HUD": "HUD",
  "Saturation": "세추레이션",
  "Deadzone": "데드존",
  "Pass": "패스",
  "Creek": "크릭"
}
```

**추가 방법:**
1. 번역 중 "📚 용어집" (`3`) 클릭
2. 원문과 번역 입력
3. 저장 후 즉시 적용

---

## 🌐 외부 접속 설정

### 방법 1: 로컬 네트워크 (같은 Wi-Fi)

**1. 방화벽 허용 (Windows):**
```cmd
allow_firewall.bat
```

**2. 내 로컬 IP 확인:**
```cmd
check_my_ip.bat
```

**3. 다른 기기에서 접속:**
```
http://[내_IP]:5000
예: http://192.168.0.10:5000
```

> 💡 스마트폰에서도 접속 가능! (같은 Wi-Fi에 연결되어 있어야 함)

---


## 🛠️ 고급 설정

### Gemini 모델 선택

| 모델 | 일일 한도 | 속도 | 품질 | 추천 |
|------|-----------|------|------|------|
| **gemini-2.5-flash-lite** | 1500회 | 빠름 | 우수 | ⭐ **추천** |
| **gemini-2.5-flash** | 1500회 | 빠름 | 최고 | 대량 작업 |
| **gemini-2.5-pro** | 50회 | 느림 | 최고 | 소량 고품질 |

**설정 방법:**
- 웹 UI의 "🔑 API 키 변경"에서 모델 선택 드롭다운 사용

---

### 배치 크기 조정

`translator_config.json`:
```json
{
  "translation": {
    "batch_size": 20  // 👈 10 ~ 50 사이 권장
  }
}
```

- **작은 값 (10)**: 빠른 피드백, API 호출 많음
- **큰 값 (50)**: API 호출 절약, 대기 시간 증가

---

## 📁 프로젝트 구조

```
PARAGEM/
│
├─ 📜 README.md                      # 이 파일
├─ 📜 requirements.txt               # Python 패키지 목록
├─ 📜 .gitignore                     # Git 제외 목록
│
├─ ⚙️ translator_config.json          # 설정 파일 (Git 제외)
├─ ⚙️ translator_config.example.json  # 설정 템플릿
│
├─ 🐍 web_translator.py               # Flask 웹 서버
├─ 🐍 paratranz_api_translator.py    # 번역 엔진 (Gemini + Paratranz)
│
├─ 🪟 run_web_translator.bat          # Windows 실행 스크립트
│
└─ 📁 templates/
    └─ 🌐 index.html                  # 웹 UI (HTML/CSS/JS)
```

---

## ❓ 자주 묻는 질문 (FAQ)

<details>
<summary><b>Q1. API 키를 잃어버렸어요!</b></summary>

**A:** 브라우저의 개발자 도구(F12) → Application → Local Storage에서 확인 가능합니다.
- `paratranz_api_key`
- `gemini_api_key`

재발급이 필요하면:
- Paratranz: https://paratranz.cn/users/my
- Gemini: https://aistudio.google.com/app/apikey
</details>

<details>
<summary><b>Q2. "배치 데이터가 없습니다" 오류가 나요.</b></summary>

**A:** 다른 사용자가 모든 항목을 작업 중이거나, 선택한 단계에 번역할 항목이 없습니다.
- 잠시 후 다시 시도하거나
- 다른 파일/단계를 선택해보세요.
</details>

<details>
<summary><b>Q3. Gemini API 할당량이 초과되었어요.</b></summary>

**A:** 
- `gemini-2.5-pro`는 **50회/일** 제한이 있습니다.
- `gemini-2.5-flash-lite`로 변경하면 **1500회/일** 사용 가능합니다.
- 웹 UI에서 모델 변경 후 재시작하세요.
</details>

<details>
<summary><b>Q4. 다른 사람과 동시에 작업하면 충돌이 나나요?</b></summary>

**A:** 아니요! 세션 잠금 시스템으로 안전합니다.
- A가 5번 항목 작업 중 → B는 5번을 가져갈 수 없음
- 5분간 미활동 시 자동 잠금 해제
</details>

<details>
<summary><b>Q5. 용어집을 파일로 관리하고 싶어요.</b></summary>

**A:** `paratranz_glossary.json` 파일을 직접 편집하세요. (서버 호스팅하는 사람만 가능)
```json
{
  "원문": "번역",
  "Brake": "브레이크",
  "Steering": "스티어링"
}
```
서버 재시작 후 적용됩니다.
</details>

---

## 🔒 보안 및 개인정보

### 안전한 API 키 관리
- ✅ **API 키는 웹 UI에서 입력** → 브라우저 localStorage에만 저장
- ✅ **config 파일에 API 키 없음** → GitHub에 노출 위험 없음
- ✅ **`.gitignore`로 자동 보호** → `translator_config.json`은 Git에서 제외
- ⚠️ **외부 공개 시 주의** → ngrok 사용 시 URL 공유에 주의

### 데이터 처리
- 번역 데이터는 Gemini AI 서버로 전송됩니다.
- Paratranz API를 통해 번역 결과를 저장합니다.
- 로컬에는 용어집(`paratranz_glossary.json`)만 저장됩니다.

