"""
Paratranz API 자동 번역 도구 (완전 자동화, 브라우저 불필요)

기능:
1. Paratranz API로 원문 자동 가져오기
2. Gemini로 2개 번역 생성
3. 사용자 선택/편집
4. Paratranz API로 자동 저장
5. 다음 항목 자동 로드

사용 전 준비:
1. pip install requests google-generativeai
2. translator_config.json 파일 수정 (API 키 입력)
"""

import json
import os
import sys
import requests
import google.generativeai as genai
from typing import Optional, List, Dict

# ===== UTF-8 인코딩 설정 (이모지 표시용) =====
if sys.platform == 'win32':
    # Windows 콘솔 UTF-8 설정
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)
    except:
        pass
    
    # Python 표준 출력 UTF-8 설정
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

# ===== 컬러 출력 설정 (CMD에서도 이쁘게) =====
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # Windows CMD 컬러 지원
    COLOR_SUPPORT = True
except ImportError:
    # colorama가 없으면 컬러 없이 실행
    COLOR_SUPPORT = False
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""

# ===== 설정 파일 로드 =====
CONFIG_FILE = "translator_config.json"

def load_config():
    """설정 파일 로드"""
    if not os.path.exists(CONFIG_FILE):
        print(f"\n[ERROR] 설정 파일을 찾을 수 없습니다: {CONFIG_FILE}")
        print("\n📌 translator_config.json 파일을 생성하고 API 키를 입력하세요!")
        input("\nEnter를 눌러 종료...")
        sys.exit(1)
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 웹 버전에서는 API 키를 웹 UI에서 입력받으므로 체크 생략
        # (콘솔 버전에서만 필요하면 별도 체크 가능)
        
        return config
    except Exception as e:
        print(f"\n[ERROR] 설정 파일 로드 실패: {e}")
        input("\nEnter를 눌러 종료...")
        sys.exit(1)

# 설정 로드
config = load_config()

# Paratranz 설정
PARATRANZ_API_KEY = config['paratranz'].get('api_key', None)  # 웹에서 입력받음
PROJECT_ID = config['paratranz']['project_id']

# Gemini 설정
GEMINI_API_KEY = config['gemini'].get('api_key', None)  # 웹에서 입력받음
MODEL_NAME = config['gemini']['model']

# 번역 설정
SOURCE_LANG = config['translation']['source_lang']
TARGET_LANG = config['translation']['target_lang']
BATCH_SIZE = config['translation'].get('batch_size', 20)

TRANSLATION_STYLE = {
    "game_genre": config['translation']['game_genre'],
    "tone": config['translation']['tone'],
    "formality": config['translation']['formality'],
    "target_audience": config['translation']['target_audience'],
}

# 용어집 파일
GLOSSARY_FILE = "paratranz_glossary.json"

# 기본 용어집 (config에서 로드)
DEFAULT_GLOSSARY = config.get('glossary', {})

# Paratranz API 베이스 URL
PARATRANZ_BASE_URL = "https://paratranz.cn/api"


class ParatranzAPITranslator:
    def __init__(self, paratranz_key=None, gemini_key=None, model_name=None):
        self.glossary = self.load_glossary()
        self.translation_count = 0
        self.current_strings = []
        self.current_index = 0
        self.total_tokens_used = 0  # 사용한 토큰 수 추적
        self.request_count = 0  # 오늘 사용한 API 호출 횟수 추적
        
        # API 키 결정 (인자로 받으면 우선 사용, 아니면 config에서)
        paratranz_api_key = paratranz_key if paratranz_key else PARATRANZ_API_KEY
        gemini_api_key = gemini_key if gemini_key else GEMINI_API_KEY
        model_name_to_use = model_name if model_name else MODEL_NAME
        
        # Paratranz API 헤더
        self.headers = {
            "Authorization": f"Bearer {paratranz_api_key}",
            "Content-Type": "application/json"
        }
        
        # Gemini 초기화
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel(model_name_to_use)
        self.model_name = model_name_to_use
        
        # Request 한도 (모델별)
        self.request_limits = {
            "gemini-2.0-flash-exp": 50,
            "gemini-2.5-pro": 50,
            "gemini-1.5-pro": 50,
            "gemini-1.5-flash": 1500,
            "gemini-2.5-flash-lite": 1500,
            "gemini-2.5-flash": 1500,
        }
        self.daily_limit = self.request_limits.get(model_name_to_use, 1500)
        
    def load_glossary(self):
        """용어집 로드"""
        if os.path.exists(GLOSSARY_FILE):
            try:
                with open(GLOSSARY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return DEFAULT_GLOSSARY.copy()
        return DEFAULT_GLOSSARY.copy()
    
    def save_glossary(self):
        """용어집 저장"""
        with open(GLOSSARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.glossary, f, ensure_ascii=False, indent=2)
        print(f"💾 용어집 저장됨: {GLOSSARY_FILE}")
    
    def fetch_files(self) -> Optional[List[Dict]]:
        """프로젝트의 파일 목록 가져오기"""
        print("\n📁 프로젝트 파일 목록 가져오는 중...")
        
        try:
            url = f"{PARATRANZ_BASE_URL}/projects/{PROJECT_ID}/files"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                files = response.json()
                return files
            else:
                print(f"[ERROR] 파일 목록 가져오기 실패: {response.status_code}")
                return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def select_file(self) -> Optional[int]:
        """사용자가 파일 선택"""
        files = self.fetch_files()
        
        if not files:
            print("[ERROR] 파일 목록을 가져올 수 없습니다.")
            return None
        
        print("\n" + "="*70)
        print("📂 번역 가능한 파일 목록")
        print("="*70)
        
        for i, file in enumerate(files, 1):
            file_name = file.get('name', '이름 없음')
            file_id = file.get('id', '?')
            total = file.get('total', 0)
            translated = file.get('translated', 0)
            progress = (translated / total * 100) if total > 0 else 0
            
            print(f"[{i}] {file_name}")
            print(f"    ID: {file_id} | 진행률: {translated}/{total} ({progress:.1f}%)")
        
        print("="*70)
        
        while True:
            try:
                choice = input(f"\n파일 선택 (1-{len(files)}): ").strip()
                idx = int(choice) - 1
                
                if 0 <= idx < len(files):
                    selected_file = files[idx]
                    file_id = selected_file.get('id')
                    file_name = selected_file.get('name')
                    print(f"\n✅ 선택됨: {file_name} (ID: {file_id})")
                    return file_id
                else:
                    print(f"❌ 1-{len(files)} 사이의 숫자를 입력하세요")
            except ValueError:
                print("❌ 숫자를 입력하세요")
            except KeyboardInterrupt:
                return None
    
    def select_stage(self) -> Optional[int]:
        """번역 단계 선택"""
        print("\n" + "="*70)
        print("📊 번역 단계 선택")
        print("="*70)
        print("[1] 원문만 (미번역) - stage=0")
        print("[2] 번역됨 - stage=1")
        print("[3] 검토 완료 - stage=5")
        print("[0] 전체")
        print("="*70)
        
        # 사용자 선택 → Paratranz stage 매핑
        stage_mapping = {
            0: None,  # 전체
            1: 0,     # 미번역 → stage=0
            2: 1,     # 번역됨 → stage=1
            3: 5,     # 검토 완료 → stage=5
        }
        
        stage_names = {
            0: "전체",
            1: "미번역 (stage=0)",
            2: "번역됨 (stage=1)",
            3: "검토 완료 (stage=5)"
        }
        
        while True:
            try:
                choice = input("\n단계 선택 (0-3): ").strip()
                user_choice = int(choice)
                
                if 0 <= user_choice <= 3:
                    paratranz_stage = stage_mapping[user_choice]
                    print(f"\n✅ 선택됨: {stage_names[user_choice]}")
                    return paratranz_stage
                else:
                    print("❌ 0-3 사이의 숫자를 입력하세요")
            except ValueError:
                print("❌ 숫자를 입력하세요")
            except KeyboardInterrupt:
                return None
    
    def fetch_strings(self, file_id: int, stage: Optional[int] = None, page: int = 1) -> bool:
        """Paratranz에서 번역할 문자열 가져오기"""
        print(f"\n📥 Paratranz에서 원문 가져오는 중... (페이지 {page})")
        
        try:
            # API 엔드포인트
            url = f"{PARATRANZ_BASE_URL}/projects/{PROJECT_ID}/strings"
            
            # 쿼리 파라미터
            params = {
                "file": file_id,
                "page": page,
                "pageSize": 20  # 한 페이지당 20개씩
            }
            
            # 스테이지 필터 (선택사항)
            if stage is not None:
                params["stage"] = stage
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # results 또는 data 키에 문자열 배열이 있을 수 있음
                if isinstance(data, dict):
                    all_strings = data.get('results', data.get('data', []))
                elif isinstance(data, list):
                    all_strings = data
                
                total_loaded = len(all_strings)
                
                # stage 값으로 필터링
                if stage == 0:  # 미번역만 (stage=0)
                    self.current_strings = [s for s in all_strings if s.get('stage') == 0]
                    print(f"✅ 미번역 {len(self.current_strings)}개 로드 완료")
                        
                elif stage == 1:  # 번역됨만 (stage=1)
                    self.current_strings = [s for s in all_strings if s.get('stage') == 1]
                    print(f"✅ 번역됨 {len(self.current_strings)}개 로드 완료")
                    
                elif stage == 5:  # 검토 완료만 (stage=5)
                    self.current_strings = [s for s in all_strings if s.get('stage') == 5]
                    print(f"✅ 검토 완료 {len(self.current_strings)}개 로드 완료")
                    
                else:  # 전체 (stage=None)
                    self.current_strings = all_strings
                    stage_counts = {}
                    for s in all_strings:
                        st = s.get('stage', 'N/A')
                        stage_counts[st] = stage_counts.get(st, 0) + 1
                    
                    print(f"✅ {total_loaded}개 항목 로드됨")
                    print(f"   📊 Stage 0 (미번역): {stage_counts.get(0, 0)}개")
                    print(f"   📊 Stage 1 (번역됨): {stage_counts.get(1, 0)}개")
                    print(f"   📊 Stage 5 (검토완료): {stage_counts.get(5, 0)}개")
                    if len(stage_counts) > 3:
                        print(f"   📊 기타: {stage_counts}")
                
                if len(self.current_strings) == 0:
                    print("\n💡 조건에 맞는 항목이 없습니다!")
                
                return True
            else:
                print(f"[ERROR] API 요청 실패: {response.status_code}")
                print(f"응답: {response.text}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 원문 가져오기 실패: {e}")
            return False
    
    def get_current_string(self) -> Optional[Dict]:
        """현재 번역할 문자열 가져오기"""
        if 0 <= self.current_index < len(self.current_strings):
            return self.current_strings[self.current_index]
        return None
    
    def create_translation_prompt(self, text):
        """번역 프롬프트 생성"""
        glossary_items = "\n".join([f"  • {en} → {ko}" for en, ko in self.glossary.items()])
        
        prompt = f"""당신은 전문 게임 로컬라이제이션 번역가입니다.

【번역 컨텍스트】
- 게임 장르: {TRANSLATION_STYLE["game_genre"]}
- 톤앤매너: {TRANSLATION_STYLE["tone"]}
- 말투: {TRANSLATION_STYLE["formality"]}
- 타겟 유저: {TRANSLATION_STYLE["target_audience"]}

【중요 지침】
1. 게임 UI/메뉴 텍스트이므로 간결하고 직관적으로 번역
2. 고유명사(지명, 코스명 등)는 반드시 한글로 음차
3. 기술 용어도 음차 우선 (예: Saturation → 세추레이션)
4. 형식 지정자(%s, %d 등)는 그대로 유지

【용어집】
{glossary_items}

【원문】
{text}

2가지 번역을 제공하세요:
1번: 정확하고 자연스러운 번역
2번: 약간 다른 스타일의 대안 번역

형식:
1: [번역1]
2: [번역2]
"""
        return prompt
    
    def translate_batch_with_gemini(self, texts: list, retry_count=0, max_retries=3):
        """여러 개의 텍스트를 한 번에 번역 (API 호출 1번)"""
        print(f"\n🤖 AI 배치 번역 중... ({len(texts)}개)")
        
        try:
            # 배치 프롬프트 생성
            glossary_items = "\n".join([f"  • {en} → {ko}" for en, ko in self.glossary.items()])
            
            # 원문 목록 생성
            originals = "\n".join([f"원문 {i+1}: {text}" for i, text in enumerate(texts)])
            
            prompt = f"""당신은 전문 게임 로컬라이제이션 번역가입니다.

【번역 컨텍스트】
- 게임 장르: {TRANSLATION_STYLE["game_genre"]}
- 톤앤매너: {TRANSLATION_STYLE["tone"]}
- 말투: {TRANSLATION_STYLE["formality"]}
- 타겟 유저: {TRANSLATION_STYLE["target_audience"]}

【중요 지침】
1. 게임 UI/메뉴 텍스트이므로 간결하고 직관적으로 번역
2. 고유명사(지명, 코스명 등)는 반드시 한글로 음차
3. 기술 용어도 음차 우선 (예: Saturation → 세추레이션)
4. 형식 지정자(%s, %d 등)는 그대로 유지

【용어집】
{glossary_items}

【원문 목록】
{originals}

각 원문에 대해 2가지 번역을 제공하세요:
1-1: [원문1의 번역1]
1-2: [원문1의 번역2]
2-1: [원문2의 번역1]
2-2: [원문2의 번역2]
...
{len(texts)}-1: [원문{len(texts)}의 번역1]
{len(texts)}-2: [원문{len(texts)}의 번역2]

정확히 위 형식으로 {len(texts)*2}개의 번역을 제공하세요."""

            response = self.model.generate_content(prompt)
            
            # Request 카운트 증가
            self.request_count += 1
            remaining = self.daily_limit - self.request_count
            percentage = (self.request_count / self.daily_limit) * 100
            
            # 토큰 사용량 추적
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                completion_tokens = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                
                self.total_tokens_used += total_tokens
                
                print(f"   📊 토큰 사용: {prompt_tokens} (입력) + {completion_tokens} (출력) = {total_tokens} (총)")
                print(f"   📊 누적 토큰: {self.total_tokens_used:,}")
            
            # Request 한도 정보
            print(f"   🎯 API 호출: {self.request_count}/{self.daily_limit} ({percentage:.1f}%) | 남은 횟수: {remaining}")
            print(f"   💰 절약: {len(texts)-1}번의 API 호출 절약!")
            
            # 경고 표시
            if remaining <= 10:
                print(f"   ⚠️  경고: 남은 호출 횟수가 {remaining}개입니다!")
            elif remaining <= 50:
                print(f"   💡 알림: 남은 호출 횟수 {remaining}개")
            
            # 응답 파싱
            lines = response.text.strip().split('\n')
            translations_dict = {}  # {index: [translation1, translation2]}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 형식: "1-1: 번역" 또는 "1-2: 번역"
                import re
                match = re.match(r'(\d+)-([12]):\s*(.+)', line)
                if match:
                    idx = int(match.group(1)) - 1  # 0-based index
                    variant = int(match.group(2))  # 1 or 2
                    translation = match.group(3).strip()
                    
                    if idx not in translations_dict:
                        translations_dict[idx] = [None, None]
                    
                    translations_dict[idx][variant-1] = translation
            
            # 결과 리스트로 변환
            results = []
            for i in range(len(texts)):
                if i in translations_dict and translations_dict[i][0] and translations_dict[i][1]:
                    results.append(translations_dict[i])
                else:
                    # 파싱 실패 시 기본값
                    results.append([f"[번역 실패: {texts[i]}]", f"[번역 실패: {texts[i]}]"])
            
            return results
            
        except Exception as e:
            error_str = str(e)
            
            # 429 에러 (쿼터 초과) 체크
            if '429' in error_str and retry_count < max_retries:
                print(f"\n⚠️  API 쿼터 초과 (429 에러)")
                
                # retry_delay 파싱
                import re
                import time
                
                retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str, re.IGNORECASE)
                if retry_match:
                    wait_time = float(retry_match.group(1))
                else:
                    wait_time = 60
                
                print(f"⏳ {int(wait_time)}초 후 자동 재시도... ({retry_count + 1}/{max_retries})")
                print(f"   (Ctrl+C로 취소 가능)")
                
                try:
                    for remaining in range(int(wait_time), 0, -1):
                        print(f"\r   ⏱️  {remaining}초 남음...", end='', flush=True)
                        time.sleep(1)
                    print("\r   ✅ 대기 완료!           ")
                    
                    return self.translate_batch_with_gemini(texts, retry_count + 1, max_retries)
                    
                except KeyboardInterrupt:
                    print("\n\n❌ 사용자가 취소했습니다.")
                    return None
            
            print(f"\n[ERROR] 번역 실패: {e}")
            return None
    
    def translate_batch_with_gemini(self, texts: list, retry_count=0, max_retries=3):
        """배치 번역: 여러 개의 텍스트를 한 번에 번역 (API 호출 1번)"""
        print(f"\n🤖 AI 배치 번역 중... ({len(texts)}개)")
        
        try:
            # 배치 프롬프트 생성
            glossary_items = "\n".join([f"  • {en} → {ko}" for en, ko in self.glossary.items()])
            
            # 원문 목록 생성
            originals = "\n".join([f"원문 {i+1}: {text}" for i, text in enumerate(texts)])
            
            prompt = f"""당신은 전문 게임 로컬라이제이션 번역가입니다.

【번역 컨텍스트】
- 게임 장르: {TRANSLATION_STYLE["game_genre"]}
- 톤앤매너: {TRANSLATION_STYLE["tone"]}
- 말투: {TRANSLATION_STYLE["formality"]}
- 타겟 유저: {TRANSLATION_STYLE["target_audience"]}

【중요 지침】
1. 게임 UI/메뉴 텍스트이므로 간결하고 직관적으로 번역
2. 고유명사(지명, 코스명 등)는 반드시 한글로 음차
3. 기술 용어도 음차 우선 (예: Saturation → 세추레이션)
4. 형식 지정자(%s, %d, {{0}} 등)는 그대로 유지
5. HTML 태그 그대로 유지

【용어집】
{glossary_items}

【원문 목록】
{originals}

각 원문에 대해 2가지 번역을 제공하세요.
반드시 아래 형식을 정확히 따르세요:

1-1: [원문1의 번역1]
1-2: [원문1의 번역2]
2-1: [원문2의 번역1]
2-2: [원문2의 번역2]
...
{len(texts)}-1: [원문{len(texts)}의 번역1]
{len(texts)}-2: [원문{len(texts)}의 번역2]

정확히 {len(texts)*2}개의 번역을 제공하세요."""

            response = self.model.generate_content(prompt)
            
            # Request 카운트 증가
            self.request_count += 1
            remaining = self.daily_limit - self.request_count
            percentage = (self.request_count / self.daily_limit) * 100
            
            # 토큰 사용량 추적
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                completion_tokens = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                
                self.total_tokens_used += total_tokens
                
                print(f"   📊 토큰 사용: {prompt_tokens} (입력) + {completion_tokens} (출력) = {total_tokens} (총)")
                print(f"   📊 누적 토큰: {self.total_tokens_used:,}")
            
            # Request 한도 정보
            print(f"   🎯 API 호출: {self.request_count}/{self.daily_limit} ({percentage:.1f}%) | 남은 횟수: {remaining}")
            print(f"   💰 절약: {len(texts)-1}번의 API 호출 절약!")
            
            # 경고 표시
            if remaining <= 10:
                print(f"   ⚠️  경고: 남은 호출 횟수가 {remaining}개입니다!")
            elif remaining <= 50:
                print(f"   💡 알림: 남은 호출 횟수 {remaining}개")
            
            # 응답 파싱
            import re
            lines = response.text.strip().split('\n')
            translations_dict = {}  # {index: [translation1, translation2]}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 형식: "1-1: 번역" 또는 "1-2: 번역"
                match = re.match(r'(\d+)-([12]):\s*(.+)', line)
                if match:
                    idx = int(match.group(1)) - 1  # 0-based index
                    variant = int(match.group(2))  # 1 or 2
                    translation = match.group(3).strip()
                    
                    if idx not in translations_dict:
                        translations_dict[idx] = [None, None]
                    
                    translations_dict[idx][variant-1] = translation
            
            # 결과 리스트로 변환
            results = []
            for i in range(len(texts)):
                if i in translations_dict and translations_dict[i][0] and translations_dict[i][1]:
                    results.append(translations_dict[i])
                else:
                    # 파싱 실패 시 기본값
                    results.append([f"[번역 실패: {texts[i]}]", f"[번역 실패: {texts[i]}]"])
            
            return results
            
        except Exception as e:
            error_str = str(e)
            
            # 429 에러 (쿼터 초과) 체크
            if '429' in error_str and retry_count < max_retries:
                print(f"\n⚠️  API 쿼터 초과 (429 에러)")
                
                # retry_delay 파싱
                import re
                import time
                
                retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str, re.IGNORECASE)
                if retry_match:
                    wait_time = float(retry_match.group(1))
                else:
                    wait_time = 60
                
                print(f"⏳ {int(wait_time)}초 후 자동 재시도... ({retry_count + 1}/{max_retries})")
                print(f"   (Ctrl+C로 취소 가능)")
                
                try:
                    for remaining_time in range(int(wait_time), 0, -1):
                        print(f"\r   ⏱️  {remaining_time}초 남음...", end='', flush=True)
                        time.sleep(1)
                    print("\r   ✅ 대기 완료!           ")
                    
                    return self.translate_batch_with_gemini(texts, retry_count + 1, max_retries)
                    
                except KeyboardInterrupt:
                    print("\n\n❌ 사용자가 취소했습니다.")
                    return None
            
            print(f"\n[ERROR] 번역 실패: {e}")
            return None
    
    def translate_with_gemini(self, text, retry_count=0, max_retries=3):
        """Gemini로 2개 번역 생성 (자동 재시도 포함) - 개별 번역용"""
        print("\n🤖 AI 번역 중...")
        
        try:
            prompt = self.create_translation_prompt(text)
            response = self.model.generate_content(prompt)
            
            # Request 카운트 증가
            self.request_count += 1
            remaining = self.daily_limit - self.request_count
            percentage = (self.request_count / self.daily_limit) * 100
            
            # 토큰 사용량 추적
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                completion_tokens = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                
                self.total_tokens_used += total_tokens
                
                print(f"   📊 토큰 사용: {prompt_tokens} (입력) + {completion_tokens} (출력) = {total_tokens} (총)")
                print(f"   📊 누적 토큰: {self.total_tokens_used:,}")
            
            # Request 한도 정보
            print(f"   🎯 API 호출: {self.request_count}/{self.daily_limit} ({percentage:.1f}%) | 남은 횟수: {remaining}")
            
            # 경고 표시
            if remaining <= 10:
                print(f"   ⚠️  경고: 남은 호출 횟수가 {remaining}개입니다!")
            elif remaining <= 50:
                print(f"   💡 알림: 남은 호출 횟수 {remaining}개")
            
            # 응답 파싱
            lines = response.text.strip().split('\n')
            translations = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('1:') or line.startswith('1.'):
                    translations.append(line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip())
                elif line.startswith('2:') or line.startswith('2.'):
                    translations.append(line.split(':', 1)[1].strip() if ':' in line else line.split('.', 1)[1].strip())
            
            if len(translations) < 2:
                translations = [response.text.strip(), response.text.strip()]
            
            return translations[:2]
            
        except Exception as e:
            error_str = str(e)
            
            # 429 에러 (쿼터 초과) 체크
            if '429' in error_str and retry_count < max_retries:
                print(f"\n⚠️  API 쿼터 초과 (429 에러)")
                
                # retry_delay 파싱
                import re
                import time
                
                retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str, re.IGNORECASE)
                if retry_match:
                    wait_time = float(retry_match.group(1))
                else:
                    # 기본 대기 시간
                    wait_time = 60
                
                print(f"⏳ {int(wait_time)}초 후 자동 재시도... ({retry_count + 1}/{max_retries})")
                print(f"   (Ctrl+C로 취소 가능)")
                
                try:
                    # 카운트다운
                    for remaining in range(int(wait_time), 0, -1):
                        print(f"\r   ⏱️  {remaining}초 남음...", end='', flush=True)
                        time.sleep(1)
                    print("\r   ✅ 대기 완료!           ")
                    
                    # 재시도
                    return self.translate_with_gemini(text, retry_count + 1, max_retries)
                    
                except KeyboardInterrupt:
                    print("\n\n❌ 사용자가 취소했습니다.")
                    return None
            
            print(f"\n[ERROR] 번역 실패: {e}")
            return None
    
    def display_and_select(self, string_data, translations):
        """번역 결과 표시 및 선택"""
        original = string_data.get('original', string_data.get('key', ''))
        
        print("\n" + "="*70)
        print(f"📝 원문 [{self.current_index + 1}/{len(self.current_strings)}]")
        print("="*70)
        print(original)
        
        # 컨텍스트 정보 표시
        if 'context' in string_data and string_data['context']:
            print(f"\n💡 컨텍스트: {string_data['context']}")
        
        print()
        
        print("="*70)
        print("🌐 번역 결과")
        print("="*70)
        print(f"[1] {translations[0]}")
        print(f"[2] {translations[1]}")
        print("="*70)
        print()
        
        while True:
            choice = input("선택 (1/2/e=편집/r=재번역/g=용어집/s=건너뛰기/q=종료): ").strip().lower()
            
            if choice == '1':
                return translations[0], 'selected'
            elif choice == '2':
                return translations[1], 'selected'
            elif choice == 'e':
                print("\n✏️  번역 편집:")
                print(f"[1] {translations[0]}")
                print(f"[2] {translations[1]}")
                base = input("편집할 번역 선택 (1/2): ").strip()
                if base in ['1', '2']:
                    base_text = translations[int(base)-1]
                    print(f"\n현재: {base_text}")
                    edited = input("수정: ")
                    if edited:
                        return edited, 'edited'
                    return base_text, 'edited'
            elif choice == 'r':
                return None, 'retry'
            elif choice == 'g':
                self.manage_glossary()
                return None, 'retry'
            elif choice == 's':
                return None, 'skip'
            elif choice == 'q':
                return None, 'quit'
            else:
                print("잘못된 입력입니다!")
    
    def manage_glossary(self):
        """용어집 관리"""
        print("\n" + "="*70)
        print("📚 용어집 관리")
        print("="*70)
        
        while True:
            print("\n현재 용어집:")
            for i, (en, ko) in enumerate(self.glossary.items(), 1):
                print(f"  {i}. {en} → {ko}")
            
            print("\n[1] 추가  [2] 삭제  [3] 수정  [4] 완료")
            action = input("선택 (1~4): ").strip()
            
            if action == '1':
                en = input("영어 용어: ").strip()
                ko = input("한글 번역: ").strip()
                if en and ko:
                    self.glossary[en] = ko
                    self.save_glossary()
                    print(f"✅ 추가됨: {en} → {ko}")
            
            elif action == '2':
                en = input("삭제할 영어 용어: ").strip()
                if en in self.glossary:
                    del self.glossary[en]
                    self.save_glossary()
                    print(f"✅ 삭제됨: {en}")
                else:
                    print("❌ 없는 용어입니다")
            
            elif action == '3':
                en = input("수정할 영어 용어: ").strip()
                if en in self.glossary:
                    ko = input(f"새 번역 (현재: {self.glossary[en]}): ").strip()
                    if ko:
                        self.glossary[en] = ko
                        self.save_glossary()
                        print(f"✅ 수정됨: {en} → {ko}")
                else:
                    print("❌ 없는 용어입니다")
            
            elif action == '4':
                break
            else:
                print("❌ 1~4 중 선택하세요.")
    
    def save_translation(self, string_data, translation, as_review=False) -> bool:
        """Paratranz API로 번역 저장"""
        print(f"\n💾 저장 중...")
        
        try:
            string_id = string_data.get('id', string_data.get('key'))
            project_id = PROJECT_ID
            
            url = f"{PARATRANZ_BASE_URL}/projects/{project_id}/strings/{string_id}"
            
            payload = {
                "translation": translation,
                "stage": 5 if as_review else 1
            }
            
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code in [200, 204]:
                status = "검토로" if as_review else "저장"
                print(f"✅ {status} 저장 완료!")
                return True
            else:
                print(f"[ERROR] 저장 실패: {response.status_code}")
                print(f"응답: {response.text}")
                
                # 대안 시도: /strings/{id} (project 없이)
                if response.status_code == 404:
                    alt_url = f"{PARATRANZ_BASE_URL}/strings/{string_id}"
                    
                    alt_response = requests.put(alt_url, headers=self.headers, json=payload)
                    
                    if alt_response.status_code in [200, 204]:
                        status = "검토로" if as_review else "저장"
                        print(f"✅ {status} 저장 완료! (대안 경로)")
                        return True
                    else:
                        print(f"[ERROR] 대안도 실패: {alt_response.status_code}")
                        print(f"응답: {alt_response.text}")
                
                return False
                
        except Exception as e:
            print(f"[ERROR] 저장 중 오류: {e}")
            return False
    
    def run(self):
        """메인 루프"""
        print("\n" + "="*70)
        print("🚀 Paratranz API 자동 번역 (브라우저 불필요)")
        print("="*70)
        
        # API 키 확인
        if not PARATRANZ_API_KEY:
            print("\n[ERROR] Paratranz API 키가 설정되지 않았습니다!")
            print("\n📌 API 키 발급 방법:")
            print("1. https://paratranz.cn/users/my 접속")
            print("2. 'API 키' 섹션에서 키 생성")
            print("3. 파일 상단의 PARATRANZ_API_KEY에 입력")
            print()
            input("Enter를 눌러 종료...")
            return
        
        print(f"\n📊 프로젝트 ID: {PROJECT_ID}")
        print(f"🤖 AI 모델: {MODEL_NAME}")
        
        # 1. 파일 선택
        selected_file_id = self.select_file()
        if selected_file_id is None:
            print("\n❌ 파일 선택이 취소되었습니다.")
            return
        
        # 2. 스테이지 선택
        selected_stage = self.select_stage()
        if selected_stage is False:  # KeyboardInterrupt 시
            print("\n❌ 단계 선택이 취소되었습니다.")
            return
        
        # 3. 원문 가져오기
        if not self.fetch_strings(selected_file_id, selected_stage):
            return
        
        if not self.current_strings:
            print("\n❌ 번역할 항목이 없습니다!")
            return
        
        print("\n" + "="*70)
        print("💡 명령어:")
        print("  [1] 첫 번째 번역 선택")
        print("  [2] 두 번째 번역 선택")
        print("  [3] 편집")
        print("  [4] 용어집")
        print("  [5] 건너뛰기")
        print("  [6] 종료")
        print("="*70)
        
        try:
            # 🎯 배치 번역 모드
            print(f"\n💡 배치 번역 모드: {BATCH_SIZE}개씩 한 번에 번역하여 API 호출 절약!")
            print()
            
            # 배치 번역 메인 루프
            while self.current_index < len(self.current_strings):
                # 배치 준비: 현재부터 BATCH_SIZE개 수집
                batch_data = []
                batch_originals = []
                
                for i in range(BATCH_SIZE):
                    idx = self.current_index + i
                    if idx >= len(self.current_strings):
                        break
                    
                    string_data = self.current_strings[idx]
                    original = string_data.get('original', string_data.get('key', ''))
                    
                    if original:
                        batch_data.append(string_data)
                        batch_originals.append(original)
                
                if not batch_data:
                    break
                
                print(f"\n{'='*70}")
                print(f"📦 배치 {len(batch_data)}개 번역 시작 (항목 {self.current_index+1}~{self.current_index+len(batch_data)}/{len(self.current_strings)})")
                print("="*70)
                
                # 배치 번역 실행
                batch_translations = self.translate_batch_with_gemini(batch_originals)
                
                if not batch_translations:
                    print("\n[ERROR] 배치 번역 실패. 건너뜁니다.")
                    self.current_index += len(batch_data)
                    continue
                
                # 하나씩 사용자에게 표시하고 선택받기
                for i, (string_data, original, translations) in enumerate(zip(batch_data, batch_originals, batch_translations)):
                    print(f"\n{'='*70}")
                    print(f"📝 원문 [{self.current_index + 1}/{len(self.current_strings)}]")
                    print("="*70)
                    print(original)
                    
                    # 컨텍스트 정보
                    if 'context' in string_data and string_data['context']:
                        print(f"\n💡 컨텍스트: {string_data['context']}")
                    
                    print("\n" + "="*70)
                    print("🌐 번역 결과")
                    print("="*70)
                    print(f"[1] {translations[0]}")
                    print(f"[2] {translations[1]}")
                    print("="*70)
                    print()
                    
                    # 선택지 표시
                    print("[3] 편집  [4] 용어집  [5] 건너뛰기  [6] 종료")
                    print()
                    
                    # 사용자 선택
                    selected_translation = None
                    while not selected_translation:
                        choice = input("선택 (1~6): ").strip()
                        
                        if choice == '1':
                            selected_translation = translations[0]
                        elif choice == '2':
                            selected_translation = translations[1]
                        elif choice == '3':
                            print("\n✏️  번역 편집:")
                            print(f"[1] {translations[0]}")
                            print(f"[2] {translations[1]}")
                            base = input("편집할 번역 선택 (1/2): ").strip()
                            if base in ['1', '2']:
                                base_text = translations[int(base)-1]
                                print(f"\n현재: {base_text}")
                                print(f"수정: {base_text}")
                                edited = input("수정: ").strip()
                                if edited:
                                    selected_translation = edited
                                else:
                                    selected_translation = base_text
                        elif choice == '4':
                            self.manage_glossary()
                            # 재번역은 안함 (이미 배치로 번역됨)
                            print("💡 용어집 변경됨. 다음 배치부터 적용됩니다.")
                            continue
                        elif choice == '5':
                            print("\n⏭️  건너뜁니다")
                            break
                        elif choice == '6':
                            print("\n👋 종료합니다")
                            print(f"   ✅ 번역 완료: {self.translation_count}개")
                            print(f"   📊 진행: {self.current_index}/{len(self.current_strings)}")
                            print(f"   🎯 총 사용 토큰: {self.total_tokens_used:,}")
                            print(f"   🔥 API 호출: {self.request_count}/{self.daily_limit}")
                            print(f"   ⭐ 남은 횟수: {self.daily_limit - self.request_count}")
                            return
                        else:
                            print("❌ 1~6 중 선택하세요.")
                            continue
                    
                    if not selected_translation:
                        self.current_index += 1
                        continue
                    
                    # 저장
                    print(f"\n최종 번역: {selected_translation}")
                    print()
                    print("[1] 저장  [2] 검토로 저장  [3] 취소")
                    save_choice = input("선택 (1~3): ").strip()
                    
                    if save_choice == '3':
                        print("❌ 취소됨")
                    elif save_choice in ['1', '2']:
                        as_review = (save_choice == '2')
                        if self.save_translation(string_data, selected_translation, as_review):
                            self.translation_count += 1
                            print(f"✅ 저장 완료! (총 {self.translation_count}개)")
                    else:
                        print("❌ 1~3 중 선택하세요. 취소됨.")
                    
                    self.current_index += 1
                
                # 다음 배치로
                if self.current_index < len(self.current_strings):
                    input(f"\n▶ 다음 배치로 이동... (남은 항목: {len(self.current_strings) - self.current_index}개)")
            
            print(f"\n🎉 작업 완료!")
            print(f"   ✅ 번역 완료: {self.translation_count}개")
            print(f"   📊 전체: {len(self.current_strings)}개")
            print(f"   🎯 총 사용 토큰: {self.total_tokens_used:,}")
            print(f"   🔥 API 호출: {self.request_count}/{self.daily_limit} ({(self.request_count/self.daily_limit*100):.1f}%)")
            print(f"   ⭐ 남은 횟수: {self.daily_limit - self.request_count}")
            
            # 절약 계산 (배치 번역으로 절약한 호출 수)
            if self.translation_count > self.request_count:
                saved = self.translation_count - self.request_count
                print(f"   💰 절약한 API 호출: {saved}번! (배치 번역 효과)")
            
        except KeyboardInterrupt:
            print("\n\n[중단됨] Ctrl+C")
            print(f"   ✅ 번역 완료: {self.translation_count}개")
            print(f"   📊 진행: {self.current_index}/{len(self.current_strings)}")
            print(f"   🎯 총 사용 토큰: {self.total_tokens_used:,}")
            print(f"   🔥 API 호출: {self.request_count}/{self.daily_limit}")
            print(f"   ⭐ 남은 횟수: {self.daily_limit - self.request_count}")
            
            # 절약 계산
            if self.translation_count > self.request_count:
                saved = self.translation_count - self.request_count
                print(f"   💰 절약한 API 호출: {saved}번! (배치 번역 효과)")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    print("="*70)
    print("Paratranz API 자동 번역 도구")
    print("="*70)
    
    translator = ParatranzAPITranslator()
    translator.run()

