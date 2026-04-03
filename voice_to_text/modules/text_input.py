import pyautogui
import pyperclip
import time
from pynput.keyboard import Controller


class TextInput:
    def __init__(self, mode="paste"):
        self.mode = mode
        self.keyboard = Controller()
    
    def set_mode(self, mode: str):
        self.mode = mode
    
    def input_text_paste(self, text: str) -> bool:
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'v')
            return True
        except Exception:
            return False
    
    def input_text_direct(self, text: str) -> bool:
        try:
            self.keyboard.type(text)
            return True
        except Exception:
            return False
    
    def input_text(self, text: str) -> bool:
        if self.mode == "direct":
            return self.input_text_direct(text)
        else:
            return self.input_text_paste(text)
    
    def copy_to_clipboard(self, text: str):
        pyperclip.copy(text)
    
    def input_with_fallback(self, text: str) -> tuple:
        if self.mode == "direct":
            success = self.input_text_direct(text)
            if success:
                return True, "直接输入成功"
            else:
                self.copy_to_clipboard(text)
                return False, "直接输入失败，文字已复制到剪贴板"
        else:
            try:
                success = self.input_text_paste(text)
                if success:
                    return True, "粘贴输入成功"
                else:
                    self.copy_to_clipboard(text)
                    return False, "粘贴失败，文字已复制到剪贴板"
            except Exception as e:
                self.copy_to_clipboard(text)
                return False, f"输入失败，文字已复制到剪贴板: {str(e)}"
