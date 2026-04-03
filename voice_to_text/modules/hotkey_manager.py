from pynput import keyboard
import threading


class HotkeyManager:
    def __init__(self):
        self.on_hotkey_pressed = None
        self._current_hotkey = None
        self._listener = None
        self._running = False
        self._lock = threading.Lock()

    def parse_hotkey(self, hotkey_str: str) -> tuple:
        if not hotkey_str:
            return None, None
        
        parts = [p.strip().lower() for p in hotkey_str.split('+')]
        
        modifiers = set()
        key = None
        
        modifier_map = {
            'ctrl': keyboard.Key.ctrl,
            'ctrl_l': keyboard.Key.ctrl_l,
            'ctrl_r': keyboard.Key.ctrl_r,
            'alt': keyboard.Key.alt,
            'alt_l': keyboard.Key.alt_l,
            'alt_r': keyboard.Key.alt_r,
            'shift': keyboard.Key.shift,
            'shift_l': keyboard.Key.shift_l,
            'shift_r': keyboard.Key.shift_r,
            'cmd': keyboard.Key.cmd,
            'cmd_l': keyboard.Key.cmd_l,
            'cmd_r': keyboard.Key.cmd_r,
            'win': keyboard.Key.cmd,
        }
        
        function_keys = {
            'f1': keyboard.Key.f1, 'f2': keyboard.Key.f2, 'f3': keyboard.Key.f3,
            'f4': keyboard.Key.f4, 'f5': keyboard.Key.f5, 'f6': keyboard.Key.f6,
            'f7': keyboard.Key.f7, 'f8': keyboard.Key.f8, 'f9': keyboard.Key.f9,
            'f10': keyboard.Key.f10, 'f11': keyboard.Key.f11, 'f12': keyboard.Key.f12,
        }
        
        for part in parts:
            if part in modifier_map:
                modifiers.add(modifier_map[part])
            elif part in function_keys:
                key = function_keys[part]
            elif len(part) == 1 and part.isalpha():
                key = keyboard.KeyCode.from_char(part)
            elif len(part) == 1 and part.isdigit():
                key = keyboard.KeyCode.from_char(part)
            else:
                try:
                    key = keyboard.KeyCode.from_char(part)
                except Exception:
                    return None, None
        
        if key is None:
            return None, None
        
        return frozenset(modifiers), key

    def register_hotkey(self, hotkey: str, callback: callable) -> bool:
        if not hotkey or not callback:
            return False
        
        with self._lock:
            try:
                modifiers, key = self.parse_hotkey(hotkey)
                if modifiers is None or key is None:
                    return False
                
                self._current_hotkey = hotkey
                self.on_hotkey_pressed = callback
                return True
            except Exception:
                return False

    def unregister_hotkey(self):
        with self._lock:
            self._current_hotkey = None
            self.on_hotkey_pressed = None

    def update_hotkey(self, new_hotkey: str) -> bool:
        if not new_hotkey:
            return False
        
        callback = self.on_hotkey_pressed
        was_running = self._running
        
        if was_running:
            self.stop()
        
        success = self.register_hotkey(new_hotkey, callback)
        
        if success and was_running:
            self.start()
        
        return success

    def start(self):
        with self._lock:
            if self._running:
                return
            
            if not self._current_hotkey:
                return
            
            try:
                hotkey_str = self._current_hotkey.lower().replace(' ', '')
                hotkey_parts = hotkey_str.split('+')
                
                normalized_parts = []
                for part in hotkey_parts:
                    if part == 'win':
                        normalized_parts.append('<cmd>')
                    elif part.startswith('f') and len(part) <= 3:
                        normalized_parts.append(f'<{part}>')
                    elif len(part) == 1:
                        normalized_parts.append(part)
                    else:
                        normalized_parts.append(f'<{part}>')
                
                pynput_hotkey = '+'.join(normalized_parts)
                
                hotkeys = {
                    pynput_hotkey: self._on_hotkey_trigger
                }
                
                self._listener = keyboard.GlobalHotKeys(hotkeys)
                self._listener.start()
                self._running = True
            except Exception:
                self._running = False
                self._listener = None

    def stop(self):
        with self._lock:
            if not self._running:
                return
            
            try:
                if self._listener:
                    self._listener.stop()
                    self._listener = None
            except Exception:
                pass
            
            self._running = False

    def _on_hotkey_trigger(self):
        if self.on_hotkey_pressed:
            try:
                self.on_hotkey_pressed()
            except Exception:
                pass

    def is_running(self) -> bool:
        return self._running

    def get_current_hotkey(self) -> str:
        return self._current_hotkey
