"""
Paratranz 웹 UI 번역기
Flask 기반 웹 인터페이스 + 키보드 단축키 지원
"""

from flask import Flask, render_template, jsonify, request
import threading
import webbrowser
import time
import os
import socket
from paratranz_api_translator import ParatranzAPITranslator, config, BATCH_SIZE

# ngrok 지원 (선택사항)
try:
    from pyngrok import ngrok
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False

# 스크립트 위치 기준으로 템플릿 폴더 찾기
script_dir = os.path.dirname(os.path.abspath(__file__))
# dist 폴더에서 실행되면 상위 폴더의 templates 사용
if os.path.basename(script_dir) == 'dist':
    template_folder = os.path.join(os.path.dirname(script_dir), 'templates')
else:
    template_folder = os.path.join(script_dir, 'templates')

app = Flask(__name__, template_folder=template_folder)

# 전역 번역기 인스턴스
translator = None
current_batch_translations = []
current_batch_data = []
current_item_index = 0
current_file_id = None
current_stage = None
current_page = 1

# 🔒 세션별 잠금 시스템
import time
from threading import Lock

# 잠금 데이터: {string_id: {'user': session_id, 'locked_at': timestamp}}
locked_strings = {}
lock_mutex = Lock()  # 스레드 안전성

def lock_string(string_id: int, session_id: str) -> bool:
    """문자열 잠금 시도"""
    with lock_mutex:
        current_time = time.time()
        
        # 기존 잠금 확인
        if string_id in locked_strings:
            lock_info = locked_strings[string_id]
            
            # 5분 타임아웃 (자동 해제)
            if current_time - lock_info['locked_at'] > 300:
                # 타임아웃 → 새로 잠금
                locked_strings[string_id] = {
                    'user': session_id,
                    'locked_at': current_time
                }
                return True
            
            # 같은 사용자면 OK
            if lock_info['user'] == session_id:
                return True
            
            # 다른 사용자가 잠금 중
            return False
        
        # 잠금 없음 → 새로 잠금
        locked_strings[string_id] = {
            'user': session_id,
            'locked_at': current_time
        }
        return True

def unlock_string(string_id: int, session_id: str):
    """문자열 잠금 해제"""
    with lock_mutex:
        if string_id in locked_strings:
            lock_info = locked_strings[string_id]
            # 본인 것만 해제 가능
            if lock_info['user'] == session_id:
                del locked_strings[string_id]

def get_locked_by(string_id: int) -> str:
    """누가 잠금했는지 확인"""
    with lock_mutex:
        if string_id in locked_strings:
            lock_info = locked_strings[string_id]
            current_time = time.time()
            
            # 타임아웃 체크
            if current_time - lock_info['locked_at'] > 300:
                del locked_strings[string_id]
                return None
            
            return lock_info['user']
        return None

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/session')
def get_session():
    """세션 ID 생성 (브라우저마다 고유)"""
    import uuid
    session_id = str(uuid.uuid4())
    return jsonify({'session_id': session_id})

@app.route('/api/files')
def get_files():
    """파일 목록 가져오기"""
    global translator
    
    # 사용자 API 키 받기
    paratranz_key = request.headers.get('X-Paratranz-Key')
    gemini_key = request.headers.get('X-Gemini-Key')
    gemini_model = request.headers.get('X-Gemini-Model', 'gemini-2.5-flash-lite')
    
    if not paratranz_key or not gemini_key:
        return jsonify({'success': False, 'error': 'API 키가 필요합니다'})
    
    # 새로운 번역기 인스턴스 생성 (사용자 키 사용)
    translator = ParatranzAPITranslator(
        paratranz_key=paratranz_key, 
        gemini_key=gemini_key,
        model_name=gemini_model
    )
    
    files = translator.fetch_files()
    if files:
        return jsonify({'success': True, 'files': files})
    return jsonify({'success': False, 'error': '파일 목록을 가져올 수 없습니다'})

@app.route('/api/start', methods=['POST'])
def start_translation():
    """번역 시작"""
    global translator, current_batch_translations, current_batch_data, current_item_index
    global current_file_id, current_stage, current_page
    
    # 사용자 API 키 받기
    paratranz_key = request.headers.get('X-Paratranz-Key')
    gemini_key = request.headers.get('X-Gemini-Key')
    gemini_model = request.headers.get('X-Gemini-Model', 'gemini-2.5-flash-lite')
    
    if not paratranz_key or not gemini_key:
        return jsonify({'success': False, 'error': 'API 키가 필요합니다'})
    
    data = request.json
    current_file_id = data.get('file_id')
    current_stage = data.get('stage')
    current_page = 1
    
    # 사용자 키로 번역기 생성
    translator = ParatranzAPITranslator(
        paratranz_key=paratranz_key, 
        gemini_key=gemini_key,
        model_name=gemini_model
    )
    
    # 문자열 가져오기 (결과는 translator.current_strings에 저장됨)
    success = translator.fetch_strings(current_file_id, current_stage, page=current_page)
    
    if not success or not translator.current_strings:
        return jsonify({'success': False, 'error': '가져올 문자열이 없습니다'})
    
    translator.current_index = 0
    
    # 첫 배치 번역 시작
    return next_batch()

@app.route('/api/next_batch')
def next_batch():
    """다음 배치 번역"""
    global translator, current_batch_translations, current_batch_data, current_item_index
    global current_file_id, current_stage, current_page  # current_page도 전역 변수
    
    # 안전 체크
    if not translator or not hasattr(translator, 'current_strings') or not isinstance(translator.current_strings, list):
        return jsonify({'success': False, 'error': '번역기가 초기화되지 않았습니다'})
    
    # 현재 페이지의 항목들을 모두 처리했으면 다음 페이지 로드
    if translator.current_index >= len(translator.current_strings):
        print(f"\n📄 현재 페이지({current_page}) 완료! 다음 페이지 로드 중...")
        current_page += 1
        
        # 다음 페이지 가져오기
        success = translator.fetch_strings(current_file_id, current_stage, page=current_page)
        
        if not success or not translator.current_strings or len(translator.current_strings) == 0:
            # 더 이상 항목이 없으면 완료
            print("✅ 모든 항목 번역 완료!")
            return jsonify({
                'success': True,
                'completed': True,
                'stats': {
                    'translated': translator.translation_count,
                    'total': translator.translation_count,
                    'tokens': translator.total_tokens_used,
                    'api_calls': translator.request_count,
                    'remaining': translator.daily_limit - translator.request_count
                }
            })
        
        translator.current_index = 0
        print(f"✅ 페이지 {current_page}: {len(translator.current_strings)}개 항목 로드됨")
    
    # 세션 ID 받기
    session_id = request.headers.get('X-Session-ID', 'anonymous')
    
    # 배치 데이터 수집 (잠금된 것 제외)
    batch_data = []
    batch_originals = []
    skipped_count = 0
    max_scan = 100  # 최대 100개까지 스캔
    
    while len(batch_data) < BATCH_SIZE and skipped_count < max_scan:
        idx = translator.current_index + len(batch_data) + skipped_count
        
        # 현재 페이지 끝에 도달하면 다음 페이지 시도
        if idx >= len(translator.current_strings):
            print(f"\n📄 현재 페이지 끝 도달. 다음 페이지 시도 중...")
            translator.current_index = len(translator.current_strings)  # 다음 페이지 준비
            current_page_temp = current_page + 1
            
            # 다음 페이지 가져오기
            success = translator.fetch_strings(current_file_id, current_stage, page=current_page_temp)
            
            if not success or not translator.current_strings or len(translator.current_strings) == 0:
                # 더 이상 페이지 없음
                print("📄 더 이상 가져올 항목이 없습니다")
                break
            
            # 다음 페이지로 전환
            current_page = current_page_temp
            translator.current_index = 0
            skipped_count = 0  # 카운트 리셋
            continue
        
        string_data = translator.current_strings[idx]
        string_id = string_data.get('id')
        original = string_data.get('original', string_data.get('key', ''))
        
        if not original:
            skipped_count += 1
            continue
        
        # 🔒 잠금 시도
        if lock_string(string_id, session_id):
            # 잠금 성공 → 배치에 추가
            batch_data.append(string_data)
            batch_originals.append(original)
        else:
            # 다른 사용자가 작업 중 → 건너뜀
            print(f"⏭️  항목 {string_id} 건너뜀 (다른 사용자 작업 중)")
            skipped_count += 1
    
    # 배치 데이터 확인
    if not batch_data:
        # 모든 항목이 잠금되어 있거나 더 이상 항목이 없음
        if skipped_count >= max_scan:
            return jsonify({
                'success': False, 
                'error': '모든 항목이 다른 사용자가 작업 중입니다. 잠시 후 다시 시도하세요.'
            })
        else:
            # 모든 항목 번역 완료
            print("✅ 모든 항목 번역 완료!")
            return jsonify({
                'success': True,
                'completed': True,
                'stats': {
                    'translated': translator.translation_count,
                    'total': translator.translation_count,
                    'tokens': translator.total_tokens_used,
                    'api_calls': translator.request_count,
                    'remaining': translator.daily_limit - translator.request_count
                }
            })
    
    # 인덱스 업데이트 (다음 번에는 건너뛴 항목 이후부터)
    translator.current_index += len(batch_data) + skipped_count
    
    # 배치 번역 실행
    batch_translations = translator.translate_batch_with_gemini(batch_originals)
    
    if not batch_translations:
        return jsonify({'success': False, 'error': '배치 번역 실패'})
    
    # 전역 변수에 저장
    current_batch_data = batch_data
    current_batch_translations = batch_translations
    current_item_index = 0
    
    # 첫 번째 항목 반환
    return get_current_item()

@app.route('/api/current')
def get_current_item():
    """현재 번역 항목 가져오기"""
    global current_batch_data, current_batch_translations, current_item_index
    
    if current_item_index >= len(current_batch_data):
        # 배치 완료, 다음 배치로
        return next_batch()
    
    string_data = current_batch_data[current_item_index]
    translations = current_batch_translations[current_item_index]
    original = string_data.get('original', string_data.get('key', ''))
    context = string_data.get('context', '')
    
    # 진행률 계산: 완료된 개수 + 현재 배치 내 진행
    current_progress = translator.translation_count + current_item_index + 1
    
    # 전체 개수는 대략적으로 표시 (정확한 전체 개수를 알 수 없으므로)
    # 완료된 개수 + 현재 배치 + 예상 남은 개수
    estimated_total = max(current_progress, translator.translation_count + len(current_batch_data))
    
    return jsonify({
        'success': True,
        'data': {
            'original': original,
            'context': context,
            'translations': translations,
            'current': current_progress,
            'total': estimated_total,
            'batch_progress': f"{current_item_index + 1}/{len(current_batch_data)}",
            'translation_count': translator.translation_count,
            'api_calls': translator.request_count,
            'remaining_calls': translator.daily_limit - translator.request_count,
            'tokens': translator.total_tokens_used
        }
    })

@app.route('/api/select', methods=['POST'])
def select_translation():
    """번역 선택"""
    global current_item_index, current_batch_translations, current_batch_data
    
    data = request.json
    choice = data.get('choice')  # 1, 2, 3(편집), 5(건너뛰기)
    edited_text = data.get('edited_text', '')
    session_id = request.headers.get('X-Session-ID', 'anonymous')
    
    if choice == 5:  # 건너뛰기
        # 🔓 잠금 해제
        string_data = current_batch_data[current_item_index]
        string_id = string_data.get('id')
        unlock_string(string_id, session_id)
        print(f"🔓 항목 {string_id} 잠금 해제 (건너뛰기)")
        
        current_item_index += 1
        return get_current_item()
    
    # 선택된 번역 결정
    if choice == 1:
        selected = current_batch_translations[current_item_index][0]
    elif choice == 2:
        selected = current_batch_translations[current_item_index][1]
    elif choice == 3:  # 편집
        selected = edited_text
    else:
        return jsonify({'success': False, 'error': '잘못된 선택입니다'})
    
    return jsonify({
        'success': True,
        'selected': selected,
        'show_save_options': True
    })

@app.route('/api/save', methods=['POST'])
def save_translation():
    """번역 저장"""
    global current_item_index, current_batch_data
    
    data = request.json
    translation = data.get('translation')
    save_type = data.get('save_type')  # 1=저장, 2=검토, 3=취소
    session_id = request.headers.get('X-Session-ID', 'anonymous')
    
    string_data = current_batch_data[current_item_index]
    string_id = string_data.get('id')
    
    if save_type == 3:  # 취소
        # 취소는 잠금 해제 안 함 (계속 작업 중)
        return jsonify({'success': True, 'cancelled': True})
    
    as_review = (save_type == 2)
    success = translator.save_translation(string_data, translation, as_review)
    
    if success:
        translator.translation_count += 1
        # 🔓 저장 성공 시 잠금 해제
        unlock_string(string_id, session_id)
        print(f"🔓 항목 {string_id} 잠금 해제 (저장 완료)")
    
    # 다음 항목으로
    current_item_index += 1
    
    return get_current_item()

@app.route('/api/glossary', methods=['GET', 'POST'])
def manage_glossary():
    """용어집 관리"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'glossary': translator.glossary
        })
    
    # POST - 용어집 업데이트
    data = request.json
    action = data.get('action')  # add, delete, update
    
    if action == 'add':
        en = data.get('en')
        ko = data.get('ko')
        if en and ko:
            translator.glossary[en] = ko
            translator.save_glossary()
            return jsonify({'success': True})
    
    elif action == 'delete':
        en = data.get('en')
        if en in translator.glossary:
            del translator.glossary[en]
            translator.save_glossary()
            return jsonify({'success': True})
    
    elif action == 'update':
        en = data.get('en')
        ko = data.get('ko')
        if en in translator.glossary and ko:
            translator.glossary[en] = ko
            translator.save_glossary()
            return jsonify({'success': True})
    
    return jsonify({'success': False})

def get_local_ip():
    """로컬 IP 주소 가져오기"""
    try:
        # 임시 소켓으로 IP 확인
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "IP 확인 실패"

def open_browser():
    """브라우저 자동 열기"""
    time.sleep(1)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    local_ip = get_local_ip()
    use_ngrok = os.getenv('USE_NGROK', 'false').lower() == 'true'
    
    print("="*60)
    print("🌐 Paratranz 웹 UI 번역기")
    print("="*60)
    print()
    print("🚀 서버 시작 중...")
    
    # ngrok 터널 생성 (외부 접속용)
    public_url = None
    if use_ngrok and NGROK_AVAILABLE:
        try:
            print("🌍 외부 접속 URL 생성 중... (ngrok)")
            
            # Windows 인코딩 문제 해결
            import locale
            import sys
            import subprocess
            
            if sys.platform == 'win32':
                # UTF-8 환경 설정
                os.environ['PYTHONIOENCODING'] = 'utf-8'
                os.environ['PYTHONUTF8'] = '1'  # Python 3.7+
                
                # pyngrok의 subprocess 인코딩 문제 우회
                try:
                    from pyngrok import conf
                    # ngrok 로그를 UTF-8로 처리
                    conf.get_default().log_event_callback = None
                except:
                    pass
                
                try:
                    locale.setlocale(locale.LC_ALL, '')
                except:
                    pass
            
            # ngrok 연결
            public_url = ngrok.connect(5000, bind_tls=True)
            print(f"✅ ngrok 터널 생성 완료!")
        except Exception as e:
            print(f"⚠️  ngrok 실패: {e}")
            print("   로컬 접속만 가능합니다.")
    elif use_ngrok and not NGROK_AVAILABLE:
        print("⚠️  ngrok 미설치: pip install pyngrok")
        print("   로컬 접속만 가능합니다.")
    
    print()
    print("🎮 사용법:")
    print("   - 버튼 클릭 또는 키보드 단축키 사용")
    print("   - 1/2: 번역 선택, 3: 용어집, 4: 건너뛰기")
    print("   - 저장 단계: 1: 저장, 2: 검토, 3: 편집, 4: 취소")
    print()
    print("🔗 접속 주소:")
    print(f"   💻 PC: http://localhost:5000")
    print(f"   📱 같은 WiFi: http://{local_ip}:5000")
    
    if public_url:
        print(f"   🌍 외부 인터넷: {public_url}")
        print("      (어디서나 접속 가능!)")
    
    print()
    print("⏹️  종료: Ctrl+C")
    print("="*60)
    
    # 브라우저 자동 열기
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Flask 서버 실행
    app.run(debug=False, host='0.0.0.0', port=5000)

