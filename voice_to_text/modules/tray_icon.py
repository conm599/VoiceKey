from PIL import Image
import pystray
from pystray import MenuItem as item
import threading
import os
import sys


class TrayIcon:
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.current_status = 'idle'
        self._running = False
        self._lock = threading.Lock()
        # 使用相对路径，基于当前可执行文件的目录
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境 - 向上两级到项目根目录
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._icon_path = os.path.join(base_dir, "FunAudioLLM.png")
        self._base_image = None
        self._load_base_image()

    def _load_base_image(self):
        try:
            if os.path.exists(self._icon_path):
                self._base_image = Image.open(self._icon_path)
                if self._base_image.mode != 'RGBA':
                    self._base_image = self._base_image.convert('RGBA')
                self._base_image = self._base_image.resize((64, 64), Image.Resampling.LANCZOS)
        except Exception:
            self._base_image = None

    def get_icon_for_status(self, status):
        if self._base_image:
            return self._base_image.copy()
        else:
            from PIL import ImageDraw
            image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            colors = {
                'idle': '#808080',
                'recording': '#FF0000',
                'processing': '#FFD700'
            }
            color = colors.get(status, colors['idle'])
            dc.ellipse([(8, 8), (56, 56)], fill=color)
            return image

    def create_icon(self):
        icon_image = self.get_icon_for_status(self.current_status)
        
        menu = (
            item('显示设置', self._on_show_settings),
            item('退出', self._on_exit)
        )
        
        self.icon = pystray.Icon(
            'voice_to_text',
            icon_image,
            '语音转文字',
            menu
        )

    def _on_show_settings(self, icon, item):
        if hasattr(self.app, 'show_settings'):
            self.app.root.after(0, self.app.show_settings)

    def _on_exit(self, icon, item):
        self.hide()
        if hasattr(self.app, 'quit'):
            self.app.root.after(0, self.app.quit)

    def show(self):
        if self.icon is None:
            self.create_icon()
        
        if not self._running:
            self._running = True
            def run_tray():
                try:
                    self.icon.run()
                except Exception:
                    pass
            self._tray_thread = threading.Thread(target=run_tray, daemon=True)
            self._tray_thread.start()

    def hide(self):
        with self._lock:
            if self.icon and self._running:
                self._running = False
                try:
                    self.icon.stop()
                except Exception:
                    pass

    def update_icon(self, status: str):
        self.current_status = status
        if self.icon:
            try:
                icon_image = self.get_icon_for_status(status)
                self.icon.icon = icon_image
                
                status_text = {
                    'idle': '空闲',
                    'recording': '录音中',
                    'processing': '处理中'
                }
                self.icon.title = f'语音转文字 - {status_text.get(status, "空闲")}'
            except Exception:
                pass

    def show_notification(self, title: str, message: str):
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass
