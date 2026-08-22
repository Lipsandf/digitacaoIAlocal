import os
import site
import json
import threading
import io
import time
import math
import wave
import ctypes
from ctypes import wintypes
import winsound
from pynput import keyboard as pynput_keyboard
import pyaudio
import sys

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                            QComboBox, QProgressBar, QTextEdit, QScrollArea, QFrame,
                            QSystemTrayIcon, QMenu, QDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QAction, QIcon, QPixmap, QFont, QKeySequence

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
# ESTADOS E CONFIGURAÇÕES
# =============================================
CONFIG_FILE = "config.json"
HISTORY_FILE = "transcriptions_history.json"
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
    "overlay_y": -1
}

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config.update(json.load(f))
    except: pass

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

model = None
is_recording = False
is_transcribing = False
audio_queue = []
last_context = ""
current_rms = 0.0
hotkey_listener = None

class WorkerSignals(QObject):
    history_updated = pyqtSignal()
    hide_overlay = pyqtSignal()

signals = WorkerSignals()

# =============================================
# GRAVAÇÃO E TRANSCRIÇÃO
# =============================================
def recording_thread_func():
    global is_recording, audio_queue, current_rms
    
    CHUNK = 1024
    p = pyaudio.PyAudio()
    
    try:
        device_info = p.get_device_info_by_index(config["mic_index"])
        SAMPLE_RATE = int(device_info.get("defaultSampleRate", 44100))
    except:
        SAMPLE_RATE = 44100

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, 
                    input=True, input_device_index=config["mic_index"], frames_per_buffer=CHUNK)
    
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

def transcribe_and_type(buffer, sample_rate):
    global last_context, model, is_transcribing, overlay_instance
    if model is None: 
        is_transcribing = False
        signals.hide_overlay.emit()
        return
    
    buf = io.BytesIO()
    p = pyaudio.PyAudio()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(buffer))
    buf.seek(0)
    p.terminate()
    
    try:
        winsound.Beep(800, 100)
        segments, _ = model.transcribe(
            buf, beam_size=5, language="pt",
            condition_on_previous_text=True,
            initial_prompt=last_context if last_context else None,
            vad_filter=True
        )
        text = "".join([s.text for s in segments]).strip()
        
        if text:
            from pynput.keyboard import Controller
            k = Controller()
            k.type(text + " ")
            last_context = (last_context + " " + text).strip()[-120:]
            
            from datetime import datetime
            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            history_data = []
            if os.path.exists(HISTORY_FILE):
                try:
                    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except: pass
            history_data.insert(0, {"time": now, "text": text})
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history_data[:50], f, ensure_ascii=False, indent=4)
                
            signals.history_updated.emit()
    except Exception as e:
        print(f"Erro na transcrição: {e}")
    finally:
        is_transcribing = False
        signals.hide_overlay.emit()

# =============================================
# OVERLAY: ONDAS COM FAKE GLOW
# =============================================
class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        self.width_ = 450
        self.height_ = 150
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
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)
        
        # Cores (Vermelho ao Roxo)
        self.colors = [
            QColor(255, 0, 0, 200),
            QColor(255, 127, 0, 200),
            QColor(255, 255, 0, 200),
            QColor(0, 255, 0, 200),
            QColor(0, 255, 255, 200),
            QColor(0, 0, 255, 200),
            QColor(139, 0, 255, 200)
        ]

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
        if not self._is_dragging and self.isVisible():
            self.frame_count += 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo quase invisível para capturar o clique do mouse em toda a extensão
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 15, 25, 40))
        painter.drawRoundedRect(self.rect(), 12, 12)
        
        if is_transcribing:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(26, 26, 46, 200))
            painter.drawRoundedRect(self.rect(), 10, 10)
            
            painter.setPen(QColor("#7c3aed"))
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            dots = "." * ((self.frame_count // 10) % 4)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"Transcrevendo{dots}")
            
            angle = (self.frame_count * 10) % 360
            painter.setPen(QPen(QColor("#a78bfa"), 4))
            painter.drawArc(self.width_ // 2 - 120, self.height_ // 2 - 15, 30, 30, -angle * 16, 120 * 16)
            return
            
        vol = current_rms if is_recording else 0
        amp = max(2.0, min(60.0, vol / 40.0))
        if not is_recording: amp = 1.0

        cy = self.height_ / 2
        points_count = 100
        step = self.width_ / points_count

        for c_idx, color in enumerate(self.colors):
            path = QPainterPath()
            path.moveTo(0, cy)
            
            for i in range(1, points_count + 1):
                x = i * step
                phase = self.frame_count * 0.1 + (i * 0.08) + c_idx
                y_offset = math.sin(phase) * amp * math.sin(i * 3.1415 / points_count)
                y_offset += math.sin(phase * 2.5) * (amp * 0.3)
                y = cy + y_offset
                path.lineTo(x, y)
            
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 50), 6))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 150), 3))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
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
        self.setWindowTitle("Digitador IA - Dashboard")
        self.resize(900, 600)
        self.setStyleSheet("QMainWindow { background-color: #0f0f1b; } QWidget { font-family: 'Segoe UI'; color: #e5e7eb; background-color: #0f0f1b; } QFrame { background-color: #1a1a2e; }")
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("QFrame { background-color: #161622; } QPushButton { background-color: transparent; border: none; padding: 12px; font-size: 14px; text-align: left; } QPushButton:hover { background-color: #7c3aed; border-radius: 5px; }")
        side_layout = QVBoxLayout(sidebar)
        
        lbl_logo = QLabel("🎙️ Digitador IA")
        lbl_logo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_logo.setStyleSheet("color: #a78bfa; padding: 15px; background-color: transparent;")
        lbl_logo.setWordWrap(False)
        side_layout.addWidget(lbl_logo)
        
        btn_tut = QPushButton("Tutorial")
        btn_mic = QPushButton("Microfone")
        btn_short = QPushButton("Atalho")
        btn_hist = QPushButton("Histórico")
        btn_hide = QPushButton("⬇️ Ocultar (Bandeja)")
        
        side_layout.addWidget(btn_tut)
        side_layout.addWidget(btn_mic)
        side_layout.addWidget(btn_short)
        side_layout.addWidget(btn_hist)
        side_layout.addStretch()
        
        lbl_credits = QLabel('Desenvolvido por Felipe<br><a href="https://lip.tec.br" style="color: #a78bfa; text-decoration: none;">https://lip.tec.br</a><br><a href="mailto:felipe@lip.tec.br" style="color: #a78bfa; text-decoration: none;">felipe@lip.tec.br</a>')
        lbl_credits.setFont(QFont("Segoe UI", 10))
        lbl_credits.setStyleSheet("color: #6b7280; padding: 10px; background-color: transparent;")
        lbl_credits.setOpenExternalLinks(True)
        side_layout.addWidget(lbl_credits)
        
        side_layout.addWidget(btn_hide)
        
        main_layout.addWidget(sidebar)
        
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        page_tut = QWidget()
        l_tut = QVBoxLayout(page_tut)
        title_tut = QLabel("Como usar o Digitador por Voz")
        title_tut.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        l_tut.addWidget(title_tut, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.banner_cuda = QLabel("⚠️ ATENÇÃO: Seu driver de vídeo NVIDIA está antigo! O programa caiu para o modo CPU. Atualize o driver da placa para ter velocidade máxima de transcrição.")
        self.banner_cuda.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.banner_cuda.setWordWrap(True)
        self.banner_cuda.setStyleSheet("background-color: #7c2d12; color: #fde047; padding: 12px; border-radius: 6px; border: 1px solid #eab308;")
        self.banner_cuda.setVisible(False)
        l_tut.addWidget(self.banner_cuda)
        
        info_tut = QLabel(f"1. Clique na caixa de texto abaixo para focar.\n2. Pressione {config['shortcut_name']} para iniciar.\n3. Fale e veja a onda mágica reagir.\n4. Pressione {config['shortcut_name']} novamente para transcrever.")
        info_tut.setFont(QFont("Segoe UI", 14))
        l_tut.addWidget(info_tut)
        
        self.test_box = QTextEdit()
        self.test_box.setPlaceholderText("Clique aqui e teste seu atalho e a digitação...")
        self.test_box.setStyleSheet("background-color: #1a1a2e; border: 1px solid #7c3aed; border-radius: 5px; font-size: 16px; padding: 10px;")
        l_tut.addWidget(self.test_box)
        self.stack.addWidget(page_tut)
        
        page_mic = QWidget()
        l_mic = QVBoxLayout(page_mic)
        title_mic = QLabel("Configuração de Microfone")
        title_mic.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        l_mic.addWidget(title_mic, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setStyleSheet("background-color: #1a1a2e; padding: 8px; font-size: 14px; border: 1px solid #7c3aed;")
        
        mics = self.get_mics()
        for idx, name in mics:
            self.mic_combo.addItem(name, idx)
            if idx == config["mic_index"]:
                self.mic_combo.setCurrentText(name)
                
        self.mic_combo.currentIndexChanged.connect(self.change_mic)
        l_mic.addWidget(self.mic_combo)
        
        l_mic.addWidget(QLabel("Teste de Áudio (Fale algo):"))
        self.mic_prog = QProgressBar()
        self.mic_prog.setTextVisible(False)
        self.mic_prog.setStyleSheet("QProgressBar { background-color: #1a1a2e; border-radius: 5px; } QProgressBar::chunk { background-color: #00ff00; }")
        l_mic.addWidget(self.mic_prog)
        l_mic.addStretch()
        self.stack.addWidget(page_mic)
        
        page_short = QWidget()
        l_short = QVBoxLayout(page_short)
        title_short = QLabel("Configuração de Atalho")
        title_short.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        l_short.addWidget(title_short, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.lbl_current_sc = QLabel(f"Atalho Atual: {config['shortcut_name']}")
        self.lbl_current_sc.setFont(QFont("Segoe UI", 16))
        l_short.addWidget(self.lbl_current_sc)
        
        btn_cap = QPushButton("Capturar Novo Atalho")
        btn_cap.setFixedSize(200, 45)
        btn_cap.setStyleSheet("background-color: #7c3aed; border-radius: 5px; font-weight: bold; font-size: 14px;")
        btn_cap.clicked.connect(self.capture_shortcut)
        l_short.addWidget(btn_cap)
        l_short.addStretch()
        self.stack.addWidget(page_short)
        
        page_hist = QWidget()
        l_hist = QVBoxLayout(page_hist)
        
        top_hist = QHBoxLayout()
        title_hist = QLabel("Histórico de Transcrições")
        title_hist.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        top_hist.addWidget(title_hist)
        
        btn_clear = QPushButton("🗑️ Apagar Tudo")
        btn_clear.setStyleSheet("background-color: #ef4444; border-radius: 5px; padding: 8px; font-weight: bold;")
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
        
        btn_tut.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_mic.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_short.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_hist.clicked.connect(lambda: [self.stack.setCurrentIndex(3), self.load_history()])
        btn_hide.clicked.connect(self.hide)

        self.mic_timer = QTimer(self)
        self.mic_timer.timeout.connect(self.update_mic_test)
        self.mic_timer.start(100)

        signals.history_updated.connect(self.load_history)
        
    def showEvent(self, event):
        super().showEvent(event)
        if cuda_driver_warning:
            self.banner_cuda.setVisible(True)
        if not hasattr(self, '_hotkey_registered'):
            self.register_native_hotkey()
            self._hotkey_registered = True

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
            self._is_changing_mic = True
            if hasattr(self, 'mic_timer'):
                self.mic_timer.stop()
            config["mic_index"] = new_idx
            save_config()
            QTimer.singleShot(300, self._resume_mic_test)

    def _resume_mic_test(self):
        self._is_changing_mic = False
        if hasattr(self, 'mic_timer'):
            self.mic_timer.start(150)

    def capture_shortcut(self):
        dlg = ShortcutDialog(self)
        if dlg.exec():
            config["shortcut_name"] = dlg.key_name
            save_config()
            self.lbl_current_sc.setText(f"Atalho Atual: {config['shortcut_name']}")
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
                pynput_shortcut: self.toggle_recording
            })
            hotkey_listener.start()
        except Exception as e:
            print("Erro ao registrar hotkey (pynput):", e)

    def toggle_recording(self):
        global is_recording, is_transcribing, overlay_instance
        if not is_recording:
            is_recording = True
            is_transcribing = False
            winsound.Beep(1500, 150)
            overlay_instance.show()
            threading.Thread(target=recording_thread_func, daemon=True).start()
        else:
            is_recording = False
            is_transcribing = True
            winsound.Beep(1000, 150)

    def load_history(self):
        for i in reversed(range(self.hist_layout.count())): 
            self.hist_layout.itemAt(i).widget().setParent(None)
            
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for idx, item in enumerate(data):
                        card = QFrame()
                        card.setStyleSheet("QFrame { background-color: #1a1a2e; border-radius: 8px; margin-bottom: 10px; }")
                        cl = QVBoxLayout(card)
                        
                        top = QHBoxLayout()
                        lbl_time = QLabel(item.get("time", ""))
                        lbl_time.setStyleSheet("color: #9ca3af; font-size: 12px;")
                        top.addWidget(lbl_time)
                        
                        btn_copy = QPushButton("Copiar")
                        btn_copy.setStyleSheet("background-color: #7c3aed; border-radius: 4px; padding: 5px;")
                        btn_copy.clicked.connect(lambda checked, t=item.get("text",""): QApplication.clipboard().setText(t))
                        top.addWidget(btn_copy)
                        
                        btn_del = QPushButton("Excluir")
                        btn_del.setStyleSheet("background-color: transparent; color: #ef4444; text-decoration: underline;")
                        btn_del.clicked.connect(lambda checked, i=idx: self.delete_history_item(i))
                        top.addWidget(btn_del)
                        cl.addLayout(top)
                        
                        txt = QLabel(item.get("text", ""))
                        txt.setWordWrap(True)
                        txt.setStyleSheet("font-size: 15px;")
                        cl.addWidget(txt)
                        
                        self.hist_layout.addWidget(card)
            except: pass

    def delete_history_item(self, index):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if 0 <= index < len(data):
                data.pop(index)
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                self.load_history()

    def clear_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            self.load_history()

    def update_mic_test(self):
        if getattr(self, '_is_changing_mic', False):
            return
        if not is_recording and self.stack.currentIndex() == 1:
            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=config["mic_index"], frames_per_buffer=1024)
                data = stream.read(1024, exception_on_overflow=False)
                import numpy as np
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples ** 2)))
                val = min(100, int((rms / 4000.0) * 100))
                self.mic_prog.setValue(val)
                stream.stop_stream()
                stream.close()
                p.terminate()
            except:
                self.mic_prog.setValue(0)

# =============================================
# INICIALIZAÇÃO E MODELO IA
# =============================================
cuda_driver_warning = False

def load_ai_model():
    global model, cuda_driver_warning
    # Tenta CUDA FP16
    try:
        model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
        winsound.Beep(1000, 100)
        winsound.Beep(1500, 100)
        print("Carregado na GPU NVIDIA via CUDA (float16)!")
        return
    except Exception as e:
        print("CUDA float16 nao suportado pela placa. Tentando CUDA int8/float32...", e)
        
        # Tenta CUDA INT8 (Perfeito para MX250 e Serie GTX 10xx)
        try:
            model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="int8")
            winsound.Beep(1000, 100)
            winsound.Beep(1500, 100)
            print("Carregado com SUCESSO na GPU NVIDIA via CUDA (Modo INT8)! Transcricao ULTRA RAPIDA ativada.")
            return
        except Exception as e_int8:
            print("CUDA int8 falhou. Tentando CUDA float32...", e_int8)
            
            # Tenta CUDA FLOAT32
            try:
                model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float32")
                winsound.Beep(1000, 100)
                winsound.Beep(1500, 100)
                print("Carregado com SUCESSO na GPU NVIDIA via CUDA (Modo FLOAT32)!")
                return
            except Exception as e_f32:
                print("Erro ao carregar GPU CUDA:", e_f32)
                err_msg = str(e_f32).lower()
                if "insufficient" in err_msg or "driver" in err_msg:
                    cuda_driver_warning = True

    # Check DirectML for AMD/Intel GPUs
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "DmlExecutionProvider" in providers:
            print("Detectado suporte DirectML (GPU AMD/Intel/DirectX 12 pronta)!")
    except Exception:
        pass

    # Fallback para CPU
    print("Caindo para o modo CPU...")
    import multiprocessing
    total_cores = multiprocessing.cpu_count()
    # Usa quase todos os nucleos para pico de velocidade, mas deixa 1 ou 2 livres para o Windows nao travar
    smart_threads = max(1, total_cores - 2) if total_cores > 4 else total_cores
    
    try:
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=smart_threads)
        winsound.Beep(800, 100)
        winsound.Beep(1200, 100)
    except Exception as e2:
        print("Erro critico ao carregar IA no modo int8, tentando float32...", e2)
        try:
            model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="float32", cpu_threads=smart_threads)
            winsound.Beep(800, 100)
            winsound.Beep(1200, 100)
        except Exception as e3:
            print("Falha total na CPU:", e3)

def main():
    global app_instance, overlay_instance, main_window
    app_instance = QApplication(sys.argv)
    app_instance.setQuitOnLastWindowClosed(False)
    
    threading.Thread(target=load_ai_model, daemon=True).start()
    
    main_window = MainWindow()
    print("Criando Overlay", flush=True)
    overlay_instance = OverlayWindow()
    signals.hide_overlay.connect(overlay_instance.hide)
    
    print("Criando Tray", flush=True)
    tray = QSystemTrayIcon()
    
    print("Criando Pixmap", flush=True)
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setBrush(QColor("#7c3aed"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(18, 4, 28, 36)
    p.drawRect(28, 40, 8, 14)
    p.drawRect(20, 54, 24, 4)
    p.end()
    
    print("Configurando tray", flush=True)
    tray.setIcon(QIcon(pix))
    menu = QMenu()
    action_show = QAction("Abrir Painel")
    action_show.triggered.connect(main_window.show)
    action_quit = QAction("Sair")
    action_quit.triggered.connect(app_instance.quit)
    
    menu.addAction(action_show)
    menu.addAction(action_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: main_window.show() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray.show()
    
    print("Mostrando MainWindow", flush=True)
    main_window.show()
    print("Executando loop", flush=True)
    sys.exit(app_instance.exec())

if __name__ == "__main__":
    main()
