import tkinter as tk
from collections import deque
from typing import Optional
from voice_to_text.modules.config import Config


class FloatingWindow:
    def __init__(self, app):
        self.app = app
        self.config = Config.get_instance()
        
        self.window = tk.Toplevel()
        self.window.title("")
        self.window.geometry("80x80")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.5)
        
        self.window.attributes('-toolwindow', True)
        self.window.wm_attributes('-transparentcolor', '#2b2b2b')
        
        self.window.resizable(False, False)
        
        self._is_visible = False
        self._current_status = "idle"
        self._volume_history = deque(maxlen=30)
        self._auto_hide_id = None
        
        self._setup_ui()
        self._setup_bindings()
        
        self.window.withdraw()
    
    def _setup_ui(self):
        self.canvas = tk.Canvas(
            self.window,
            width=80,
            height=80,
            bg='#2b2b2b',
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self._draw_circle()
    
    def _setup_bindings(self):
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Button-3>', self._on_right_click)
    
    def _on_click(self, event):
        if hasattr(self.app, 'toggle_recording'):
            self.app.toggle_recording()
    
    def _on_right_click(self, event):
        if hasattr(self.app, 'cancel_recording'):
            if hasattr(self.app, 'is_recording') and self.app.is_recording:
                self.app.cancel_recording()
            else:
                self.hide()
        else:
            self.hide()
    
    def _draw_circle(self):
        self.canvas.delete('all')
        
        cx, cy = 40, 40
        base_radius = 30
        
        if self._current_status == "recording":
            self.canvas.create_oval(
                cx - base_radius - 5, cy - base_radius - 5,
                cx + base_radius + 5, cy + base_radius + 5,
                fill='#2196F3',
                outline='#2196F3'
            )
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                fill='#ff0000',
                outline='#ff0000'
            )
            
            if self._volume_history:
                volume = self._volume_history[-1]
                pulse_radius = base_radius + int(volume * 10)
                self.canvas.create_oval(
                    cx - pulse_radius, cy - pulse_radius,
                    cx + pulse_radius, cy + pulse_radius,
                    fill='',
                    outline='#2196F3',
                    width=2
                )
        elif self._current_status == "recognizing":
            self.canvas.create_oval(
                cx - base_radius - 3, cy - base_radius - 3,
                cx + base_radius + 3, cy + base_radius + 3,
                fill='#FFA500',
                outline='#FFA500'
            )
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                fill='#ff0000',
                outline='#ff0000'
            )
        elif self._current_status == "completed":
            self.canvas.create_oval(
                cx - base_radius - 3, cy - base_radius - 3,
                cx + base_radius + 3, cy + base_radius + 3,
                fill='#4CAF50',
                outline='#4CAF50'
            )
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                fill='#ff0000',
                outline='#ff0000'
            )
        elif self._current_status == "error":
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                fill='#ff0000',
                outline='#ff0000'
            )
            self.canvas.create_line(
                cx - 15, cy - 15, cx + 15, cy + 15,
                fill='white', width=3
            )
            self.canvas.create_line(
                cx + 15, cy - 15, cx - 15, cy + 15,
                fill='white', width=3
            )
        else:
            self.canvas.create_oval(
                cx - base_radius, cy - base_radius,
                cx + base_radius, cy + base_radius,
                fill='#ff0000',
                outline='#ff0000'
            )
    
    def show(self, x: Optional[int] = None, y: Optional[int] = None):
        self._cancel_auto_hide()
        
        if x is None or y is None:
            config_x = self.config.get('floating_window_x')
            config_y = self.config.get('floating_window_y')
            
            if config_x is not None and config_y is not None:
                x = config_x
                y = config_y
            else:
                screen_width = self.window.winfo_screenwidth()
                screen_height = self.window.winfo_screenheight()
                window_width = 80
                window_height = 80
                x = screen_width - window_width - 20
                y = 100
        
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self._is_visible = True
    
    def hide(self):
        self._cancel_auto_hide()
        self.window.withdraw()
        self._is_visible = False
    
    def _cancel_auto_hide(self):
        if self._auto_hide_id:
            self.window.after_cancel(self._auto_hide_id)
            self._auto_hide_id = None
    
    def _schedule_auto_hide(self, delay_ms=1000):
        self._cancel_auto_hide()
        self._auto_hide_id = self.window.after(delay_ms, self.hide)
    
    def update_status(self, status: str):
        self._current_status = status
        self._draw_circle()
        
        if status == "completed":
            self._schedule_auto_hide(1000)
        elif status == "error":
            self._schedule_auto_hide(2000)
    
    def update_duration(self, seconds: int):
        pass
    
    def update_volume(self, volume: float):
        self._volume_history.append(volume)
        if self._current_status == "recording":
            self._draw_circle()
    
    def show_result(self, text: str):
        pass
    
    def show_error(self, error: str):
        self._current_status = "error"
        self._draw_circle()
        self._schedule_auto_hide(2000)
    
    def set_position(self, x: int, y: int):
        self.window.geometry(f"+{x}+{y}")
        self.config.set('floating_window_x', x)
        self.config.set('floating_window_y', y)
    
    def is_visible(self) -> bool:
        return self._is_visible
    
    def reset(self):
        self._volume_history.clear()
        self._current_status = "idle"
        self._cancel_auto_hide()
        self._draw_circle()
