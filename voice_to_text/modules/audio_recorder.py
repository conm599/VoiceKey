import sounddevice as sd
import numpy as np
from scipy.io import wavfile
from datetime import datetime
import threading
import time
import os
from typing import Callable, Optional


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_volume_change: Optional[Callable[[float], None]] = None
        self.on_silence_detected: Optional[Callable[[], None]] = None
        
        self._is_recording = False
        self._audio_data = []
        self._stream = None
        self._silence_start_time = None
        self._recording_start_time = None
        self._silence_threshold = 500
        self._silence_duration = 2.0
        self._max_duration = 60.0
        self._current_volume = 0.0
        self._volume_callback_thread = None
        self._stop_event = threading.Event()
        import tempfile
        self._temp_dir = tempfile.gettempdir()
        
        os.makedirs(self._temp_dir, exist_ok=True)
    
    def start_recording(self, silence_threshold: float = 500, silence_duration: float = 2.0, max_duration: float = 60.0):
        if self._is_recording:
            return
        
        self._silence_threshold = silence_threshold
        self._silence_duration = silence_duration
        self._max_duration = max_duration
        self._audio_data = []
        self._is_recording = True
        self._silence_start_time = None
        self._recording_start_time = time.time()
        self._stop_event.clear()
        
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback
        )
        self._stream.start()
        
        self._volume_callback_thread = threading.Thread(target=self._volume_monitor, daemon=True)
        self._volume_callback_thread.start()
    
    def _audio_callback(self, indata, frames, time_info, status):
        if not self._is_recording:
            return
        
        self._audio_data.append(indata.copy())
        
        rms = np.sqrt(np.mean(indata**2)) * 32767
        self._current_volume = min(rms / 32767.0, 1.0)
        
        current_time = time.time()
        
        if current_time - self._recording_start_time >= self._max_duration:
            self._trigger_silence_callback()
            return
        
        if rms < self._silence_threshold:
            if self._silence_start_time is None:
                self._silence_start_time = current_time
            elif current_time - self._silence_start_time >= self._silence_duration:
                self._trigger_silence_callback()
        else:
            self._silence_start_time = None
    
    def _trigger_silence_callback(self):
        if self.on_silence_detected:
            threading.Thread(target=self.on_silence_detected, daemon=True).start()
    
    def _volume_monitor(self):
        while self._is_recording and not self._stop_event.is_set():
            if self.on_volume_change:
                self.on_volume_change(self._current_volume)
            time.sleep(0.05)
    
    def stop_recording(self) -> str:
        if not self._is_recording:
            return ""
        
        self._is_recording = False
        self._stop_event.set()
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if self._volume_callback_thread:
            self._volume_callback_thread.join(timeout=1.0)
        
        if not self._audio_data:
            return ""
        
        audio_array = np.concatenate(self._audio_data, axis=0)
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        filepath = os.path.join(self._temp_dir, filename)
        
        wavfile.write(filepath, self.sample_rate, audio_int16)
        
        return filepath
    
    def cancel_recording(self):
        if not self._is_recording:
            return
        
        self._is_recording = False
        self._stop_event.set()
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if self._volume_callback_thread:
            self._volume_callback_thread.join(timeout=1.0)
        
        self._audio_data = []
    
    def is_recording(self) -> bool:
        return self._is_recording
    
    def get_current_volume(self) -> float:
        return self._current_volume
    
    @property
    def silence_threshold(self) -> float:
        return self._silence_threshold
    
    @silence_threshold.setter
    def silence_threshold(self, value: float):
        self._silence_threshold = value
    
    @property
    def silence_duration(self) -> float:
        return self._silence_duration
    
    @silence_duration.setter
    def silence_duration(self, value: float):
        self._silence_duration = value
    
    @property
    def max_duration(self) -> float:
        return self._max_duration
    
    @max_duration.setter
    def max_duration(self, value: float):
        self._max_duration = value
