import os
import sys
import time
import traceback

# Previne crashes de 'print()' quando o app roda via pythonw.exe (atalho sem terminal)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Força o diretório de trabalho a ser a pasta do aplicativo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR:
    try:
        os.chdir(BASE_DIR)
    except Exception:
        pass

def log_uncaught_exception(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        log_path = os.path.join(BASE_DIR, "crash_debug.log") if BASE_DIR else "crash_debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {time.ctime()} ---\n{error_msg}\n")
    except Exception:
        pass
    try:
        if sys.__excepthook__:
            sys.__excepthook__(exctype, value, tb)
    except Exception:
        pass

sys.excepthook = log_uncaught_exception

try:
    import faulthandler
    crash_log = os.path.join(BASE_DIR, "crash_debug.log") if BASE_DIR else "crash_debug.log"
    _fh_file = open(crash_log, "a", encoding="utf-8")
    faulthandler.enable(file=_fh_file)
except Exception:
    pass

import site
import json
import threading
import io
import math
import wave
import struct
import ctypes
from ctypes import wintypes
import winsound
import urllib.request
import urllib.error
import uuid
import ssl
import base64
from datetime import datetime
from pynput import keyboard as pynput_keyboard
import pyaudio

def play_beep(freq, duration):
    def _beep():
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                            QComboBox, QProgressBar, QTextEdit, QScrollArea, QFrame,
                            QSystemTrayIcon, QMenu, QDialog, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QUrl
from PyQt6.QtGui import (QPainter, QColor, QPen, QPainterPath, QAction, QIcon, 
                        QPixmap, QFont, QKeySequence, QDesktopServices, QLinearGradient, QRadialGradient)

# --- CORREÇÃO DA PLACA DE VÍDEO (cublas64_12.dll) ---
try:
    for site_pkg in site.getsitepackages():
        nvidia_dir = os.path.join(site_pkg, "nvidia")
        if os.path.exists(nvidia_dir):
            for root, dirs, files in os.walk(nvidia_dir):
                if any(f.endswith(".dll") for f in files):
                    os.add_dll_directory(root)
                    os.environ["PATH"] += os.pathsep + root
except Exception:
    pass

from faster_whisper import WhisperModel

# =============================================
# ESTADOS E CONFIGURAÇÕES (PERSISTÊNCIA DUPLA)
# =============================================
APP_VERSION = "0.28"
VERSION_URL = "https://lip.tec.br/version.txt"
RAW_CODE_URL = "https://raw.githubusercontent.com/Lipsandf/digitacaoIAlocal/main/voice_typer.py"
GITHUB_API_URL = "https://api.github.com/repos/Lipsandf/digitacaoIAlocal/contents/voice_typer.py"

# Armazenamento seguro de configurações e histórico
USER_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DigitadorIA")
try:
    os.makedirs(USER_DATA_DIR, exist_ok=True)
except Exception:
    USER_DATA_DIR = BASE_DIR

CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.json")
HISTORY_FILE = os.path.join(USER_DATA_DIR, "transcriptions_history.json")

LOCAL_CONFIG = os.path.join(BASE_DIR, "config.json")
LOCAL_HISTORY = os.path.join(BASE_DIR, "transcriptions_history.json")

MODEL_SIZE = "large-v3"
if os.path.exists("model_choice.txt"):
    try:
        with open("model_choice.txt", "r") as f:
            c = f.read().strip()
            if c: MODEL_SIZE = c
    except: pass

config = {
    "mic_index": 0,
    "shortcut_name": "ctrl+space",
    "overlay_x": -1,
    "overlay_y": -1,
    "engine": "local",                 # "local" ou "groq"
    "groq_api_key": "",
    "groq_model": "whisper-large-v3",   # "whisper-large-v3" ou "whisper-large-v3-turbo"
    "groq_quota": {}
}

# Carrega config (do APPDATA ou do diretório local)
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    except: pass
elif os.path.exists(LOCAL_CONFIG):
    try:
        with open(LOCAL_CONFIG, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    except: pass

# Migração / sincronização do histórico local existente
if not os.path.exists(HISTORY_FILE) and os.path.exists(LOCAL_HISTORY):
    try:
        with open(LOCAL_HISTORY, "r", encoding="utf-8") as f:
            hist_init = json.load(f)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist_init[:50], f, ensure_ascii=False, indent=4)
    except: pass

def save_config():
    global config
    # 1. Salva em APPDATA
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[CONFIG APPDATA ERROR] {e}", flush=True)
        
    # 2. Espelha na pasta local se possível
    try:
        with open(LOCAL_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except: pass

save_config()

# =============================================
# SINAIS GLOBAIS
# =============================================
class WorkerSignals(QObject):
    history_updated = pyqtSignal()
    hide_overlay = pyqtSignal()
    mic_level_signal = pyqtSignal(int)
    update_result_signal = pyqtSignal(str)
    engine_changed = pyqtSignal(str)
    quota_updated = pyqtSignal(dict)
    groq_test_result = pyqtSignal(bool, str)
    toggle_recording_signal = pyqtSignal()

signals = WorkerSignals()

# =============================================
# AUTO-UPDATE OBRIGATÓRIO, DESACOPLADO E SILENCIOSO
# =============================================
is_updating = False
update_required = False

def check_for_updates(manual=False, auto_force=False):
    global is_updating, update_required
    if is_updating:
        return
    try:
        url = f"{VERSION_URL}?t={int(time.time())}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=6) as response:
            remote_ver = response.read().decode('utf-8').strip()
        
        print(f"[AUTO-UPDATE] Versao local: {APP_VERSION} | Versao Servidor: {remote_ver}", flush=True)
        if remote_ver and remote_ver != APP_VERSION:
            update_required = True
            signals.update_result_signal.emit(f"🚀 Atualizar para v{remote_ver} (Clique aqui)")
            
            # Só fecha e roda o updater quando clicado manualmente
            if manual:
                is_updating = True
                signals.update_result_signal.emit(f"⏳ Atualizando para v{remote_ver}...")
                print(f"[AUTO-UPDATE] Disparando updater para v{remote_ver}...", flush=True)
                
                # Prepara o script updater.ps1 em %TEMP%
                temp_dir = os.environ.get("TEMP", "C:/Temp")
                temp_updater = os.path.join(temp_dir, "DigitadorIA_updater.ps1")
                
                updater_code = ""
                try:
                    upd_api = "https://api.github.com/repos/Lipsandf/digitacaoIAlocal/contents/updater.ps1"
                    api_req = urllib.request.Request(upd_api, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(api_req, context=ctx, timeout=6) as api_resp:
                        data = json.loads(api_resp.read().decode('utf-8'))
                        updater_code = base64.b64decode(data['content']).decode('utf-8')
                except: pass
                
                if not updater_code and os.path.exists(os.path.join(BASE_DIR, "updater.ps1")):
                    try:
                        with open(os.path.join(BASE_DIR, "updater.ps1"), "r", encoding="utf-8") as f:
                            updater_code = f.read()
                    except: pass
                    
                if updater_code:
                    try:
                        with open(temp_updater, "w", encoding="utf-8") as f:
                            f.write(updater_code)
                    except: pass
                
                target_dir = os.path.abspath(BASE_DIR)
                ps_args = f'-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{temp_updater}" -TargetDir "{target_dir}"'
                
                # Dispara com elevação RunAs para atualizar em Program Files
                ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", ps_args, None, 0)
                time.sleep(1.0)
                os._exit(0)
        else:
            update_required = False
            if manual:
                signals.update_result_signal.emit(f"✅ Versão v{APP_VERSION} é a mais recente!")
            else:
                signals.update_result_signal.emit(f"🔄 Versão v{APP_VERSION}")
    except Exception as e:
        print(f"[AUTO-UPDATE] Falha ao verificar versao: {e}", flush=True)
        if manual:
            signals.update_result_signal.emit("❌ Erro ao conectar ao servidor.")
        is_updating = False

# =============================================
# INTEGRAÇÃO GROQ CLOUD API (NATIVO URLLIB)
# =============================================
def parse_groq_rate_limits(headers):
    quota = {}
    for key, val in headers.items():
        k = key.lower()
        if k == "x-ratelimit-remaining-requests":
            try: quota["remaining_requests"] = int(val)
            except: quota["remaining_requests"] = val
        elif k == "x-ratelimit-limit-requests":
            try: quota["limit_requests"] = int(val)
            except: quota["limit_requests"] = val
        elif k == "x-ratelimit-reset-requests":
            quota["reset_requests"] = val
        elif k == "x-ratelimit-remaining-tokens":
            try: quota["remaining_tokens"] = int(val)
            except: quota["remaining_tokens"] = val
        elif k == "x-ratelimit-limit-tokens":
            try: quota["limit_tokens"] = int(val)
            except: quota["limit_tokens"] = val
        elif k == "x-ratelimit-reset-tokens":
            quota["reset_tokens"] = val
    quota["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return quota

def test_groq_api_key(api_key):
    if not api_key or not api_key.strip():
        return False, "Chave de API não informada.", {}
    
    clean_key = api_key.strip()
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "User-Agent": f"DigitadorIA/{APP_VERSION}"
    }
    
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            quota = parse_groq_rate_limits(resp.info())
            if not quota.get("remaining_requests"):
                quota["remaining_requests"] = 14400
                quota["limit_requests"] = 14400
                quota["reset_requests"] = "24h"
            quota["last_check"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            return True, "Chave válida! Conexão com Groq OK.", quota
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Chave de API inválida ou expirada (Erro 401).", {}
        return False, f"Erro HTTP {e.code}: {e.reason}", {}
    except Exception as e:
        return False, f"Erro de conexão com a Groq: {e}", {}

def transcribe_with_groq(audio_wav_bytes, api_key, model="whisper-large-v3", prompt="", language="pt"):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    def add_field(name, value):
        nonlocal body
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))

    def add_file(name, filename, file_bytes, content_type="audio/wav"):
        nonlocal body
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")

    add_field("model", model)
    add_field("language", language)
    add_field("temperature", "0.0")
    add_field("response_format", "verbose_json")
    if prompt:
        add_field("prompt", prompt)
    add_file("file", "speech.wav", audio_wav_bytes, "audio/wav")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": f"DigitadorIA/{APP_VERSION}"
    }

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
            quota_info = parse_groq_rate_limits(response.info())
            resp_data = json.loads(response.read().decode("utf-8"))
            text = resp_data.get("text", "").strip()
            return {"success": True, "text": text, "quota": quota_info}
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_content)
            err_msg = err_json.get("error", {}).get("message", str(e))
        except Exception:
            err_msg = str(e)
        return {"success": False, "error": err_msg, "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e), "code": -1}

# =============================================
# GERENCIADOR DE MICROFONE
# =============================================
class MicTestManager:
    def __init__(self):
        self.p = None
        self.stream = None
        self.current_mic_index = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        try:
            import numpy as np
            samples = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(samples ** 2)))
            val = min(100, int((rms / 3500.0) * 100))
            signals.mic_level_signal.emit(val)
        except Exception:
            signals.mic_level_signal.emit(0)
        return (None, pyaudio.paContinue)

    def start_test(self, mic_index):
        self.stop_test()
        if mic_index is None or is_recording:
            return
        
        self.current_mic_index = mic_index
        try:
            if self.p is None:
                self.p = pyaudio.PyAudio()
            
            try:
                info = self.p.get_device_info_by_index(mic_index)
                sample_rate = int(info.get("defaultSampleRate", 44100))
            except Exception:
                sample_rate = 16000

            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
        except Exception as e:
            print(f"[DEBUG MIC] Nao foi possivel abrir mic {mic_index}: {e}", flush=True)
            signals.mic_level_signal.emit(0)

    def stop_test(self):
        signals.mic_level_signal.emit(0)
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception: pass
            self.stream = None
        if self.p is not None:
            try:
                self.p.terminate()
            except Exception: pass
            self.p = None

# =============================================
# GERENCIADOR DINÂMICO DE MEMÓRIA DA IA (LAZY LOAD & AUTO-UNLOAD)
# =============================================
model = None
model_lock = threading.Lock()
model_loading = False
model_ready_event = threading.Event()
model_last_used_time = 0.0
MODEL_IDLE_TIMEOUT = 300.0  # Descarrega da memória após 5 minutos (300 segundos) de inatividade

is_recording = False
is_transcribing = False
audio_queue = []
last_context = ""
current_rms = 0.0
hotkey_listener = None
cuda_driver_warning = False

def ensure_model_loaded(async_mode=False):
    """
    Inicia o carregamento do modelo de IA se não estiver carregado.
    Se async_mode=True, executa em thread de fundo (ex: enquanto o usuário fala).
    Se async_mode=False, aguarda até carregar e retorna o modelo.
    """
    global model, model_loading, model_ready_event, model_last_used_time
    
    model_last_used_time = time.time()
    
    with model_lock:
        if model is not None:
            return model
        if not model_loading:
            model_loading = True
            model_ready_event.clear()
            
            def _loader():
                global model, model_loading, cuda_driver_warning
                try:
                    print(f"[IA MANAGER] Carregando modelo Whisper ({MODEL_SIZE}) na memória...", flush=True)
                    loaded = None
                    # Tenta CUDA FP16
                    try:
                        loaded = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
                        print("[IA MANAGER] Modelo carregado na GPU NVIDIA via CUDA (FP16)!", flush=True)
                    except Exception:
                        # Tenta CUDA INT8
                        try:
                            loaded = WhisperModel(MODEL_SIZE, device="cuda", compute_type="int8")
                            print("[IA MANAGER] Modelo carregado na GPU NVIDIA via CUDA (INT8)!", flush=True)
                        except Exception:
                            # Tenta CUDA FLOAT32
                            try:
                                loaded = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float32")
                                print("[IA MANAGER] Modelo carregado na GPU NVIDIA via CUDA (FLOAT32)!", flush=True)
                            except Exception as e_f32:
                                err_msg = str(e_f32).lower()
                                if "insufficient" in err_msg or "driver" in err_msg:
                                    cuda_driver_warning = True
                    
                    # Fallback CPU
                    if loaded is None:
                        print("[IA MANAGER] Utilizando processamento em CPU...", flush=True)
                        import multiprocessing
                        total_cores = multiprocessing.cpu_count()
                        smart_threads = max(1, total_cores - 2) if total_cores > 4 else total_cores
                        try:
                            loaded = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=smart_threads)
                        except Exception:
                            try:
                                loaded = WhisperModel(MODEL_SIZE, device="cpu", compute_type="float32", cpu_threads=smart_threads)
                            except Exception as e3:
                                print(f"[IA MANAGER] Falha ao carregar modelo na CPU: {e3}", flush=True)
                    
                    with model_lock:
                        model = loaded
                        model_loading = False
                        model_ready_event.set()
                        print("[IA MANAGER] Modelo pronto para uso imediato!", flush=True)
                except Exception as ex:
                    print(f"[IA MANAGER] Erro inesperado ao carregar modelo: {ex}", flush=True)
                    with model_lock:
                        model_loading = False
                        model_ready_event.set()

            threading.Thread(target=_loader, daemon=True).start()

    if not async_mode:
        model_ready_event.wait(timeout=30.0)
        return model
    return None

def unload_model_if_idle():
    """
    Descarrega o modelo da memória (RAM/VRAM) se estiver inativo há mais de MODEL_IDLE_TIMEOUT segundos.
    """
    global model, model_loading
    with model_lock:
        if model is not None and not model_loading and not is_recording and not is_transcribing:
            idle_seconds = time.time() - model_last_used_time
            if idle_seconds >= MODEL_IDLE_TIMEOUT:
                print(f"[IA MANAGER] Inativo por {int(idle_seconds)}s. Liberando memória RAM/VRAM...", flush=True)
                del model
                model = None
                import gc
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
                print("[IA MANAGER] Memória liberada com sucesso. IA colocada em standby!", flush=True)

def force_unload_model():
    """Força o descarregamento imediato (ex: ao trocar para modo Groq Cloud)."""
    global model, model_loading
    with model_lock:
        if model is not None and not is_recording and not is_transcribing:
            print("[IA MANAGER] Descarregando modelo local imediatamente...", flush=True)
            del model
            model = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

def recording_thread_func():
    global is_recording, audio_queue, current_rms
    
    CHUNK = 1024
    p = pyaudio.PyAudio()
    
    try:
        device_info = p.get_device_info_by_index(config["mic_index"])
        SAMPLE_RATE = int(device_info.get("defaultSampleRate", 44100))
    except:
        SAMPLE_RATE = 44100

    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, 
                        input=True, input_device_index=config["mic_index"], frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Erro ao abrir stream de gravacao: {e}")
        is_recording = False
        p.terminate()
        signals.hide_overlay.emit()
        return
    
    audio_queue = []
    
    while is_recording:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_queue.append(data)
            
            import numpy as np
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            current_rms = float(np.sqrt(np.mean(samples ** 2)))
        except:
            pass
            
    stream.stop_stream()
    stream.close()
    p.terminate()
    current_rms = 0
    
    if len(audio_queue) > 10:
        transcribe_and_type(audio_queue, SAMPLE_RATE)
    else:
        signals.hide_overlay.emit()

def transcribe_and_type(buffer, sample_rate):
    global last_context, is_transcribing, overlay_instance, model_last_used_time
    
    model_last_used_time = time.time()
    engine = config.get("engine", "local")
    groq_key = config.get("groq_api_key", "").strip()

    raw_data = b''.join(buffer)
    target_rate = 16000
    
    # Reamostragem para 16kHz
    if sample_rate != target_rate and len(raw_data) > 0:
        try:
            import numpy as np
            samples = np.frombuffer(raw_data, dtype=np.int16)
            if len(samples) > 0:
                duration = len(samples) / float(sample_rate)
                target_length = int(duration * target_rate)
                orig_indices = np.linspace(0, len(samples) - 1, len(samples))
                target_indices = np.linspace(0, len(samples) - 1, target_length)
                resampled_samples = np.interp(target_indices, orig_indices, samples).astype(np.int16)
                raw_data = resampled_samples.tobytes()
                sample_rate = target_rate
        except Exception as e_resample:
            print(f"[DEBUG MIC] Erro ao reamostrar audio: {e_resample}", flush=True)

    buf = io.BytesIO()
    p = pyaudio.PyAudio()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(raw_data)
    audio_wav_bytes = buf.getvalue()
    buf.seek(0)
    p.terminate()
    
    text = ""
    
    try:
        play_beep(800, 80)
        
        # --- 1. MODO GROQ CLOUD ---
        if engine == "groq" and groq_key:
            groq_m = config.get("groq_model", "whisper-large-v3")
            print(f"[TRANSCRIÇÃO] Enviando para Groq Cloud ({groq_m})...", flush=True)
            res = transcribe_with_groq(
                audio_wav_bytes, 
                groq_key, 
                model=groq_m, 
                prompt=last_context if last_context else ""
            )
            
            if res["success"]:
                text = res["text"]
                if res.get("quota"):
                    config["groq_quota"] = res["quota"]
                    save_config()
                    signals.quota_updated.emit(res["quota"])
            else:
                print(f"[GROQ ERROR] {res.get('error')}. Tentando fallback local...", flush=True)
                play_beep(500, 150)
                fallback_model = ensure_model_loaded(async_mode=False)
                if fallback_model is not None:
                    buf.seek(0)
                    segments, _ = fallback_model.transcribe(
                        buf, beam_size=5, language="pt",
                        condition_on_previous_text=True,
                        initial_prompt=last_context if last_context else None,
                        vad_filter=True
                    )
                    text = "".join([s.text for s in segments]).strip()
        
        # --- 2. MODO LOCAL (OU FALLBACK) ---
        else:
            active_model = ensure_model_loaded(async_mode=False)
            if active_model is not None:
                buf.seek(0)
                segments, _ = active_model.transcribe(
                    buf, beam_size=5, language="pt",
                    condition_on_previous_text=True,
                    initial_prompt=last_context if last_context else None,
                    vad_filter=True
                )
                text = "".join([s.text for s in segments]).strip()
            else:
                print("[IA MANAGER] Falha: modelo local indisponível.", flush=True)
                play_beep(400, 200)
        
        # Digitação automática
        if text:
            from pynput.keyboard import Controller
            k = Controller()
            k.type(text + " ")
            last_context = (last_context + " " + text).strip()[-120:]
            
            # Salva no histórico (limite estrito de 50 transcrições)
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            history_data = []
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except: pass
            elif os.path.exists(LOCAL_HISTORY):
                try:
                    with open(LOCAL_HISTORY, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except: pass
            
            tag = "⚡ Groq" if (engine == "groq" and groq_key) else "🖥️ Local"
            history_data.insert(0, {"time": now, "text": text, "engine": tag})
            history_data = history_data[:50] # Limite exato de 50 transcrições
            
            try:
                os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, ensure_ascii=False, indent=4)
            except: pass
            
            try:
                with open(LOCAL_HISTORY, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, ensure_ascii=False, indent=4)
            except: pass
                
            signals.history_updated.emit()
    except Exception as e:
        print(f"Erro na transcrição: {e}", flush=True)
    finally:
        is_transcribing = False
        signals.hide_overlay.emit()

# =============================================
# OVERLAY: ONDAS HARMÔNICAS NEON (ESTILO SIRI / LASER GLOW)
# =============================================
class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        self.width_ = 520
        self.height_ = 140
        self.resize(self.width_, self.height_)
        
        if config["overlay_x"] != -1:
            self.move(config["overlay_x"], config["overlay_y"])
        else:
            screen_geo = QApplication.primaryScreen().geometry()
            x = (screen_geo.width() - self.width_) // 2
            y = screen_geo.height() - self.height_ - 80
            self.move(x, y)
            
        self._is_dragging = False
        self._drag_pos = None
        self.frame_count = 0
        self.smoothed_amp = 5.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(25)  # 40 FPS super fluido

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            config["overlay_x"] = self.x()
            config["overlay_y"] = self.y()
            save_config()
            event.accept()

    def update_animation(self):
        if not self._is_dragging:
            self.frame_count += 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        cy = h / 2.0
        
        # Fundo Translúcido com efeito Vidro Escuro e borda suave
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor(10, 10, 22, 215))
        bg_grad.setColorAt(1.0, QColor(16, 14, 30, 235))
        painter.setPen(QPen(QColor(120, 100, 240, 50), 1))
        painter.setBrush(bg_grad)
        painter.drawRoundedRect(4, 4, w - 8, h - 8, 16, 16)
        
        # Badge de Motor Ativo no topo
        engine = config.get("engine", "local")
        is_groq = (engine == "groq" and bool(config.get("groq_api_key", "").strip()))
        badge_text = "⚡ GROQ CLOUD" if is_groq else "🖥️ IA LOCAL"
        badge_color = QColor("#0284c7") if is_groq else QColor("#7c3aed")
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(badge_color)
        painter.drawRoundedRect(w - 130, 12, 115, 22, 11, 11)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(w - 130, 12, 115, 22, Qt.AlignmentFlag.AlignCenter, badge_text)
        
        # Status de áudio no canto esquerdo
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        if is_transcribing:
            painter.setPen(QColor("#38bdf8" if is_groq else "#c4b5fd"))
            dots = "." * ((self.frame_count // 8) % 4)
            painter.drawText(18, 28, f"⚡ Transcrevendo áudio{dots}")
        else:
            painter.setPen(QColor("#34d399"))
            painter.drawText(18, 28, "🎙️ Ouvindo voz... Fale agora")

        # Tela de Transcrição com Pulso Radiante
        if is_transcribing:
            pulse = math.sin(self.frame_count * 0.15) * 8
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(56, 189, 248, 40) if is_groq else QColor(167, 139, 250, 40))
            painter.drawEllipse(int(w/2 - 24 - pulse/2), int(cy - 24 - pulse/2), int(48 + pulse), int(48 + pulse))
            
            painter.setPen(QPen(QColor("#38bdf8" if is_groq else "#a78bfa"), 3.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            angle = (self.frame_count * 12) % 360
            painter.drawArc(int(w/2 - 16), int(cy - 16), 32, 32, -angle * 16, 240 * 16)
            return

        # FÍSICA E SUAVIZAÇÃO DA AMPLITUDE DE VOZ (LERP)
        vol = current_rms if is_recording else 0
        base_idle = 18.0 + math.sin(self.frame_count * 0.08) * 3.0
        if is_recording:
            vol_boost = min(42.0, (vol / 25.0))
            target_amp = base_idle + vol_boost
        else:
            target_amp = base_idle
            
        self.smoothed_amp = self.smoothed_amp * 0.65 + target_amp * 0.35
        amp = self.smoothed_amp

        # ONDAS HARMÔNICAS MULTICAMADAS ESTILO SILK / LASER NEON
        t = self.frame_count * 0.04
        points = 120
        dx = (w - 30) / float(points - 1)
        
        # 4 Feixes Harmônicos com Cores Vibrantes (Magenta, Ciano, Violeta, Laranja Solar)
        wave_ribbons = [
            {"color": QColor(255, 30, 140), "freq": 2.2, "speed": 1.4, "sub_freq": 4.5, "amp_mult": 1.0, "sub_amp": 0.35, "phase_shift": 0.0},
            {"color": QColor(0, 220, 255),  "freq": 1.8, "speed": -1.1, "sub_freq": 3.8, "amp_mult": 0.85, "sub_amp": 0.4, "phase_shift": 1.8},
            {"color": QColor(168, 85, 247), "freq": 2.6, "speed": 0.9, "sub_freq": 5.2, "amp_mult": 0.75, "sub_amp": 0.3, "phase_shift": 3.2},
            {"color": QColor(255, 140, 0),  "freq": 3.0, "speed": -1.6, "sub_freq": 6.0, "amp_mult": 0.65, "sub_amp": 0.25, "phase_shift": 4.5},
        ]
        
        for ribbon in wave_ribbons:
            base_col = ribbon["color"]
            
            # Para cada fita, desenhamos 3 filamentos paralelos (Strands) para efeito Silk Waves
            for strand_i in range(3):
                strand_offset = (strand_i - 1) * 0.18
                strand_alpha = 190 if strand_i == 1 else 115
                
                path = QPainterPath()
                first = True
                
                for i in range(points):
                    x = 15 + i * dx
                    norm_x = float(i) / (points - 1)
                    
                    # Envelope de Sino Suave (Transição orgânica para zero nas pontas)
                    envelope = math.sin(norm_x * math.pi) ** 1.8
                    
                    # Equação de Harmônicos Compostos
                    p1 = (norm_x * ribbon["freq"] * 2.0 * math.pi) + (t * ribbon["speed"]) + ribbon["phase_shift"] + strand_offset
                    p2 = (norm_x * ribbon["sub_freq"] * 2.0 * math.pi) - (t * ribbon["speed"] * 1.3)
                    
                    y_disp = (math.sin(p1) * ribbon["amp_mult"] + math.sin(p2) * ribbon["sub_amp"]) * amp * envelope
                    y = cy + y_disp
                    
                    if first:
                        path.moveTo(x, y)
                        first = False
                    else:
                        path.lineTo(x, y)
                
                # Pass 1: Aura Neon Difusa Larga
                if strand_i == 1:
                    painter.setPen(QPen(QColor(base_col.red(), base_col.green(), base_col.blue(), 35), 9))
                    painter.drawPath(path)
                    painter.setPen(QPen(QColor(base_col.red(), base_col.green(), base_col.blue(), 75), 4.5))
                    painter.drawPath(path)
                
                # Pass 2: Filamento Principal Vibrante
                painter.setPen(QPen(QColor(base_col.red(), base_col.green(), base_col.blue(), strand_alpha), 1.8))
                painter.drawPath(path)
                
                # Pass 3: Núcleo Laser Branco (Glow Core nos picos da voz)
                if strand_i == 1 and is_recording and vol > 70:
                    painter.setPen(QPen(QColor(255, 255, 255, 160), 1.0))
                    painter.drawPath(path)

# =============================================
# CAPTURADOR DE ATALHO (Dialog)
# =============================================
class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pressione o Atalho")
        self.setFixedSize(300, 150)
        self.setStyleSheet("background-color: #1a1a2e; color: white;")
        
        layout = QVBoxLayout()
        self.lbl = QLabel("Pressione a combinação de teclas agora...", self)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.lbl)
        self.setLayout(layout)
        
        self.key_name = ""

    def keyPressEvent(self, event):
        mods = event.modifiers()
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return 
            
        name_parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            name_parts.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            name_parts.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            name_parts.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            name_parts.append("win")
            
        key_str = QKeySequence(key).toString().lower()
        if key_str:
            name_parts.append(key_str)
        
        self.key_name = "+".join(name_parts)
        self.accept()

# =============================================
# JANELA PRINCIPAL (DASHBOARD)
# =============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Digitador IA - Dashboard (v{APP_VERSION})")
        self.resize(920, 620)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f1b; } 
            QWidget { font-family: 'Segoe UI'; color: #e5e7eb; background-color: #0f0f1b; } 
            QFrame { background-color: #1a1a2e; border-radius: 8px; }
            QLineEdit { background-color: #161622; border: 1px solid #7c3aed; border-radius: 5px; padding: 8px; color: #ffffff; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #38bdf8; }
            QComboBox { background-color: #161622; border: 1px solid #7c3aed; border-radius: 5px; padding: 8px; font-size: 13px; }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame { background-color: #161622; border-radius: 0px; } 
            QPushButton { background-color: transparent; border: none; padding: 12px; font-size: 14px; text-align: left; border-radius: 5px; } 
            QPushButton:hover { background-color: #7c3aed; color: #ffffff; }
        """)
        side_layout = QVBoxLayout(sidebar)
        
        lbl_logo = QLabel("🎙️ Digitador IA")
        lbl_logo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_logo.setStyleSheet("color: #a78bfa; padding: 15px; background-color: transparent;")
        lbl_logo.setWordWrap(False)
        side_layout.addWidget(lbl_logo)
        
        btn_tut = QPushButton("📖 Tutorial")
        btn_engine = QPushButton("⚡ Motor de IA (Groq/Local)")
        btn_mic = QPushButton("🎤 Microfone")
        btn_short = QPushButton("⌨️ Atalho")
        btn_hist = QPushButton("📜 Histórico")
        btn_hide = QPushButton("⬇️ Ocultar (Bandeja)")
        
        side_layout.addWidget(btn_tut)
        side_layout.addWidget(btn_engine)
        side_layout.addWidget(btn_mic)
        side_layout.addWidget(btn_short)
        side_layout.addWidget(btn_hist)
        side_layout.addStretch()
        
        self.btn_version = QPushButton(f"🔄 Versão v{APP_VERSION}")
        self.btn_version.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_version.setStyleSheet("QPushButton { background-color: #1a1a2e; color: #a78bfa; border: 1px solid #7c3aed; border-radius: 5px; padding: 8px; margin: 5px; font-weight: bold; } QPushButton:hover { background-color: #7c3aed; color: #ffffff; }")
        self.btn_version.clicked.connect(self.manual_check_update)
        side_layout.addWidget(self.btn_version)
        
        lbl_credits = QLabel('Desenvolvido por Felipe<br><a href="https://lip.tec.br" style="color: #a78bfa; text-decoration: none;">https://lip.tec.br</a><br><a href="mailto:felipe@lip.tec.br" style="color: #a78bfa; text-decoration: none;">felipe@lip.tec.br</a>')
        lbl_credits.setFont(QFont("Segoe UI", 9))
        lbl_credits.setStyleSheet("color: #6b7280; padding: 10px; background-color: transparent;")
        lbl_credits.setOpenExternalLinks(True)
        side_layout.addWidget(lbl_credits)
        
        side_layout.addWidget(btn_hide)
        main_layout.addWidget(sidebar)
        
        # --- STACK DE PÁGINAS ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # 1. PÁGINA INICIAL / TUTORIAL INTERATIVO (Index 0)
        page_tut = QWidget()
        l_tut = QVBoxLayout(page_tut)
        l_tut.setSpacing(10)
        l_tut.setContentsMargins(15, 15, 15, 15)
        
        # Cabeçalho Hero com Status ao Vivo
        head_row = QHBoxLayout()
        title_tut = QLabel("🎙️ Bem-vindo ao Digitador IA")
        title_tut.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_tut.setStyleSheet("color: #ffffff; background: transparent;")
        
        self.badge_status = QLabel("🟢 Sistema Pronto")
        self.badge_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.badge_status.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #059669; border-radius: 12px; padding: 4px 12px;")
        
        head_row.addWidget(title_tut)
        head_row.addStretch()
        head_row.addWidget(self.badge_status)
        l_tut.addLayout(head_row)
        
        sub_tut = QLabel("Ditado por voz inteligente com transcrição instantânea e digitação automática em qualquer aplicativo.")
        sub_tut.setFont(QFont("Segoe UI", 11))
        sub_tut.setStyleSheet("color: #9ca3af; margin-bottom: 4px; background: transparent;")
        l_tut.addWidget(sub_tut)
        
        self.banner_cuda = QLabel("⚠️ ATENÇÃO: Seu driver NVIDIA está desatualizado. Usando modo CPU. Atualize o driver ou use Groq Cloud para transcrição ultrarrápida.")
        self.banner_cuda.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.banner_cuda.setWordWrap(True)
        self.banner_cuda.setStyleSheet("background-color: #7c2d12; color: #fde047; padding: 10px; border-radius: 6px; border: 1px solid #eab308;")
        self.banner_cuda.setVisible(False)
        l_tut.addWidget(self.banner_cuda)
        
        # Grid de 3 Passos Visuais
        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(10)
        
        # Card 1: Atalho
        step1 = QFrame()
        step1.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1b4b, stop:1 #161622); border: 1px solid #4338ca; border-radius: 10px; padding: 10px; }")
        l_s1 = QVBoxLayout(step1)
        lbl_s1_t = QLabel("1️⃣ Posicione o Cursor")
        lbl_s1_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_s1_t.setStyleSheet("color: #a5b4fc; background: transparent;")
        lbl_s1_desc = QLabel("Clique onde deseja digitar (Word, WhatsApp, Navegador) e pressione o atalho:")
        lbl_s1_desc.setWordWrap(True)
        lbl_s1_desc.setFont(QFont("Segoe UI", 9))
        lbl_s1_desc.setStyleSheet("color: #cbd5e1; background: transparent;")
        self.lbl_step_key = QLabel(f"⌨️  {config.get('shortcut_name', 'ctrl+space').upper()}")
        self.lbl_step_key.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_step_key.setStyleSheet("background-color: #312e81; color: #e0e7ff; border: 1px solid #6366f1; border-radius: 6px; padding: 6px 10px;")
        self.lbl_step_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_s1.addWidget(lbl_s1_t)
        l_s1.addWidget(lbl_s1_desc)
        l_s1.addStretch()
        l_s1.addWidget(self.lbl_step_key)
        
        # Card 2: Falar
        step2 = QFrame()
        step2.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #082f49, stop:1 #161622); border: 1px solid #0284c7; border-radius: 10px; padding: 10px; }")
        l_s2 = QVBoxLayout(step2)
        lbl_s2_t = QLabel("2️⃣ Fale Naturalmente")
        lbl_s2_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_s2_t.setStyleSheet("color: #38bdf8; background: transparent;")
        lbl_s2_desc = QLabel("Fale normalmente. Uma onda luminosa na tela acompanha a captação da sua voz.")
        lbl_s2_desc.setWordWrap(True)
        lbl_s2_desc.setFont(QFont("Segoe UI", 9))
        lbl_s2_desc.setStyleSheet("color: #cbd5e1; background: transparent;")
        badge_s2 = QLabel("🌊 Onda Luminosa Ativa")
        badge_s2.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        badge_s2.setStyleSheet("background-color: #0c4a6e; color: #7dd3fc; border: 1px solid #0284c7; border-radius: 6px; padding: 6px 10px;")
        badge_s2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_s2.addWidget(lbl_s2_t)
        l_s2.addWidget(lbl_s2_desc)
        l_s2.addStretch()
        l_s2.addWidget(badge_s2)
        
        # Card 3: Digitação Instantânea
        step3 = QFrame()
        step3.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #064e3b, stop:1 #161622); border: 1px solid #059669; border-radius: 10px; padding: 10px; }")
        l_s3 = QVBoxLayout(step3)
        lbl_s3_t = QLabel("3️⃣ Digitação Instantânea")
        lbl_s3_t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_s3_t.setStyleSheet("color: #34d399; background: transparent;")
        lbl_s3_desc = QLabel("Pressione o atalho novamente para finalizar. O texto é digitado na hora onde estiver o cursor.")
        lbl_s3_desc.setWordWrap(True)
        lbl_s3_desc.setFont(QFont("Segoe UI", 9))
        lbl_s3_desc.setStyleSheet("color: #cbd5e1; background: transparent;")
        badge_s3 = QLabel("⚡ < 0.3s Resposta Instantânea")
        badge_s3.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        badge_s3.setStyleSheet("background-color: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 6px; padding: 6px 10px;")
        badge_s3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_s3.addWidget(lbl_s3_t)
        l_s3.addWidget(lbl_s3_desc)
        l_s3.addStretch()
        l_s3.addWidget(badge_s3)
        
        steps_layout.addWidget(step1)
        steps_layout.addWidget(step2)
        steps_layout.addWidget(step3)
        l_tut.addLayout(steps_layout)
        
        # Playground de Digitação Interativo
        test_card = QFrame()
        test_card.setStyleSheet("QFrame { background-color: #161622; border: 1px solid #7c3aed; border-radius: 10px; padding: 10px; }")
        l_tc = QVBoxLayout(test_card)
        l_tc.setSpacing(8)
        
        th_row = QHBoxLayout()
        lbl_tc_title = QLabel("🧪 Playground de Digitação ao Vivo")
        lbl_tc_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_tc_title.setStyleSheet("color: #c4b5fd; background: transparent;")
        
        self.btn_mic_test_toggle = QPushButton("🎤 Gravar Teste")
        self.btn_mic_test_toggle.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_mic_test_toggle.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 5px; padding: 6px 14px;")
        self.btn_mic_test_toggle.clicked.connect(self.toggle_recording)
        
        self.btn_copy_test = QPushButton("📋 Copiar")
        self.btn_copy_test.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_copy_test.setStyleSheet("background-color: #1e1b4b; color: #a5b4fc; border: 1px solid #4338ca; border-radius: 5px; padding: 5px 10px;")
        self.btn_copy_test.clicked.connect(lambda: QApplication.clipboard().setText(self.test_box.toPlainText()))
        
        self.btn_clear_test = QPushButton("🗑️ Limpar")
        self.btn_clear_test.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_clear_test.setStyleSheet("background-color: #1e1b4b; color: #f87171; border: 1px solid #991b1b; border-radius: 5px; padding: 5px 10px;")
        self.btn_clear_test.clicked.connect(lambda: self.test_box.clear())
        
        th_row.addWidget(lbl_tc_title)
        th_row.addStretch()
        th_row.addWidget(self.btn_mic_test_toggle)
        th_row.addWidget(self.btn_copy_test)
        th_row.addWidget(self.btn_clear_test)
        l_tc.addLayout(th_row)
        
        self.test_box = QTextEdit()
        self.test_box.setFixedHeight(110)
        self.test_box.setPlaceholderText("Clique aqui e pressione seu atalho (ou clique em 'Gravar Teste') para testar a transcrição...")
        self.test_box.setStyleSheet("""
            QTextEdit {
                background-color: #0f0f1b;
                border: 1px solid #374151;
                border-radius: 6px;
                font-size: 14px;
                color: #f3f4f6;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 1px solid #a78bfa;
            }
        """)
        self.test_box.textChanged.connect(self.update_test_stats)
        l_tc.addWidget(self.test_box)
        
        tf_row = QHBoxLayout()
        self.lbl_test_stats = QLabel("0 palavras • 0 caracteres")
        self.lbl_test_stats.setFont(QFont("Segoe UI", 9))
        self.lbl_test_stats.setStyleSheet("color: #6b7280; background: transparent;")
        
        lbl_test_hint = QLabel("💡 Dica: Todas as transcrições são salvas na aba 📜 Histórico.")
        lbl_test_hint.setFont(QFont("Segoe UI", 9))
        lbl_test_hint.setStyleSheet("color: #a78bfa; background: transparent;")
        
        tf_row.addWidget(self.lbl_test_stats)
        tf_row.addStretch()
        tf_row.addWidget(lbl_test_hint)
        l_tc.addLayout(tf_row)
        
        l_tut.addWidget(test_card)
        
        # Barra Inferior de Atalhos Rápidos
        footer_quick = QHBoxLayout()
        footer_quick.setSpacing(8)
        
        self.pill_engine = QPushButton("⚡ Motor: Groq Cloud")
        self.pill_engine.setStyleSheet("QPushButton { background-color: #1a1a2e; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #0c4a6e; }")
        self.pill_engine.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        
        self.pill_mic = QPushButton("🎤 Configurar Microfone")
        self.pill_mic.setStyleSheet("QPushButton { background-color: #1a1a2e; color: #34d399; border: 1px solid #059669; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #064e3b; }")
        self.pill_mic.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        
        self.pill_shortcut = QPushButton(f"⌨️ Atalho: {config.get('shortcut_name', 'ctrl+space')}")
        self.pill_shortcut.setStyleSheet("QPushButton { background-color: #1a1a2e; color: #a78bfa; border: 1px solid #7c3aed; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #312e81; }")
        self.pill_shortcut.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        
        footer_quick.addWidget(self.pill_engine)
        footer_quick.addWidget(self.pill_mic)
        footer_quick.addWidget(self.pill_shortcut)
        footer_quick.addStretch()
        l_tut.addLayout(footer_quick)
        
        l_tut.addStretch()
        self.stack.addWidget(page_tut)
        
        # 2. PÁGINA MOTOR DE IA (Index 1)
        page_engine = QWidget()
        l_engine = QVBoxLayout(page_engine)
        
        title_engine = QLabel("Motor de Transcrição (IA)")
        title_engine.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        l_engine.addWidget(title_engine, alignment=Qt.AlignmentFlag.AlignTop)
        
        desc_engine = QLabel("Escolha entre processamento 100% offline no seu computador ou transcrição ultrarrápida na nuvem via Groq Cloud.")
        desc_engine.setFont(QFont("Segoe UI", 11))
        desc_engine.setStyleSheet("color: #9ca3af; margin-bottom: 8px;")
        l_engine.addWidget(desc_engine)
        
        # CARDS DE SELEÇÃO DE MOTOR
        cards_layout = QHBoxLayout()
        
        # Card IA Local
        self.card_local = QFrame()
        self.card_local.setCursor(Qt.CursorShape.PointingHandCursor)
        l_cl = QVBoxLayout(self.card_local)
        lbl_loc_t = QLabel("🖥️ IA Local (Offline)")
        lbl_loc_t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_loc_t.setStyleSheet("color: #a78bfa; background: transparent;")
        lbl_loc_desc = QLabel("• 100% Privado (Sem internet)\n• Whisper executado no seu PC\n• Recomendado para GPUs fortes")
        lbl_loc_desc.setFont(QFont("Segoe UI", 10))
        lbl_loc_desc.setStyleSheet("color: #9ca3af; background: transparent;")
        self.btn_select_local = QPushButton("Ativar Modo Local")
        self.btn_select_local.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        l_cl.addWidget(lbl_loc_t)
        l_cl.addWidget(lbl_loc_desc)
        l_cl.addStretch()
        l_cl.addWidget(self.btn_select_local)
        
        # Card Groq Cloud
        self.card_groq = QFrame()
        self.card_groq.setCursor(Qt.CursorShape.PointingHandCursor)
        l_cg = QVBoxLayout(self.card_groq)
        lbl_groq_t = QLabel("⚡ Groq Cloud (Nuvem)")
        lbl_groq_t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_groq_t.setStyleSheet("color: #38bdf8; background: transparent;")
        lbl_groq_desc = QLabel("• Transcrição Instantânea (<0.3s)\n• Zero uso de CPU e Memória RAM\n• Requer internet e Chave Grátis")
        lbl_groq_desc.setFont(QFont("Segoe UI", 10))
        lbl_groq_desc.setStyleSheet("color: #9ca3af; background: transparent;")
        self.btn_select_groq = QPushButton("Ativar Groq Cloud")
        self.btn_select_groq.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        l_cg.addWidget(lbl_groq_t)
        l_cg.addWidget(lbl_groq_desc)
        l_cg.addStretch()
        l_cg.addWidget(self.btn_select_groq)
        
        cards_layout.addWidget(self.card_local)
        cards_layout.addWidget(self.card_groq)
        l_engine.addLayout(cards_layout)
        
        # Permite clicar em qualquer lugar dos cards para selecionar
        def select_local_handler(event=None):
            self.set_engine("local")
            if event:
                try: event.accept()
                except: pass
            
        def select_groq_handler(event=None):
            self.set_engine("groq")
            if event:
                try: event.accept()
                except: pass

        self.card_local.mousePressEvent = select_local_handler
        self.card_groq.mousePressEvent = select_groq_handler
        self.btn_select_local.clicked.connect(lambda: select_local_handler())
        self.btn_select_groq.clicked.connect(lambda: select_groq_handler())
        
        # PAINEL DE CONFIGURAÇÕES DA GROQ
        self.groq_settings_box = QFrame()
        self.groq_settings_box.setStyleSheet("background-color: #161622; border: 1px solid #38bdf8; padding: 12px; border-radius: 8px;")
        l_gs = QVBoxLayout(self.groq_settings_box)
        
        lbl_gs_title = QLabel("🔑 Configurações da Groq Cloud")
        lbl_gs_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_gs_title.setStyleSheet("color: #38bdf8; background: transparent;")
        l_gs.addWidget(lbl_gs_title)
        
        # Campo API Key
        key_layout = QHBoxLayout()
        self.input_groq_key = QLineEdit()
        self.input_groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_groq_key.setPlaceholderText("Cole sua Chave de API aqui (gsk_...)")
        self.input_groq_key.setText(config.get("groq_api_key", ""))
        self.input_groq_key.textChanged.connect(self.on_groq_key_changed)
        
        self.btn_toggle_eye = QPushButton("👁️")
        self.btn_toggle_eye.setFixedWidth(36)
        self.btn_toggle_eye.setStyleSheet("background-color: #1a1a2e; border: 1px solid #7c3aed; border-radius: 5px; font-size: 14px;")
        self.btn_toggle_eye.clicked.connect(self.toggle_key_visibility)
        
        self.btn_test_groq = QPushButton("🧪 Testar Chave")
        self.btn_test_groq.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; border-radius: 5px; padding: 8px 12px;")
        self.btn_test_groq.clicked.connect(self.test_groq_connection)
        
        self.btn_get_groq_key = QPushButton("🌐 Criar Chave Grátis")
        self.btn_get_groq_key.setStyleSheet("background-color: #1a1a2e; color: #38bdf8; border: 1px solid #38bdf8; font-weight: bold; border-radius: 5px; padding: 8px 12px;")
        self.btn_get_groq_key.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://console.groq.com/keys")))
        
        key_layout.addWidget(self.input_groq_key)
        key_layout.addWidget(self.btn_toggle_eye)
        key_layout.addWidget(self.btn_test_groq)
        key_layout.addWidget(self.btn_get_groq_key)
        l_gs.addLayout(key_layout)
        
        self.lbl_groq_status = QLabel("")
        self.lbl_groq_status.setFont(QFont("Segoe UI", 10))
        self.lbl_groq_status.setStyleSheet("background: transparent;")
        l_gs.addWidget(self.lbl_groq_status)
        
        # Seleção de Modelo Groq
        model_row = QHBoxLayout()
        lbl_mod = QLabel("Modelo Groq:")
        lbl_mod.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_mod.setStyleSheet("background: transparent;")
        self.combo_groq_model = QComboBox()
        self.combo_groq_model.addItem("whisper-large-v3 (Qualidade Máxima de Estúdio)", "whisper-large-v3")
        self.combo_groq_model.addItem("whisper-large-v3-turbo (Velocidade Extrema)", "whisper-large-v3-turbo")
        cur_mod = config.get("groq_model", "whisper-large-v3")
        for mi in range(self.combo_groq_model.count()):
            if self.combo_groq_model.itemData(mi) == cur_mod:
                self.combo_groq_model.setCurrentIndex(mi)
        self.combo_groq_model.currentIndexChanged.connect(self.on_groq_model_changed)
        model_row.addWidget(lbl_mod)
        model_row.addWidget(self.combo_groq_model)
        model_row.addStretch()
        l_gs.addLayout(model_row)
        
        # Card de Cota ao Vivo
        quota_card = QFrame()
        quota_card.setStyleSheet("background-color: #1a1a2e; border: 1px solid #374151; padding: 12px; border-radius: 6px; margin-top: 5px;")
        l_qc = QVBoxLayout(quota_card)
        
        q_head = QHBoxLayout()
        lbl_qc_t = QLabel("📊 Status da sua Cota Groq:")
        lbl_qc_t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_qc_t.setStyleSheet("color: #a78bfa; background: transparent;")
        self.btn_refresh_quota = QPushButton("🔄 Atualizar Cota")
        self.btn_refresh_quota.setStyleSheet("background-color: #2e1065; color: #c4b5fd; border: 1px solid #7c3aed; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
        self.btn_refresh_quota.clicked.connect(self.test_groq_connection)
        q_head.addWidget(lbl_qc_t)
        q_head.addStretch()
        q_head.addWidget(self.btn_refresh_quota)
        l_qc.addLayout(q_head)
        
        self.quota_bar = QProgressBar()
        self.quota_bar.setFixedHeight(18)
        self.quota_bar.setRange(0, 100)
        self.quota_bar.setValue(100)
        self.quota_bar.setTextVisible(False)
        self.quota_bar.setStyleSheet("""
            QProgressBar { background-color: #161622; border-radius: 9px; border: 1px solid #374151; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #38bdf8); border-radius: 8px; }
        """)
        l_qc.addWidget(self.quota_bar)
        
        self.lbl_quota_details = QLabel("Clique em 'Testar Chave' para consultar o status da cota.")
        self.lbl_quota_details.setFont(QFont("Segoe UI", 9))
        self.lbl_quota_details.setStyleSheet("color: #9ca3af; background: transparent; padding-top: 4px;")
        l_qc.addWidget(self.lbl_quota_details)
        
        l_gs.addWidget(quota_card)
        l_engine.addWidget(self.groq_settings_box)
        l_engine.addStretch()
        self.stack.addWidget(page_engine)
        
        # 3. PÁGINA MICROFONE (Index 2)
        page_mic = QWidget()
        l_mic = QVBoxLayout(page_mic)
        title_mic = QLabel("Configuração de Microfone")
        title_mic.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        l_mic.addWidget(title_mic, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setStyleSheet("background-color: #1a1a2e; padding: 8px; font-size: 14px; border: 1px solid #7c3aed;")
        
        mics = self.get_mics()
        for idx, name in mics:
            self.mic_combo.addItem(name, idx)
            if idx == config["mic_index"]:
                self.mic_combo.setCurrentText(name)
                
        self.mic_combo.activated.connect(self.change_mic)
        l_mic.addWidget(self.mic_combo)
        
        l_mic.addWidget(QLabel("Teste de Áudio (Fale algo para ver a barra verde):"))
        self.mic_prog = QProgressBar()
        self.mic_prog.setTextVisible(False)
        self.mic_prog.setStyleSheet("QProgressBar { background-color: #1a1a2e; border-radius: 5px; } QProgressBar::chunk { background-color: #10b981; }")
        l_mic.addWidget(self.mic_prog)
        l_mic.addStretch()
        self.stack.addWidget(page_mic)
        
        # 4. PÁGINA ATALHO (Index 3)
        page_short = QWidget()
        l_short = QVBoxLayout(page_short)
        title_short = QLabel("Configuração de Atalho Global")
        title_short.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        l_short.addWidget(title_short, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.lbl_current_sc = QLabel(f"Atalho Atual: {config['shortcut_name']}")
        self.lbl_current_sc.setFont(QFont("Segoe UI", 15))
        l_short.addWidget(self.lbl_current_sc)
        
        btn_cap = QPushButton("Capturar Novo Atalho")
        btn_cap.setFixedSize(200, 42)
        btn_cap.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 5px; font-weight: bold; font-size: 14px;")
        btn_cap.clicked.connect(self.capture_shortcut)
        l_short.addWidget(btn_cap)
        l_short.addStretch()
        self.stack.addWidget(page_short)
        
        # 5. PÁGINA HISTÓRICO (Index 4)
        page_hist = QWidget()
        l_hist = QVBoxLayout(page_hist)
        
        top_hist = QHBoxLayout()
        title_hist = QLabel("Histórico de Transcrições")
        title_hist.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        top_hist.addWidget(title_hist)
        
        btn_clear = QPushButton("🗑️ Apagar Tudo")
        btn_clear.setStyleSheet("background-color: #ef4444; color: white; border-radius: 5px; padding: 8px 12px; font-weight: bold;")
        btn_clear.clicked.connect(self.clear_history)
        top_hist.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)
        l_hist.addLayout(top_hist)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        hist_container = QWidget()
        hist_container.setObjectName("histContainer")
        hist_container.setStyleSheet("QWidget#histContainer { background-color: transparent; }")
        
        self.hist_layout = QVBoxLayout(hist_container)
        self.hist_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(hist_container)
        l_hist.addWidget(scroll)
        self.stack.addWidget(page_hist)
        
        # Botões de Navegação Sidebar
        btn_tut.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_engine.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_mic.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_short.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        btn_hist.clicked.connect(lambda: [self.stack.setCurrentIndex(4), self.load_history()])
        btn_hide.clicked.connect(self.hide)

        # Conexão de Sinais
        signals.history_updated.connect(self.load_history)
        signals.mic_level_signal.connect(self.mic_prog.setValue)
        signals.update_result_signal.connect(self.update_result_handler)
        signals.engine_changed.connect(self.update_engine_ui)
        signals.quota_updated.connect(self.render_quota_ui)
        signals.groq_test_result.connect(self.on_groq_test_finished)
        signals.toggle_recording_signal.connect(self.toggle_recording)
        
        self.mic_tester = MicTestManager()
        self.stack.currentChanged.connect(self.on_page_changed)
        
        # Inicializa a UI do motor e cota
        self.update_engine_ui(config.get("engine", "local"))
        if config.get("groq_quota"):
            self.render_quota_ui(config["groq_quota"])
            
        # Timer de Verificação Periódica de Atualizações (A cada 15 minutos)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(lambda: threading.Thread(target=lambda: check_for_updates(auto_force=True), daemon=True).start())
        self.update_timer.start(15 * 60 * 1000)

        # Timer inteligente de liberação de memória após 60s de inatividade (roda a cada 10s)
        self.idle_memory_timer = QTimer(self)
        self.idle_memory_timer.timeout.connect(unload_model_if_idle)
        self.idle_memory_timer.start(10000)

    def manual_check_update(self):
        self.btn_version.setText("⏳ Verificando...")
        threading.Thread(target=lambda: check_for_updates(manual=True), daemon=True).start()

    def update_result_handler(self, msg):
        self.btn_version.setText(msg)

    def on_page_changed(self, index):
        if hasattr(self, 'mic_tester'):
            if index == 2:
                self.mic_tester.start_test(config.get("mic_index", None))
            else:
                self.mic_tester.stop_test()
        
    def showEvent(self, event):
        super().showEvent(event)
        if cuda_driver_warning:
            self.banner_cuda.setVisible(True)
        if not hasattr(self, '_hotkey_registered'):
            self.register_native_hotkey()
            self._hotkey_registered = True

    # --- MÉTODOS GROQ E SELEÇÃO DE MOTOR ---
    def set_engine(self, new_engine):
        global config
        try:
            config["engine"] = new_engine
            save_config()
            self.update_engine_ui(new_engine)
            if new_engine == "groq":
                threading.Thread(target=force_unload_model, daemon=True).start()
        except Exception as e:
            print(f"[SET ENGINE ERROR] {e}", flush=True)

    def update_engine_ui(self, engine):
        try:
            if engine == "groq":
                self.card_groq.setStyleSheet("QFrame { background-color: #0c4a6e; border: 2px solid #38bdf8; border-radius: 8px; padding: 12px; }")
                self.btn_select_groq.setText("✅ Modo Groq Cloud ATIVO")
                self.btn_select_groq.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; border-radius: 5px; padding: 10px; border: none;")
                
                self.card_local.setStyleSheet("QFrame { background-color: #161622; border: 1px solid #374151; border-radius: 8px; padding: 12px; }")
                self.btn_select_local.setText("👉 Ativar Modo Local")
                self.btn_select_local.setStyleSheet("background-color: #1a1a2e; color: #a78bfa; border: 1px solid #7c3aed; font-weight: bold; border-radius: 5px; padding: 10px;")
                
                if hasattr(self, 'pill_engine'):
                    self.pill_engine.setText("⚡ Motor: Groq Cloud (Nuvem)")
                    self.pill_engine.setStyleSheet("QPushButton { background-color: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #0369a1; }")
                if hasattr(self, 'badge_status'):
                    self.badge_status.setText("⚡ Groq Cloud Ativo")
                    self.badge_status.setStyleSheet("background-color: #082f49; color: #38bdf8; border: 1px solid #0284c7; border-radius: 12px; padding: 4px 12px;")
            else:
                self.card_local.setStyleSheet("QFrame { background-color: #3b0764; border: 2px solid #a78bfa; border-radius: 8px; padding: 12px; }")
                self.btn_select_local.setText("✅ Modo Local ATIVO")
                self.btn_select_local.setStyleSheet("background-color: #7c3aed; color: white; font-weight: bold; border-radius: 5px; padding: 10px; border: none;")
                
                self.card_groq.setStyleSheet("QFrame { background-color: #161622; border: 1px solid #374151; border-radius: 8px; padding: 12px; }")
                self.btn_select_groq.setText("👉 Ativar Groq Cloud")
                self.btn_select_groq.setStyleSheet("background-color: #1a1a2e; color: #38bdf8; border: 1px solid #38bdf8; font-weight: bold; border-radius: 5px; padding: 10px;")
                
                if hasattr(self, 'pill_engine'):
                    self.pill_engine.setText("🖥️ Motor: IA Local (Whisper)")
                    self.pill_engine.setStyleSheet("QPushButton { background-color: #3b0764; color: #c4b5fd; border: 1px solid #7c3aed; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #581c87; }")
                if hasattr(self, 'badge_status'):
                    self.badge_status.setText("🖥️ IA Local Ativo")
                    self.badge_status.setStyleSheet("background-color: #2e1065; color: #c4b5fd; border: 1px solid #7c3aed; border-radius: 12px; padding: 4px 12px;")
            
            if hasattr(self, 'tray_menu_update_callback') and self.tray_menu_update_callback:
                self.tray_menu_update_callback()
        except Exception as e:
            print(f"[UPDATE ENGINE UI ERROR] {e}", flush=True)

    def update_test_stats(self):
        try:
            text = self.test_box.toPlainText()
            words = len(text.split()) if text.strip() else 0
            chars = len(text)
            self.lbl_test_stats.setText(f"{words:,} palavras • {chars:,} caracteres")
        except Exception: pass

    def toggle_key_visibility(self):
        if self.input_groq_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_groq_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_eye.setText("🔒")
        else:
            self.input_groq_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_eye.setText("👁️")

    def on_groq_key_changed(self, text):
        clean_key = text.strip()
        config["groq_api_key"] = clean_key
        save_config()

    def on_groq_model_changed(self, index):
        mod = self.combo_groq_model.itemData(index)
        if mod:
            config["groq_model"] = mod
            save_config()

    def test_groq_connection(self):
        key = self.input_groq_key.text().strip()
        config["groq_api_key"] = key
        save_config()
        
        self.lbl_groq_status.setText("⏳ Conectando aos servidores da Groq...")
        self.lbl_groq_status.setStyleSheet("color: #fde047; background: transparent;")
        
        def run_test():
            success, msg, quota = test_groq_api_key(key)
            signals.groq_test_result.emit(success, msg)
            if success and quota:
                config["groq_quota"] = quota
                save_config()
                signals.quota_updated.emit(quota)
                
        threading.Thread(target=run_test, daemon=True).start()

    def on_groq_test_finished(self, success, msg):
        if success:
            self.lbl_groq_status.setText(f"✅ {msg}")
            self.lbl_groq_status.setStyleSheet("color: #10b981; background: transparent; font-weight: bold;")
        else:
            self.lbl_groq_status.setText(f"❌ {msg}")
            self.lbl_groq_status.setStyleSheet("color: #ef4444; background: transparent; font-weight: bold;")

    def render_quota_ui(self, quota):
        if not quota:
            return
        rem = quota.get("remaining_requests")
        lim = quota.get("limit_requests")
        reset_t = quota.get("reset_requests", "24h")
        last_c = quota.get("last_check", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        self.quota_bar.setRange(0, 100)
        
        if rem is not None and lim is not None and lim > 0:
            try:
                pct = max(0, min(100, int((float(rem) / float(lim)) * 100)))
            except:
                pct = 100
            self.quota_bar.setValue(pct)
            self.lbl_quota_details.setText(f"🟢 Cota Disponível: {pct}% ({rem:,} de {lim:,} requisições restantes hoje) | Reset em: {reset_t} (Última checagem: {last_c})")
        else:
            self.quota_bar.setValue(100)
            self.lbl_quota_details.setText(f"🟢 Cota Ativa: 100% Disponível | Status: Conectado à Groq Cloud (Checado em: {last_c})")

    def toggle_engine_from_tray(self):
        cur = config.get("engine", "local")
        new_eng = "local" if cur == "groq" else "groq"
        self.set_engine(new_eng)

    # --- MÉTODOS DE MICROFONE E ATALHO ---
    def get_mics(self):
        p = pyaudio.PyAudio()
        mics = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    raw_name = info.get("name", "?")
                    try:
                        name = raw_name.encode('cp1252').decode('utf-8')
                    except:
                        name = raw_name
                    if "Mapeador" not in name and "Steam" not in name:
                        mics.append((i, f"{i}: {name}"))
            except: pass
        p.terminate()
        return mics

    def change_mic(self):
        new_idx = self.mic_combo.currentData()
        if new_idx is not None:
            config["mic_index"] = new_idx
            save_config()
            if hasattr(self, 'mic_tester') and self.stack.currentIndex() == 2:
                self.mic_tester.start_test(new_idx)

    def capture_shortcut(self):
        dlg = ShortcutDialog(self)
        if dlg.exec():
            config["shortcut_name"] = dlg.key_name
            save_config()
            self.lbl_current_sc.setText(f"Atalho Atual: {config['shortcut_name']}")
            if hasattr(self, 'lbl_step_key'):
                self.lbl_step_key.setText(f"⌨️  {config['shortcut_name'].upper()}")
            if hasattr(self, 'pill_shortcut'):
                self.pill_shortcut.setText(f"⌨️ Atalho: {config['shortcut_name']}")
            self.register_native_hotkey()

    def register_native_hotkey(self):
        global hotkey_listener
        if hotkey_listener is not None:
            try:
                hotkey_listener.stop()
            except:
                pass
            hotkey_listener = None
            
        shortcut = config.get("shortcut_name", "ctrl+space")
        parts = shortcut.split('+')
        pynput_parts = []
        for p in parts:
            p = p.lower().strip()
            if p == 'ctrl': pynput_parts.append('<ctrl>')
            elif p == 'alt': pynput_parts.append('<alt>')
            elif p == 'shift': pynput_parts.append('<shift>')
            elif p == 'win': pynput_parts.append('<cmd>')
            elif p == 'return': pynput_parts.append('<enter>')
            else:
                if len(p) > 1:
                    pynput_parts.append(f'<{p}>')
                else:
                    pynput_parts.append(p)
                
        pynput_shortcut = '+'.join(pynput_parts)
            
        try:
            hotkey_listener = pynput_keyboard.GlobalHotKeys({
                pynput_shortcut: lambda: signals.toggle_recording_signal.emit()
            })
            hotkey_listener.start()
        except Exception as e:
            print("Erro ao registrar hotkey (pynput):", e)

    def toggle_recording(self):
        global is_recording, is_transcribing, overlay_instance, update_required
        if update_required:
            play_beep(400, 200)
            play_beep(300, 200)
            print("[AUTO-UPDATE] Uso bloqueado: atualização obrigatória pendente.", flush=True)
            threading.Thread(target=lambda: check_for_updates(auto_force=True), daemon=True).start()
            return
            
        if not is_recording:
            is_recording = True
            is_transcribing = False
            play_beep(1500, 150)
            overlay_instance.show()
            if hasattr(self, 'btn_mic_test_toggle'):
                self.btn_mic_test_toggle.setText("⏹️ Parar Gravação")
                self.btn_mic_test_toggle.setStyleSheet("background-color: #ef4444; color: white; border-radius: 5px; padding: 6px 14px; font-weight: bold;")
            
            # Enquanto a pessoa fala, inicia o pré-carregamento concorrente da IA em background
            engine = config.get("engine", "local")
            groq_key = config.get("groq_api_key", "").strip()
            if engine == "local" or not groq_key:
                ensure_model_loaded(async_mode=True)
                
            threading.Thread(target=recording_thread_func, daemon=True).start()
        else:
            is_recording = False
            is_transcribing = True
            play_beep(1000, 150)
            if hasattr(self, 'btn_mic_test_toggle'):
                self.btn_mic_test_toggle.setText("🎤 Gravar Teste")
                self.btn_mic_test_toggle.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 5px; padding: 6px 14px; font-weight: bold;")

    def load_history(self):
        for i in reversed(range(self.hist_layout.count())): 
            self.hist_layout.itemAt(i).widget().setParent(None)
            
        history_data = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except: pass
        if not history_data and os.path.exists(LOCAL_HISTORY):
            try:
                with open(LOCAL_HISTORY, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except: pass
            
        history_data = history_data[:50]
        for idx, item in enumerate(history_data):
            card = QFrame()
            card.setStyleSheet("QFrame { background-color: #1a1a2e; border-radius: 8px; margin-bottom: 10px; padding: 5px; }")
            cl = QVBoxLayout(card)
            
            top = QHBoxLayout()
            engine_tag = item.get("engine", "")
            lbl_time = QLabel(f"{item.get('time', '')} {engine_tag}")
            lbl_time.setStyleSheet("color: #9ca3af; font-size: 12px; background: transparent;")
            top.addWidget(lbl_time)
            
            btn_copy = QPushButton("📋 Copiar")
            btn_copy.setStyleSheet("background-color: #7c3aed; color: white; border-radius: 4px; padding: 4px 8px; font-size: 12px;")
            btn_copy.clicked.connect(lambda checked, t=item.get("text",""): QApplication.clipboard().setText(t))
            top.addWidget(btn_copy)
            
            btn_del = QPushButton("Excluir")
            btn_del.setStyleSheet("background-color: transparent; color: #ef4444; text-decoration: underline; font-size: 12px;")
            btn_del.clicked.connect(lambda checked, i=idx: self.delete_history_item(i))
            top.addWidget(btn_del)
            cl.addLayout(top)
            
            txt = QLabel(item.get("text", ""))
            txt.setWordWrap(True)
            txt.setStyleSheet("font-size: 14px; background: transparent; padding-top: 4px;")
            cl.addWidget(txt)
            
            self.hist_layout.addWidget(card)

    def delete_history_item(self, index):
        history_data = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except: pass
        elif os.path.exists(LOCAL_HISTORY):
            try:
                with open(LOCAL_HISTORY, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except: pass
            
        if 0 <= index < len(history_data):
            history_data.pop(index)
            history_data = history_data[:50]
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, ensure_ascii=False, indent=4)
            except: pass
            try:
                with open(LOCAL_HISTORY, "w", encoding="utf-8") as f:
                    json.dump(history_data, f, ensure_ascii=False, indent=4)
            except: pass
            self.load_history()

    def clear_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except: pass
        try:
            with open(LOCAL_HISTORY, "w", encoding="utf-8") as f:
                json.dump([], f)
        except: pass
        self.load_history()

# =============================================
# INICIALIZAÇÃO DO MODELO LOCAL
# =============================================
def load_ai_model():
    """Helper para carregar o modelo de IA sob demanda."""
    return ensure_model_loaded(async_mode=False)

# =============================================
# MAIN
# =============================================
def main():
    global app_instance, overlay_instance, main_window
    
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("lip.digitadoria.voicetyper.1.0")
    except Exception:
        pass

    app_instance = QApplication(sys.argv)
    app_instance.setQuitOnLastWindowClosed(False)
    
    # Checa atualizações obrigatoriamente na inicialização (segundo plano imediato)
    threading.Thread(target=lambda: check_for_updates(auto_force=True), daemon=True).start()
    
    # Ícone do microfone
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setBrush(QColor("#7c3aed"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(18, 4, 28, 36)
    p.drawRect(28, 40, 8, 14)
    p.drawRect(20, 54, 24, 4)
    p.end()
    
    app_icon = QIcon(pix)
    if os.path.exists("icon.ico"):
        app_icon = QIcon("icon.ico")
    else:
        try: pix.save("icon.ico")
        except: pass
        
    app_instance.setWindowIcon(app_icon)

    main_window = MainWindow()
    main_window.setWindowIcon(app_icon)
    
    overlay_instance = OverlayWindow()
    signals.hide_overlay.connect(overlay_instance.hide)
    
    # SYSTEM TRAY
    tray = QSystemTrayIcon()
    tray.setIcon(app_icon)
    menu = QMenu()
    
    action_engine_info = QAction("")
    action_engine_info.setEnabled(False)
    action_switch = QAction("")
    action_switch.triggered.connect(main_window.toggle_engine_from_tray)
    
    def update_tray_menu():
        cur_eng = config.get("engine", "local")
        if cur_eng == "groq":
            action_engine_info.setText("● Modo: ⚡ Groq Cloud")
            action_switch.setText("🔄 Alternar para: 🖥️ IA Local")
        else:
            action_engine_info.setText("● Modo: 🖥️ IA Local")
            action_switch.setText("🔄 Alternar para: ⚡ Groq Cloud")
            
    main_window.tray_menu_update_callback = update_tray_menu
    update_tray_menu()
    
    action_show = QAction("⚙️ Abrir Painel")
    action_show.triggered.connect(main_window.show)
    action_quit = QAction("❌ Sair")
    action_quit.triggered.connect(app_instance.quit)
    
    menu.addAction(action_engine_info)
    menu.addAction(action_switch)
    menu.addSeparator()
    menu.addAction(action_show)
    menu.addAction(action_quit)
    
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: main_window.show() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray.show()
    
    main_window.show()
    sys.exit(app_instance.exec())

if __name__ == "__main__":
    main()
