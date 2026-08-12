import io
import math
import threading
import time
import os
import ctypes
import tkinter as tk
import mss
import keyboard
import win32clipboard
import win32con
from PIL import Image, ImageDraw, ImageFont, ImageTk
from pystray import Icon, Menu, MenuItem

Image.MAX_IMAGE_PIXELS = 200_000_000

# ========== НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ (скриншот) ==========
HOTKEY = 'ctrl+alt+s'
CANCEL_KEYS = ['<Escape>', '<Button-3>']
FRAME_COLOR = 'red'
FRAME_WIDTH = 2
MIN_CROP_SIZE = 5
TOAST_DURATION = 1500
TOAST_SIZE = "200x30"
TOAST_POSITION_OFFSET = (210, 70)
# ======================================================

# ========== НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ (текст в картинку) ==========
TEXT_HOTKEY = 'ctrl+alt+t'
TEXT_IMG_MAX_WIDTH = 1000
TEXT_PADDING = 20
TEXT_BG = (255, 255, 255)
TEXT_FG = (30, 30, 30)
TEXT_SCALE = 2
TEXT_FONT_SIZE = 28
TEXT_FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
TEXT_LINE_SPACING = 6
TEXT_TIMEOUT_AFTER_COPY = 0.15
TEXT_SCALE_REF = 500
TEXT_SCALE_MAX = 5
MAX_IMG_HEIGHT = 12000
# ==============================================================

def copy_to_clipboard(img):
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            return True
        except:
            time.sleep(0.05)
    return False

def show_toast(master, msg):
    toast = tk.Toplevel(master)
    toast.overrideredirect(True)
    toast.attributes('-topmost', True)
    sw, sh = toast.winfo_screenwidth(), toast.winfo_screenheight()
    x = sw - TOAST_POSITION_OFFSET[0]
    y = sh - TOAST_POSITION_OFFSET[1]
    toast.geometry(f'{TOAST_SIZE}+{x}+{y}')
    tk.Label(toast, text=msg, bg='#2b2b2b', fg='white').pack(fill='both', expand=True)
    toast.after(TOAST_DURATION, toast.destroy)

def wrap_text(text, font, max_width, draw):
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        words = paragraph.split()
        current_line = []
        for word in words:
            if draw.textlength(word, font=font) > max_width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                chunk = ''
                for ch in word:
                    test_chunk = chunk + ch
                    if chunk and draw.textlength(test_chunk, font=font) > max_width:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk = test_chunk
                current_line = [chunk]
                continue
            test_line = ' '.join(current_line + [word])
            if draw.textlength(test_line, font=font) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
    return lines

def render_text_to_image(text):
    font_base = ImageFont.truetype(TEXT_FONT_PATH, TEXT_FONT_SIZE)
    draw_base = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    wrapped = wrap_text(text, font_base, TEXT_IMG_MAX_WIDTH, draw_base)

    asc, desc = font_base.getmetrics()
    line_pitch = asc + desc + TEXT_LINE_SPACING
    base_height = asc + (len(wrapped) - 1) * line_pitch + desc

    s = min(TEXT_SCALE_MAX, max(TEXT_SCALE, math.ceil(base_height / TEXT_SCALE_REF)))
    s = max(TEXT_SCALE, min(s, MAX_IMG_HEIGHT // max(base_height, 1)))

    padding = TEXT_PADDING * s
    font = ImageFont.truetype(TEXT_FONT_PATH, TEXT_FONT_SIZE * s)
    asc, desc = font.getmetrics()
    line_pitch = asc + desc + TEXT_LINE_SPACING * s
    width = (TEXT_IMG_MAX_WIDTH + TEXT_PADDING * 2) * s
    height = padding * 2 + asc + (len(wrapped) - 1) * line_pitch + desc

    img = Image.new("RGB", (width, height), TEXT_BG)
    draw = ImageDraw.Draw(img)
    body = "\n".join(wrapped)
    draw.multiline_text(
        (padding, padding),
        body,
        fill=TEXT_FG,
        font=font,
        spacing=TEXT_LINE_SPACING * s
    )

    bbox = draw.textbbox((padding, padding), body, font=font, spacing=TEXT_LINE_SPACING * s)
    img = img.crop((
        max(0, bbox[0] - padding),
        max(0, bbox[1] - padding),
        min(width, bbox[2] + padding),
        min(height, bbox[3] + padding)
    ))
    img.info['dpi'] = (72 * s, 72 * s)
    return img

class CaptureTool:
    def __init__(self, master):
        self.master = master
        self.root = tk.Toplevel(master)
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self._init_capture()

    def _init_capture(self):
        with mss.mss() as sct:
            self.mon = sct.monitors[0]
            sct_img = sct.grab(self.mon)
            self.screen = Image.frombytes('RGB', (self.mon['width'], self.mon['height']),
                                        sct_img.bgra, 'raw', 'BGRX')

        self.root.deiconify()
        self.root.focus_force()
        self.root.grab_set()
        self.root.geometry(f"{self.mon['width']}x{self.mon['height']}+0+0")

        self.canvas = tk.Canvas(self.root, cursor='cross', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.tk_img = ImageTk.PhotoImage(self.screen)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)

        self.rect = None
        self.start_x = self.start_y = 0

        self.root.bind('<ButtonPress-1>', self.on_press)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<ButtonRelease-1>', self.on_release)

        for key in CANCEL_KEYS:
            self.root.bind(key, lambda e: self.root.destroy())

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y,
            outline=FRAME_COLOR,
            width=FRAME_WIDTH
        )

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        x1, y1 = min(self.start_x, e.x), min(self.start_y, e.y)
        x2, y2 = max(self.start_x, e.x), max(self.start_y, e.y)
        self.root.destroy()

        if (x2 - x1) > MIN_CROP_SIZE and (y2 - y1) > MIN_CROP_SIZE:
            crop = self.screen.crop((x1, y1, x2, y2))
            if copy_to_clipboard(crop):
                show_toast(self.master, "Скопировано!")

def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root = tk.Tk()
    root.withdraw()

    def run_capture():
        root.after(0, lambda: CaptureTool(root))

    def capture_text():
        try:
            keyboard.press_and_release('ctrl+c')
            time.sleep(TEXT_TIMEOUT_AFTER_COPY)
            win32clipboard.OpenClipboard()
            try:
                text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except:
                text = None
            win32clipboard.CloseClipboard()
            if text and text.strip():
                img = render_text_to_image(text.strip())
                root.after(0, lambda img=img: [copy_to_clipboard(img), show_toast(root, "Текст скопирован как картинка!")])
        except Exception as e:
            pass

    def on_exit(icon, item):
        icon.stop()
        root.quit()
        os._exit(0)

    icon_img = Image.new('RGB', (64, 64), (40, 40, 40))
    d = ImageDraw.Draw(icon_img)
    d.rectangle([10, 10, 54, 54], outline='white', width=4)

    icon = Icon('FScr', icon_img, 'FScr', menu=Menu(
        MenuItem('Скриншот', run_capture, default=True),
        MenuItem('Текст в картинку', capture_text),
        MenuItem('Выход', on_exit)
    ))

    keyboard.add_hotkey(HOTKEY, run_capture)
    keyboard.add_hotkey(TEXT_HOTKEY, capture_text)

    icon.run_detached()
    root.mainloop()

if __name__ == '__main__':
    main()
