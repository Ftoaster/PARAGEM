# Paratranz 웹 번역기 🌐

**Gemini AI + Paratranz API**를 활용한 인터랙티브 게임 번역 도구

## ✨ 주요 기능

- 🤖 **Gemini AI 번역**: 2개의 번역 옵션 제공
- ✏️ **실시간 편집**: 번역 결과를 바로 수정 가능
- 📚 **용어집 관리**: 일관된 번역을 위한 용어집
- 🔒 **세션 잠금**: 여러 사용자가 동시 작업 시 충돌 방지
- 📊 **진행률 추적**: 실시간 번역 진행 상황 확인
- ⚡ **배치 번역**: 한 번에 20개씩 효율적 처리
- 🎯 **단계별 필터**: 미번역/번역완료/검토필요 선택

## 📦 필수 요구사항

- Python 3.7+
- Paratranz API 키 ([발급 링크](https://paratranz.cn/users/my))
- Google Gemini API 키 ([발급 링크](https://aistudio.google.com/app/apikey))

## 🚀 설치 및 실행

### 1. 파일 다운로드

```bash
git clone https://github.com/your-username/paratranz-web-translator.git
cd paratranz-web-translator
```

### 2. 설정 파일 생성

```bash
# Windows
copy translator_config.example.json translator_config.json

# Linux/Mac
cp translator_config.example.json translator_config.json
```

`translator_config.json`에는 프로젝트 설정만 있습니다:
```json
{
  "paratranz": {
    "project_id": 16593
  },
  "gemini": {
    "model": "gemini-2.5-flash-lite"
  }
}
```

**✅ API 키는 웹 UI에서 입력하세요!** (브라우저에 안전하게 저장됨)

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 서버 실행

**Windows:**
```bash
run_web_translator.bat
```

**Linux/Mac:**
```bash
python web_translator.py
```

브라우저가 자동으로 열리며, 웹에서 API 키를 입력할 수도 있습니다.

## 📖 사용 방법

1. **파일 선택**: 번역할 Paratranz 파일 선택
2. **단계 선택**: 미번역/번역완료/검토필요 중 선택
3. **번역 시작**: 자동으로 20개씩 배치 번역
4. **번역 선택**: 2개 옵션 중 선택 또는 편집
5. **저장**: "저장" 또는 "검토" 상태로 저장

### 키보드 단축키

- `1`, `2`: 번역 선택
- `3`: 용어집
- `4`: 건너뛰기
- **저장 단계:**
  - `1`: 저장 (번역 완료)
  - `2`: 검토 필요로 저장
  - `3`: 편집
  - `4`: 취소

## 🌐 외부 접속 (선택)

### 로컬 네트워크 (같은 Wi-Fi)

1. 방화벽 설정:
   ```bash
   allow_firewall.bat
   ```
2. 내 IP 확인:
   ```bash
   check_my_ip.bat
   ```
3. 다른 기기에서 접속:
   ```
   http://[내_IP]:5000
   ```

### 인터넷 외부 접속 (ngrok)

1. ngrok 설정:
   ```bash
   setup_ngrok.bat
   ```
2. 외부 접속용 실행:
   ```bash
   run_web_translator_external.bat
   ```

## 📁 프로젝트 구조

```
paratranz-web-translator/
├─ web_translator.py              # Flask 서버
├─ paratranz_api_translator.py    # 번역 엔진
├─ translator_config.json          # 설정 (Git 제외)
├─ translator_config.example.json  # 설정 템플릿
├─ requirements.txt                # Python 패키지
├─ run_web_translator.bat          # 실행 스크립트
├─ .gitignore                      # Git 제외 목록
└─ templates/
     └─ index.html                 # 웹 UI
```

## 🔒 보안 주의사항

- **API 키는 웹 UI에서 입력** → 브라우저 localStorage에 저장됨
- `translator_config.json`에는 API 키가 없음 (안전!)
- `.gitignore`로 자동 보호됨
- 외부 공개 시 ngrok 인증 필수

## 🤝 기여

이슈 제보 및 풀 리퀘스트 환영합니다!

## 📝 라이선스

MIT License

## 👤 제작자

개인 프로젝트 - 게임 로컬라이제이션 자동화

---

**💡 팁**: 
- Gemini 모델은 `gemini-2.5-flash-lite` (1500회/일) 추천
- 배치 크기는 `translator_config.json`에서 조정 가능
- 용어집은 웹에서 실시간으로 추가 가능

