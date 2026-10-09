# -*- coding: utf-8 -*-
"""
YTB Downloader - Modern, High-Performance Video & Audio Downloader
Matches custom dark aesthetic mockup with instant preview, high-DPI crisp rendering,
and multi-threaded accelerated downloads.
"""

import os
import sys
import threading
import time
import io
import json
import re
import queue
import subprocess
import urllib.request
import ssl
import math
import tkinter as tk
from tkinter import filedialog, messagebox

# ----------------- 1. Enable High DPI Awareness (Windows) -----------------
# Fixes pixelation/blurriness on 125%, 150%, 200% displays
if sys.platform == "win32":
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter

# ----------------- Directory & Tool Constants -----------------
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
YT_DLP_EXE = os.path.join(CUR_DIR, "yt-dlp.exe")
FFMPEG_EXE = os.path.join(CUR_DIR, "ffmpeg.exe")

if not os.path.exists(YT_DLP_EXE):
    YT_DLP_EXE = "yt-dlp"
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
if not os.path.exists(DEFAULT_DOWNLOAD_DIR):
    DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Desktop")

# SSL context for reliable image & API requests without Windows cert-store issues
SSL_CTX = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# ----------------- Visual Assets Generation (On-the-fly & Cached) -----------------
def generate_assets():
    """Generates crisp high-DPI icons if not present"""
    scale = 4
    
    # 1. App Logo (Badge with play triangle and download arrow)
    logo_path = os.path.join(CUR_DIR, "app_logo.png")
    if not os.path.exists(logo_path):
        s = 64 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = int(4 * scale)
        radius = int(14 * scale)
        draw.rounded_rectangle([pad, pad, s-pad, s-pad], radius=radius, fill=(239, 68, 68, 255))
        draw.rounded_rectangle([pad+int(2*scale), pad+int(2*scale), s-pad-int(2*scale), int(s*0.45)], radius=int(12*scale), fill=(248, 113, 113, 100))
        # Triangle
        tri = [(int(s * 0.30), int(s * 0.28)), (int(s * 0.62), int(s * 0.50)), (int(s * 0.30), int(s * 0.72))]
        draw.polygon(tri, fill=(255, 255, 255, 255))
        # Arrow
        cx = int(s * 0.72)
        top = int(s * 0.52)
        bot = int(s * 0.76)
        w = int(s * 0.08)
        hw = int(s * 0.16)
        neck = int(s * 0.66)
        draw.polygon([(cx-w, top), (cx+w, top), (cx+w, neck), (cx+hw, neck), (cx, bot), (cx-hw, neck), (cx-w, neck)], fill=(255, 255, 255, 255))
        img.resize((64, 64), Image.Resampling.LANCZOS).save(logo_path)

    # 2. Laptop Placeholder Graphic (Matching Mockup exactly)
    placeholder_path = os.path.join(CUR_DIR, "laptop_placeholder.png")
    if not os.path.exists(placeholder_path):
        width, height = 240, 170
        w, h = width * scale, height * scale
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        sx0, sy0 = int(w * 0.18), int(h * 0.12)
        sx1, sy1 = int(w * 0.82), int(h * 0.72)
        r = int(14 * scale)
        draw.rounded_rectangle([sx0, sy0, sx1, sy1], radius=r, fill=(38, 48, 64, 255), outline=(64, 80, 105, 255), width=int(2.5*scale))
        
        pad = int(8 * scale)
        dx0, dy0 = sx0 + pad, sy0 + pad
        dx1, dy1 = sx1 - pad, sy1 - int(6 * scale)
        draw.rounded_rectangle([dx0, dy0, dx1, dy1], radius=int(6*scale), fill=(18, 25, 36, 255))
        
        bx0, by0 = int(w * 0.10), sy1
        bx1, by1 = int(w * 0.90), int(h * 0.79)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(6*scale), fill=(48, 60, 78, 255), outline=(70, 88, 114, 255), width=int(2*scale))
        
        nw = int(w * 0.15)
        nx0 = int((w - nw) / 2)
        draw.rounded_rectangle([nx0, by0, nx0 + nw, by0 + int(4*scale)], radius=int(2*scale), fill=(28, 36, 48, 255))
        
        tcx = int((dx0 + dx1) / 2)
        tw = int((dx1 - dx0) * 0.40)
        ty1 = dy1 - int(12 * scale)
        ty0 = ty1 - int(14 * scale)
        tx0, tx1 = tcx - int(tw / 2), tcx + int(tw / 2)
        draw.line([(tx0, ty0), (tx0, ty1), (tx1, ty1), (tx1, ty0)], fill=(110, 231, 183, 255), width=int(3*scale), joint='curve')
        
        aw = int(tw * 0.45)
        ahw = int(tw * 0.85)
        atop = dy0 + int(6 * scale)
        aneck = ty1 - int(18 * scale)
        abot = ty1 - int(5 * scale)
        draw.polygon([(tcx - int(aw/2), atop), (tcx + int(aw/2), atop), (tcx + int(aw/2), aneck), (tcx + int(ahw/2), aneck), (tcx, abot), (tcx - int(ahw/2), aneck), (tcx - int(aw/2), aneck)], fill=(52, 211, 153, 255))
        
        draw.ellipse([int(w*0.84), int(h*0.25), int(w*0.84)+int(4*scale), int(h*0.25)+int(4*scale)], fill=(251, 191, 36, 180))
        draw.ellipse([int(w*0.87), int(h*0.35), int(w*0.87)+int(3*scale), int(h*0.35)+int(3*scale)], fill=(244, 114, 182, 180))
        draw.ellipse([int(w*0.13), int(h*0.48), int(w*0.13)+int(3*scale), int(h*0.48)+int(3*scale)], fill=(147, 197, 253, 180))
        
        img.resize((width, height), Image.Resampling.LANCZOS).save(placeholder_path)

    # 3. Video & Audio Icons
    v_icon_path = os.path.join(CUR_DIR, "icon_video.png")
    if not os.path.exists(v_icon_path):
        s = 48 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bx0, by0, bx1, by1 = int(s*0.16), int(s*0.28), int(s*0.62), int(s*0.72)
        color = (56, 189, 248, 255)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(6*scale), outline=color, width=int(2.5*scale))
        draw.polygon([(int(s*0.65), int(s*0.40)), (int(s*0.84), int(s*0.30)), (int(s*0.84), int(s*0.70)), (int(s*0.65), int(s*0.60))], outline=color, fill=(56, 189, 248, 40))
        cx, cy = int((bx0+bx1)/2), int((by0+by1)/2)
        cr = int(6*scale)
        draw.ellipse([cx-cr, cy-cr, cx+cr, cy+cr], outline=color, width=int(2*scale))
        img.resize((48, 48), Image.Resampling.LANCZOS).save(v_icon_path)

    a_icon_path = os.path.join(CUR_DIR, "icon_audio.png")
    if not os.path.exists(a_icon_path):
        s = 48 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (251, 113, 133, 255)
        draw.arc([int(s*0.20), int(s*0.20), int(s*0.80), int(s*0.76)], start=180, end=0, fill=color, width=int(3*scale))
        ew, eh = int(6*scale), int(14*scale)
        draw.rounded_rectangle([int(s*0.16), int(s*0.48), int(s*0.16)+ew, int(s*0.48)+eh], radius=int(3*scale), fill=color)
        draw.rounded_rectangle([int(s*0.84)-ew, int(s*0.48), int(s*0.84), int(s*0.48)+eh], radius=int(3*scale), fill=color)
        cx = int(s*0.50)
        for dy, h_bar in [(-12, 10), (-6, 18), (0, 24), (6, 18), (12, 10)]:
            bx = cx + int(dy*scale*0.7)
            by = int(s*0.55)
            bh = int(h_bar*scale*0.5)
            draw.line([(bx, by-bh), (bx, by+bh)], fill=color, width=int(2*scale))
        img.resize((48, 48), Image.Resampling.LANCZOS).save(a_icon_path)

    # 4. Small UI badges (Search, Check, Switches, Gear, Folder)
    s_icon = os.path.join(CUR_DIR, "icon_search.png")
    if not os.path.exists(s_icon):
        s = 28 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (148, 163, 184, 255)
        cr, cx, cy = int(s*0.28), int(s*0.40), int(s*0.40)
        draw.ellipse([cx-cr, cy-cr, cx+cr, cy+cr], outline=color, width=int(2.5*scale))
        draw.line([(int(cx+cr*0.70), int(cy+cr*0.70)), (int(s*0.82), int(s*0.82))], fill=color, width=int(3*scale))
        img.resize((28, 28), Image.Resampling.LANCZOS).save(s_icon)

    c_icon = os.path.join(CUR_DIR, "icon_check.png")
    if not os.path.exists(c_icon):
        s = 18 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, s-1, s-1], fill=(56, 189, 248, 255))
        draw.line([(int(s*0.28), int(s*0.52)), (int(s*0.44), int(s*0.68)), (int(s*0.72), int(s*0.34))], fill=(15, 23, 42, 255), width=int(2.5*scale), joint='curve')
        img.resize((18, 18), Image.Resampling.LANCZOS).save(c_icon)

    sw_on = os.path.join(CUR_DIR, "icon_switch_on.png")
    if not os.path.exists(sw_on):
        w, h = 36 * scale, 18 * scale
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = h // 2
        draw.rounded_rectangle([0, 0, w-1, h-1], radius=r, fill=(52, 211, 153, 255))
        kr = int(r * 0.70)
        knob_cx = w - r
        draw.ellipse([knob_cx-kr, r-kr, knob_cx+kr, r+kr], fill=(255, 255, 255, 255))
        img.resize((36, 18), Image.Resampling.LANCZOS).save(sw_on)

    sw_off = os.path.join(CUR_DIR, "icon_switch_off.png")
    if not os.path.exists(sw_off):
        w, h = 36 * scale, 18 * scale
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = h // 2
        draw.rounded_rectangle([0, 0, w-1, h-1], radius=r, fill=(51, 65, 85, 255))
        kr = int(r * 0.70)
        knob_cx = r
        draw.ellipse([knob_cx-kr, r-kr, knob_cx+kr, r+kr], fill=(148, 163, 184, 255))
        img.resize((36, 18), Image.Resampling.LANCZOS).save(sw_off)

    g_icon = os.path.join(CUR_DIR, "icon_gear.png")
    if not os.path.exists(g_icon):
        s = 24 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = s//2, s//2
        color = (148, 163, 184, 255)
        rout, rin = int(s*0.38), int(s*0.22)
        draw.ellipse([cx-rout, cy-rout, cx+rout, cy+rout], outline=color, width=int(2.5*scale))
        draw.ellipse([cx-rin, cy-rin, cx+rin, cy+rin], outline=color, width=int(2*scale))
        for i in range(8):
            ang = i * (math.pi / 4)
            x0 = cx + int((rout - int(2*scale)) * math.cos(ang))
            y0 = cy + int((rout - int(2*scale)) * math.sin(ang))
            x1 = cx + int((rout + int(4*scale)) * math.cos(ang))
            y1 = cy + int((rout + int(4*scale)) * math.sin(ang))
            draw.line([(x0, y0), (x1, y1)], fill=color, width=int(3*scale))
        img.resize((24, 24), Image.Resampling.LANCZOS).save(g_icon)

    f_icon = os.path.join(CUR_DIR, "icon_folder.png")
    if not os.path.exists(f_icon):
        s = 24 * scale
        img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (148, 163, 184, 255)
        fx0, fy0, fx1, fy1 = int(s*0.15), int(s*0.25), int(s*0.85), int(s*0.78)
        tw = int(s*0.30)
        draw.polygon([(fx0, fy0+int(4*scale)), (fx0, fy0), (fx0+tw, fy0), (fx0+tw+int(4*scale), fy0+int(4*scale)), (fx1, fy0+int(4*scale)), (fx1, fy1), (fx0, fy1)], outline=color, fill=(148, 163, 184, 40))
        img.resize((24, 24), Image.Resampling.LANCZOS).save(f_icon)

generate_assets()

# ----------------- Multi-Language Dictionary -----------------
STRINGS = {
    "ar": {
        "app_title": "YTB Downloader",
        "url_placeholder": "أدخل رابط يوتيوب هنا...",
        "paste_btn": "لصق (Paste)",
        "mode_video": "فيديو",
        "mode_audio": "صوت",
        "quality_title": "الجودة",
        "start_btn": "تنزيل الآن",
        "save_path_btn": "تحديد مسار الحفظ",
        "library_btn": "المكتبة",
        "settings_btn": "الإعدادات",
        "empty_preview": "يرجى إدخال الرابط للبدء",
        "fetching": "جاري فحص الرابط...",
        "downloading": "جاري التنزيل...",
        "merging": "جاري دمج وتحويل الملف...",
        "done": "اكتمل التنزيل بنجاح! 🎉",
        "failed": "تعذر التنزيل، تحقق من الرابط",
        "cancelled": "تم إلغاء التنزيل",
        "cancel_btn": "إلغاء التنزيل ⏹",
        "open_folder": "فتح المجلد 📂",
        "play_file": "تشغيل الملف ▶",
        "clipboard_empty": "الحافظة لا تحتوي على رابط يوتيوب صالح.",
        "opt_low": "ضعيفة",
        "opt_med": "متوسطة",
        "opt_good": "جيدة",
        "opt_high": "عالية",
        "opt_ultra": "فائقة",
        "dur_label": "المدة: {dur}",
        "channel_label": "القناة: {channel}",
        "speed_eta": "السرعة: {speed}  |  المتبقي: {eta}",
    },
    "en": {
        "app_title": "YTB Downloader",
        "url_placeholder": "Paste YouTube link here...",
        "paste_btn": "Paste",
        "mode_video": "Video",
        "mode_audio": "Audio",
        "quality_title": "Quality",
        "start_btn": "Download Now",
        "save_path_btn": "Select Save Path",
        "library_btn": "Library",
        "settings_btn": "Settings",
        "empty_preview": "Please enter a link to start",
        "fetching": "Fetching video info...",
        "downloading": "Downloading...",
        "merging": "Processing & merging file...",
        "done": "Download Completed! 🎉",
        "failed": "Download failed, check link",
        "cancelled": "Download cancelled",
        "cancel_btn": "Cancel ⏹",
        "open_folder": "Open Folder 📂",
        "play_file": "Play File ▶",
        "clipboard_empty": "Clipboard does not contain a valid URL.",
        "opt_low": "Low",
        "opt_med": "Medium",
        "opt_good": "Good",
        "opt_high": "High",
        "opt_ultra": "Ultra",
        "dur_label": "Duration: {dur}",
        "channel_label": "Channel: {channel}",
        "speed_eta": "Speed: {speed}  |  ETA: {eta}",
    }
}

# ----------------- Quality Definitions -----------------
VIDEO_QUALITIES = [
    {"key": "144p",  "label_ar": "أدنى",   "label_en": "Min",     "sub": "144p"},
    {"key": "240p",  "label_ar": "خفيفة",  "label_en": "Low",     "sub": "240p"},
    {"key": "360p",  "label_ar": "ضعيفة",  "label_en": "Standard","sub": "360p"},
    {"key": "480p",  "label_ar": "متوسطة", "label_en": "Medium",  "sub": "480p"},
    {"key": "720p",  "label_ar": "جيدة",   "label_en": "Good",    "sub": "720p HD"},
    {"key": "1080p", "label_ar": "عالية",  "label_en": "High",    "sub": "1080p FHD"},
    {"key": "2k",    "label_ar": "فائقة",  "label_en": "2K QHD",  "sub": "2K - 1440p"},
    {"key": "4k",    "label_ar": "قصوى",   "label_en": "4K UHD",  "sub": "4K - 2160p"}
]

AUDIO_QUALITIES = [
    {"key": "64k",   "label_ar": "ضعيفة",  "label_en": "Low",    "sub": "Low - 64k"},
    {"key": "128k",  "label_ar": "متوسطة", "label_en": "Medium", "sub": "Medium - 128k"},
    {"key": "192k",  "label_ar": "جيدة",   "label_en": "Good",   "sub": "Good - 192k"},
    {"key": "256k",  "label_ar": "عالية",  "label_en": "High",   "sub": "High - 256k"},
    {"key": "320k",  "label_ar": "فائقة",  "label_en": "Ultra",  "sub": "Ultra - 320kbps"}
]

# Helper to round image corners
def round_corners(image, radius=14):
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    rounded = Image.new('RGBA', image.size, (0, 0, 0, 0))
    rounded.paste(image, (0, 0), mask)
    return rounded


class YTBDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("YTB Downloader")
        self.geometry("980x720")
        self.minsize(880, 660)
        self.configure(fg_color="#101622")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Enable Windows 10/11 Dark Titlebar
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                value = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
                )
            except Exception:
                pass

        # Set App Window Icon
        icon_path = os.path.join(CUR_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # State Variables
        self.lang = "ar"
        self.download_dir = tk.StringVar(value=DEFAULT_DOWNLOAD_DIR)
        self.url_var = tk.StringVar()
        self.download_mode = "video"  # "video" or "audio"
        self.selected_video_idx = 5   # 1080p FHD by default (0-7)
        self.selected_audio_idx = 4   # 320kbps by default (0-4)
        
        self.current_video_id = None
        self.current_video_info = None
        self.active_thumbnail_img = None
        self.last_downloaded_file = None
        
        self.is_downloading = False
        self.current_process = None
        self.msg_queue = queue.Queue()
        self.info_cache = {}

        # Preload CTkImages
        self._load_ui_images()

        # Build UI
        self._build_header()
        self._build_main_content()
        self._build_bottom_bar()

        # Initial Language update & Selection state
        self._update_mode_ui()
        self._rebuild_quality_cards()
        self._apply_language()

        # Start background queue poller
        self.after(50, self._poll_queue)

    def _t(self, key, **kwargs):
        text = STRINGS[self.lang].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    @property
    def selected_quality_idx(self):
        return self.selected_video_idx if self.download_mode == "video" else self.selected_audio_idx

    @selected_quality_idx.setter
    def selected_quality_idx(self, val):
        if self.download_mode == "video":
            self.selected_video_idx = max(0, min(val, len(VIDEO_QUALITIES) - 1))
        else:
            self.selected_audio_idx = max(0, min(val, len(AUDIO_QUALITIES) - 1))

    def _load_ui_images(self):
        """Loads and creates CTkImage instances for crisp rendering"""
        self.img_logo = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "app_logo.png")), size=(32, 32))
        self.img_laptop = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "laptop_placeholder.png")), size=(210, 150))
        self.img_video = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_video.png")), size=(36, 36))
        self.img_audio = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_audio.png")), size=(36, 36))
        self.img_search = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_search.png")), size=(20, 20))
        self.img_check = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_check.png")), size=(16, 16))
        self.img_sw_on = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_switch_on.png")), size=(32, 16))
        self.img_sw_off = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_switch_off.png")), size=(32, 16))
        self.img_gear = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_gear.png")), size=(18, 18))
        self.img_folder = ctk.CTkImage(Image.open(os.path.join(CUR_DIR, "icon_folder.png")), size=(18, 18))

    # =========================================================================
    # --------------------------- UI BUILDERS ---------------------------------
    # =========================================================================
    def _build_header(self):
        """Top Header Bar with App Title and Centered Modern Search/Paste Capsule"""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=90)
        self.header_frame.pack(fill="x", padx=24, pady=(16, 10))
        self.header_frame.pack_propagate(False)

        # Left: App Logo & Title
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", anchor="center")

        logo_lbl = ctk.CTkLabel(title_box, image=self.img_logo, text="")
        logo_lbl.pack(side="left", padx=(0, 10))

        self.title_lbl = ctk.CTkLabel(
            title_box,
            text="YTB Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#f8fafc"
        )
        self.title_lbl.pack(side="left")

        # Center/Right: Rounded Search Box Capsule (Matching mockup exactly)
        self.search_capsule = ctk.CTkFrame(
            self.header_frame,
            fg_color="#18212e",
            border_width=1,
            border_color="#263447",
            corner_radius=18,
            width=540,
            height=78
        )
        self.search_capsule.pack(side="right", padx=(20, 0))
        self.search_capsule.pack_propagate(False)

        # Upper row inside search capsule: Paste Button + URL Entry
        input_row = ctk.CTkFrame(self.search_capsule, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(8, 0))

        # Paste Button (Cyan/Mint glowing badge on the right in Arabic layout)
        self.paste_btn = ctk.CTkButton(
            input_row,
            text=self._t("paste_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#38bdf8",
            fg_color="#152435",
            hover_color="#1d3550",
            border_width=1.5,
            border_color="#38bdf8",
            corner_radius=12,
            width=100,
            height=34,
            command=self._on_paste_click
        )
        self.paste_btn.pack(side="right", padx=(8, 0))

        # URL Entry Field (Right-aligned placeholder for Arabic, clean transparent background)
        self.url_entry = ctk.CTkEntry(
            input_row,
            textvariable=self.url_var,
            placeholder_text=self._t("url_placeholder"),
            placeholder_text_color="#64748b",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#f8fafc",
            fg_color="transparent",
            border_width=0,
            justify="right",
            height=34
        )
        self.url_entry.pack(side="right", fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda e: self._trigger_fetch())
        self.url_var.trace_add("write", self._on_url_typing)

        # Lower row inside search capsule: Search icon button
        search_icon_btn = ctk.CTkButton(
            self.search_capsule,
            image=self.img_search,
            text="",
            width=28,
            height=20,
            fg_color="transparent",
            hover_color="#223043",
            corner_radius=6,
            command=self._trigger_fetch
        )
        search_icon_btn.pack(side="bottom", pady=(0, 4))

    def _build_main_content(self):
        """Split 2-Column Section: Left Controls (Mode, Quality, Actions) & Right Preview Card"""
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=24, pady=(6, 12))
        self.content_frame.grid_columnconfigure(0, weight=55)  # Left controls
        self.content_frame.grid_columnconfigure(1, weight=45)  # Right preview card
        self.content_frame.grid_rowconfigure(0, weight=1)

        # ---------------- Left Controls Container ----------------
        self.left_box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # 1. Mode Cards (فيديو / صوت)
        self.mode_row = ctk.CTkFrame(self.left_box, fg_color="transparent")
        self.mode_row.pack(fill="x", pady=(0, 10))
        self.mode_row.grid_columnconfigure((0, 1), weight=1)

        # Video Mode Card
        self.card_video = ctk.CTkFrame(
            self.mode_row,
            corner_radius=14,
            height=80,
            cursor="hand2"
        )
        self.card_video.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.card_video.pack_propagate(False)
        self.card_video.bind("<Button-1>", lambda e: self._set_mode("video"))

        v_content = ctk.CTkFrame(self.card_video, fg_color="transparent")
        v_content.place(relx=0.5, rely=0.5, anchor="center")
        v_content.bind("<Button-1>", lambda e: self._set_mode("video"))

        self.lbl_v_icon = ctk.CTkLabel(v_content, image=self.img_video, text="")
        self.lbl_v_icon.pack(side="top", pady=(0, 2))
        self.lbl_v_icon.bind("<Button-1>", lambda e: self._set_mode("video"))

        self.lbl_v_text = ctk.CTkLabel(
            v_content,
            text=self._t("mode_video"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc"
        )
        self.lbl_v_text.pack(side="top")
        self.lbl_v_text.bind("<Button-1>", lambda e: self._set_mode("video"))

        # Audio Mode Card
        self.card_audio = ctk.CTkFrame(
            self.mode_row,
            corner_radius=14,
            height=80,
            cursor="hand2"
        )
        self.card_audio.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.card_audio.pack_propagate(False)
        self.card_audio.bind("<Button-1>", lambda e: self._set_mode("audio"))

        a_content = ctk.CTkFrame(self.card_audio, fg_color="transparent")
        a_content.place(relx=0.5, rely=0.5, anchor="center")
        a_content.bind("<Button-1>", lambda e: self._set_mode("audio"))

        self.lbl_a_icon = ctk.CTkLabel(a_content, image=self.img_audio, text="")
        self.lbl_a_icon.pack(side="top", pady=(0, 2))
        self.lbl_a_icon.bind("<Button-1>", lambda e: self._set_mode("audio"))

        self.lbl_a_text = ctk.CTkLabel(
            a_content,
            text=self._t("mode_audio"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc"
        )
        self.lbl_a_text.pack(side="top")
        self.lbl_a_text.bind("<Button-1>", lambda e: self._set_mode("audio"))

        # 2. Quality Card ("الجودة" Slider + Interactive Cards)
        self.quality_box = ctk.CTkFrame(
            self.left_box,
            fg_color="#18212e",
            border_width=1,
            border_color="#253346",
            corner_radius=16
        )
        self.quality_box.pack(fill="x", pady=(0, 12), ipady=6)

        # Header of Quality Card ("الجودة" aligned right)
        q_head = ctk.CTkFrame(self.quality_box, fg_color="transparent")
        q_head.pack(fill="x", padx=16, pady=(10, 4))

        self.lbl_quality_title = ctk.CTkLabel(
            q_head,
            text=self._t("quality_title"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#cbd5e1"
        )
        self.lbl_quality_title.pack(side="right")

        # Horizontal Cyan Slider
        self.slider = ctk.CTkSlider(
            self.quality_box,
            from_=0,
            to=7,
            number_of_steps=7,
            progress_color="#38bdf8",
            button_color="#38bdf8",
            button_hover_color="#0ea5e9",
            fg_color="#243346",
            height=16,
            command=self._on_slider_change
        )
        self.slider.set(self.selected_quality_idx)
        self.slider.pack(fill="x", padx=20, pady=(4, 8))

        # Dynamic Quality Cards Grid Container
        self.cards_grid = ctk.CTkFrame(self.quality_box, fg_color="transparent")
        self.cards_grid.pack(fill="x", padx=8, pady=(0, 6))

        self.quality_card_widgets = []

        # 3. Action Area (Glow Download Button & Save Path Button)
        action_box = ctk.CTkFrame(self.left_box, fg_color="transparent")
        action_box.pack(fill="x", pady=(4, 0))

        # Glow Halo Box around "تنزيل الآن"
        self.glow_halo = ctk.CTkFrame(
            action_box,
            fg_color="#381926",
            border_width=1.5,
            border_color="#f43f5e",
            corner_radius=22
        )
        self.glow_halo.pack(pady=(0, 8))

        self.download_btn = ctk.CTkButton(
            self.glow_halo,
            text=self._t("start_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#0f172a",
            fg_color="#bfdbfe",
            hover_color="#93c5fd",
            corner_radius=18,
            width=215,
            height=46,
            command=self._start_download_thread
        )
        self.download_btn.pack(padx=3, pady=3)

        # Save Path Button ("تحديد مسار الحفظ")
        self.save_path_btn = ctk.CTkButton(
            action_box,
            text=self._t("save_path_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#cbd5e1",
            fg_color="#1c2534",
            hover_color="#263449",
            border_width=1,
            border_color="#2a394d",
            corner_radius=14,
            width=180,
            height=34,
            command=self._browse_save_folder
        )
        self.save_path_btn.pack(pady=(0, 2))

        # ---------------- Right Preview Card ----------------
        self.preview_card = ctk.CTkFrame(
            self.content_frame,
            fg_color="#18212e",
            border_width=1,
            border_color="#253346",
            corner_radius=18
        )
        self.preview_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self._build_preview_states()

    def _build_preview_states(self):
        """Constructs elements inside Preview Card for Empty, Loaded, and Downloading states"""
        # --- State A: Empty Preview (Matching mockup laptop + arrow) ---
        self.empty_view = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.empty_view.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_laptop = ctk.CTkLabel(self.empty_view, image=self.img_laptop, text="")
        self.lbl_laptop.pack(pady=(0, 14))

        self.lbl_empty_msg = ctk.CTkLabel(
            self.empty_view,
            text=self._t("empty_preview"),
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_empty_msg.pack()

        # --- State B: Loaded / Downloading View ---
        self.loaded_view = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        # Kept unmapped until video info or download begins

        # Video Thumbnail Image Label
        self.thumb_label = ctk.CTkLabel(
            self.loaded_view,
            text="",
            corner_radius=14
        )
        self.thumb_label.pack(padx=16, pady=(16, 10))

        # Video Title
        self.video_title_lbl = ctk.CTkLabel(
            self.loaded_view,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc",
            wraplength=340,
            justify="center"
        )
        self.video_title_lbl.pack(padx=14, pady=(0, 4))

        # Channel & Duration Badges Frame
        self.meta_frame = ctk.CTkFrame(self.loaded_view, fg_color="transparent")
        self.meta_frame.pack(pady=(0, 8))

        self.channel_lbl = ctk.CTkLabel(
            self.meta_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#38bdf8"
        )
        self.channel_lbl.pack(side="left", padx=8)

        self.dur_lbl = ctk.CTkLabel(
            self.meta_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cbd5e1"
        )
        self.dur_lbl.pack(side="left", padx=8)

        # Progress / Status Section (Visible during and after download)
        self.progress_section = ctk.CTkFrame(self.loaded_view, fg_color="transparent")
        self.progress_section.pack(fill="x", padx=20, pady=(6, 0))

        # Big Percent Text
        self.percent_lbl = ctk.CTkLabel(
            self.progress_section,
            text="0%",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color="#38bdf8"
        )
        self.percent_lbl.pack(pady=(0, 2))

        # Cyan Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_section,
            progress_color="#38bdf8",
            fg_color="#243346",
            height=10,
            corner_radius=5
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=4)

        # Status & Speed / ETA Text
        self.status_detail_lbl = ctk.CTkLabel(
            self.progress_section,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        self.status_detail_lbl.pack(pady=2)

        # Action Buttons inside preview (Cancel / Open folder / Play)
        self.preview_action_box = ctk.CTkFrame(self.loaded_view, fg_color="transparent")
        self.preview_action_box.pack(pady=(8, 12))

        self.cancel_btn = ctk.CTkButton(
            self.preview_action_box,
            text=self._t("cancel_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=32,
            width=130,
            corner_radius=10,
            command=self._cancel_download
        )
        self.cancel_btn.pack(side="left", padx=4)

        self.open_file_btn = ctk.CTkButton(
            self.preview_action_box,
            text=self._t("open_folder"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#38bdf8",
            hover_color="#0284c7",
            text_color="#0f172a",
            height=32,
            width=130,
            corner_radius=10,
            command=self._open_download_dir
        )
        # unmapped until download finishes

    def _build_bottom_bar(self):
        """Bottom bar with Settings Icon, Library Button, and Active Save Path indicator"""
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent", height=42)
        self.bottom_bar.pack(fill="x", padx=24, pady=(0, 14))
        self.bottom_bar.pack_propagate(False)

        # Left: Settings & Library Buttons (matching mockup)
        left_ctrls = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        left_ctrls.pack(side="left")

        # Gear / Settings button
        self.btn_settings = ctk.CTkButton(
            left_ctrls,
            image=self.img_gear,
            text="",
            width=36,
            height=36,
            fg_color="#18212e",
            hover_color="#253346",
            border_width=1,
            border_color="#253346",
            corner_radius=10,
            command=self._open_settings_dialog
        )
        self.btn_settings.pack(side="left", padx=(0, 8))

        # Library button ("المكتبة")
        self.btn_library = ctk.CTkButton(
            left_ctrls,
            image=self.img_folder,
            text=self._t("library_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#cbd5e1",
            compound="left",
            width=96,
            height=36,
            fg_color="#18212e",
            hover_color="#253346",
            border_width=1,
            border_color="#253346",
            corner_radius=10,
            command=self._open_download_dir
        )
        self.btn_library.pack(side="left")

        # Right: Path indicator
        self.path_lbl = ctk.CTkLabel(
            self.bottom_bar,
            text=f"📂 {self.download_dir.get()}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        self.path_lbl.pack(side="right")

    # =========================================================================
    # ----------------------- MODE & QUALITY CONTROLS -------------------------
    # =========================================================================
    def _set_mode(self, mode):
        if self.download_mode == mode:
            return
        self.download_mode = mode
        self._update_mode_ui()

        quals = VIDEO_QUALITIES if self.download_mode == "video" else AUDIO_QUALITIES
        max_idx = len(quals) - 1
        self.slider.configure(from_=0, to=max_idx, number_of_steps=max_idx)
        self.slider.set(self.selected_quality_idx)
        self._rebuild_quality_cards()

    def _update_mode_ui(self):
        """Updates borders and highlights for Video vs Audio mode cards"""
        if self.download_mode == "video":
            # Video Active (Cyan Glow)
            self.card_video.configure(
                fg_color="#162638",
                border_width=2,
                border_color="#38bdf8"
            )
            # Audio Inactive
            self.card_audio.configure(
                fg_color="#18212e",
                border_width=1,
                border_color="#253346"
            )
        else:
            # Audio Active (Coral/Rose Glow)
            self.card_audio.configure(
                fg_color="#331c28",
                border_width=2,
                border_color="#fb7185"
            )
            # Video Inactive
            self.card_video.configure(
                fg_color="#18212e",
                border_width=1,
                border_color="#253346"
            )

    def _on_slider_change(self, val):
        idx = int(round(val))
        if idx != self.selected_quality_idx:
            self.selected_quality_idx = idx
            self._update_quality_cards_state()

    def _set_quality_index(self, idx):
        self.selected_quality_idx = idx
        self.slider.set(idx)
        self._update_quality_cards_state()

    def _rebuild_quality_cards(self):
        """Dynamically creates quality cards: 8 (in 2 rows of 4) for video, 5 for audio"""
        for w in self.cards_grid.winfo_children():
            w.destroy()

        quals = VIDEO_QUALITIES if self.download_mode == "video" else AUDIO_QUALITIES
        n = len(quals)
        cols = 4 if n == 8 else 5

        for c in range(cols):
            self.cards_grid.grid_columnconfigure(c, weight=1)

        self.quality_card_widgets = []
        for i, q_data in enumerate(quals):
            r = i // cols
            c = i % cols
            c_frame = ctk.CTkFrame(
                self.cards_grid,
                corner_radius=10,
                cursor="hand2",
                height=66
            )
            c_frame.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            c_frame.pack_propagate(False)
            c_frame.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            top_bar = ctk.CTkFrame(c_frame, fg_color="transparent")
            top_bar.pack(fill="x", padx=4, pady=(4, 1))
            top_bar.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            chk_lbl = ctk.CTkLabel(top_bar, image=self.img_check, text="", width=16, height=16)
            chk_lbl.pack(side="right")
            chk_lbl.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            sw_lbl = ctk.CTkLabel(top_bar, image=self.img_sw_off, text="", width=32, height=16)
            sw_lbl.pack(side="left")
            sw_lbl.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            label_text = q_data[f"label_{self.lang}"]
            main_lbl = ctk.CTkLabel(
                c_frame,
                text=label_text,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#f8fafc"
            )
            main_lbl.pack(side="top", pady=(1, 0))
            main_lbl.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            sub_lbl = ctk.CTkLabel(
                c_frame,
                text=q_data["sub"],
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color="#94a3b8"
            )
            sub_lbl.pack(side="top")
            sub_lbl.bind("<Button-1>", lambda e, idx=i: self._set_quality_index(idx))

            self.quality_card_widgets.append({
                "frame": c_frame,
                "chk": chk_lbl,
                "sw": sw_lbl,
                "main": main_lbl,
                "sub": sub_lbl
            })

        self._update_quality_cards_state()

    def _update_quality_cards_state(self):
        """Updates active/inactive visual styling for currently selected card"""
        sel_idx = self.selected_quality_idx
        for i, w in enumerate(self.quality_card_widgets):
            if i == sel_idx:
                w["frame"].configure(
                    fg_color="#182d3e",
                    border_width=2,
                    border_color="#38bdf8"
                )
                w["sw"].configure(image=self.img_sw_on)
                w["chk"].pack(side="right")
            else:
                w["frame"].configure(
                    fg_color="#151d28",
                    border_width=1,
                    border_color="#253346"
                )
                w["sw"].configure(image=self.img_sw_off)
                w["chk"].pack_forget()

    def _update_quality_cards(self):
        self._rebuild_quality_cards()

    # =========================================================================
    # ----------------- INSTANT VIDEO & THUMBNAIL FETCHING --------------------
    # =========================================================================
    def _extract_video_id(self, url):
        """Instantly parses YouTube video ID in 0.0001 seconds via Regex"""
        if not url:
            return None
        url = url.strip()
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?\/]|$)',
            r'(?:embed\/|v\/|shorts\/)([0-9A-Za-z_-]{11})',
            r'youtu\.be\/([0-9A-Za-z_-]{11})',
            r'youtube\.com\/live\/([0-9A-Za-z_-]{11})'
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
            return url
        return None

    def _on_paste_click(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_var.set(text)
                self._trigger_fetch()
            else:
                messagebox.showinfo("!", self._t("clipboard_empty"))
        except Exception:
            messagebox.showinfo("!", self._t("clipboard_empty"))

    def _on_url_typing(self, *args):
        # Auto-trigger fetch when a complete link is pasted or typed
        raw = self.url_var.get().strip()
        vid = self._extract_video_id(raw)
        if vid and vid != self.current_video_id:
            self._trigger_fetch()

    def _trigger_fetch(self):
        url = self.url_var.get().strip()
        if not url:
            return

        vid = self._extract_video_id(url)
        self.current_video_id = vid

        # Switch Preview Card to Loading / Details View
        self.empty_view.place_forget()
        self.loaded_view.pack(fill="both", expand=True)
        self.progress_section.pack_forget()
        self.cancel_btn.pack_forget()
        self.open_file_btn.pack_forget()

        self.video_title_lbl.configure(text=self._t("fetching"))
        self.channel_lbl.configure(text="")
        self.dur_lbl.configure(text="")

        # Check Cache for Instant 0ms Load
        if vid and vid in self.info_cache:
            self._apply_cached_info(self.info_cache[vid])
            return

        # Start Fast Multi-Threaded Fetcher
        threading.Thread(target=self._fast_fetch_worker, args=(url, vid), daemon=True).start()

    def _apply_cached_info(self, data):
        self.current_video_info = data
        self.video_title_lbl.configure(text=data.get("title", ""))
        self.channel_lbl.configure(text=self._t("channel_label", channel=data.get("channel", "--")))
        self.dur_lbl.configure(text=self._t("dur_label", dur=data.get("duration", "--")))
        if "ctk_thumb" in data:
            self.thumb_label.configure(image=data["ctk_thumb"])

    def _fast_fetch_worker(self, url, vid):
        """
        Ultra-fast dual-stage fetcher:
        Stage 1: Instant oEmbed Title & Author (<300ms) + Direct HD Thumbnail (<300ms)
        Stage 2: Fast yt-dlp duration & formats in background
        """
        title = None
        author = None
        dur_str = "--:--"

        # 1. YouTube oEmbed (Lightning Fast)
        if vid:
            try:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
                req = urllib.request.Request(oembed_url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=3.5) as resp:
                    oembed_data = json.loads(resp.read().decode('utf-8'))
                    title = oembed_data.get("title")
                    author = oembed_data.get("author_name")
                    self.msg_queue.put(('quick_info', title, author))
            except Exception:
                pass

            # Fetch HD Thumbnail immediately
            self._fetch_hd_thumbnail_youtube(vid)

        # 2. Parallel yt-dlp for exact duration & non-YouTube URLs
        try:
            cmd = [
                YT_DLP_EXE,
                "--dump-single-json",
                "--no-warnings",
                "--skip-download",
                "--no-playlist",
                "--playlist-items", "1",
                "--compat-options", "no-youtube-unavailable-videos",
                url
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
                timeout=12
            )
            if res.returncode == 0 and res.stdout.strip():
                ydata = json.loads(res.stdout)
                final_title = ydata.get("title") or title or "YouTube Video"
                final_author = ydata.get("uploader") or ydata.get("channel") or author or "--"
                dur_sec = ydata.get("duration", 0)
                if dur_sec:
                    m, s = divmod(int(dur_sec), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

                # Non-YouTube fallback thumbnail
                if not vid and ydata.get("thumbnail"):
                    self._fetch_thumbnail_generic(ydata.get("thumbnail"))

                info_pkg = {
                    "title": final_title,
                    "channel": final_author,
                    "duration": dur_str,
                    "raw": ydata
                }
                if vid:
                    self.info_cache[vid] = info_pkg

                self.msg_queue.put(('full_info', info_pkg))
            else:
                if not title:
                    self.msg_queue.put(('fetch_error', None))
        except Exception:
            if not title:
                self.msg_queue.put(('fetch_error', None))

    def _fetch_hd_thumbnail_youtube(self, vid):
        """Tries MaxRes -> SD -> HQ -> MQ thumbnails with automatic SSL bypass and Lanczos anti-aliasing"""
        urls = [
            f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"
        ]
        for t_url in urls:
            try:
                req = urllib.request.Request(t_url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=3.5) as resp:
                    raw_data = resp.read()
                if len(raw_data) > 1000: # Valid JPEG (not 404 transparent placeholder)
                    pil_img = Image.open(io.BytesIO(raw_data)).convert("RGB")
                    # Scale to 16:9 crisp card dimensions (350 x 197)
                    pil_img = pil_img.resize((350, 197), Image.Resampling.LANCZOS)
                    pil_img = round_corners(pil_img, radius=12)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(350, 197))
                    self.active_thumbnail_img = ctk_img
                    if vid in self.info_cache:
                        self.info_cache[vid]["ctk_thumb"] = ctk_img
                    self.msg_queue.put(('thumb_ready', ctk_img))
                    return
            except Exception:
                continue

    def _fetch_thumbnail_generic(self, thumb_url):
        try:
            req = urllib.request.Request(thumb_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=5) as resp:
                raw_data = resp.read()
            pil_img = Image.open(io.BytesIO(raw_data)).convert("RGB")
            pil_img = pil_img.resize((350, 197), Image.Resampling.LANCZOS)
            pil_img = round_corners(pil_img, radius=12)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(350, 197))
            self.msg_queue.put(('thumb_ready', ctk_img))
        except Exception:
            pass

    # =========================================================================
    # ------------------- HIGH SPEED DOWNLOAD PIPELINE ------------------------
    # =========================================================================
    def _start_download_thread(self):
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("!", self._t("empty_preview"))
            return

        save_path = self.download_dir.get().strip()
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return

        # Prepare UI for Download Mode
        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.progress_section.pack(fill="x", padx=20, pady=(6, 0))
        self.cancel_btn.pack(side="left", padx=4)
        self.open_file_btn.pack_forget()

        self.progress_bar.set(0)
        self.percent_lbl.configure(text="0%", text_color="#38bdf8")
        self.status_detail_lbl.configure(text=self._t("downloading"))

        quals = VIDEO_QUALITIES if self.download_mode == "video" else AUDIO_QUALITIES
        selected_key = quals[self.selected_quality_idx]["key"]

        cmd = self._build_fast_download_command(url, save_path, self.download_mode, selected_key)

        # Clear queue
        while not self.msg_queue.empty():
            try:
                self.msg_queue.get_nowait()
            except queue.Empty:
                break

        threading.Thread(target=self._download_worker, args=(cmd, self.download_mode), daemon=True).start()

    def _build_fast_download_command(self, url, save_path, mode, quality_key):
        """Constructs yt-dlp command with distinct filenames per quality and 5-stream acceleration"""
        if mode == "video":
            outtmpl = os.path.join(save_path, f"%(title)s [{quality_key}].%(ext)s")
        else:
            outtmpl = os.path.join(save_path, f"%(title)s [Audio {quality_key}].%(ext)s")

        cmd = [
            YT_DLP_EXE,
            "--newline",
            "--force-overwrites",
            "--progress-template",
            "PROGRESS_DATA:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s|%(progress.filename)s",
            "--ffmpeg-location", FFMPEG_EXE,
            "--windows-filenames",
            "--concurrent-fragments", "5",  # 5x-8x download speed accelerator!
            "--buffer-size", "64K",
            "--retries", "10",
            "--fragment-retries", "10",
            "--no-playlist",
            "-o", outtmpl
        ]

        if mode == "video":
            if quality_key == "4k":
                cmd += ["-f", "bestvideo[height<=2160]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best", "--merge-output-format", "mp4"]
            elif quality_key == "2k":
                cmd += ["-f", "bestvideo[height<=1440]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]/best", "--merge-output-format", "mp4"]
            elif quality_key == "1080p":
                cmd += ["-f", "bestvideo[height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best", "--merge-output-format", "mp4"]
            elif quality_key == "720p":
                cmd += ["-f", "bestvideo[height<=720]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best", "--merge-output-format", "mp4"]
            elif quality_key == "480p":
                cmd += ["-f", "bestvideo[height<=480]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best", "--merge-output-format", "mp4"]
            elif quality_key == "360p":
                cmd += ["-f", "bestvideo[height<=360]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]/best", "--merge-output-format", "mp4"]
            elif quality_key == "240p":
                cmd += ["-f", "bestvideo[height<=240]+bestaudio[ext=m4a]/bestvideo[height<=240]+bestaudio/best[height<=240]/best", "--merge-output-format", "mp4"]
            elif quality_key == "144p":
                cmd += ["-f", "bestvideo[height<=144]+bestaudio[ext=m4a]/bestvideo[height<=144]+bestaudio/best[height<=144]/best", "--merge-output-format", "mp4"]
            else:
                cmd += ["-f", "bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best", "--merge-output-format", "mp4"]
        else: # Audio mode
            audio_rate = quality_key if quality_key.endswith("k") else "320k"
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", audio_rate]

        cmd.append(url)
        return cmd

    def _download_worker(self, cmd, mode):
        cancelled = False
        success = False
        stream_count = 0
        last_file = None
        has_downloaded_data = False

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW
            )
            self.current_process = proc

            for raw_line in proc.stdout:
                line = raw_line.strip()
                if not line:
                    continue

                if "[download] Destination:" in line:
                    stream_count += 1
                    dest = line.replace("[download] Destination:", "").strip()
                    if dest:
                        last_file = dest

                elif "[ExtractAudio] Destination:" in line:
                    dest = line.replace("[ExtractAudio] Destination:", "").strip()
                    if dest:
                        last_file = dest

                elif "[Merger] Merging formats into" in line:
                    m = re.search(r'Merging formats into ["\'](.*?)["\']', line)
                    if m:
                        last_file = m.group(1).strip()

                if "PROGRESS_DATA:" in line:
                    parts = line.replace("PROGRESS_DATA:", "").split("|")
                    if len(parts) >= 3:
                        p_raw = parts[0].replace("%", "").strip()
                        speed_str = parts[1].strip() if len(parts) > 1 else "--"
                        eta_str = parts[2].strip() if len(parts) > 2 else "--"
                        if len(parts) > 3 and parts[3].strip():
                            last_file = parts[3].strip()

                        try:
                            p_val = float(p_raw)
                            if p_val > 0:
                                has_downloaded_data = True
                            # Smooth combined progress calculation
                            if mode == "video":
                                if stream_count <= 1:
                                    overall = p_val * 0.85
                                else:
                                    overall = 85.0 + (p_val * 0.10)
                            else:
                                overall = p_val * 0.90

                            ratio = min(max(overall / 100.0, 0.0), 0.98)
                            self.msg_queue.put(('progress', ratio, int(overall), speed_str, eta_str))
                        except ValueError:
                            pass

                elif "[ExtractAudio]" in line or "[Merger]" in line:
                    self.msg_queue.put(('merging',))

            proc.wait()
            if proc.returncode == 0:
                # Genuine verification: at least one stream was downloaded OR valid file was produced
                if (last_file and os.path.exists(last_file) and os.path.getsize(last_file) > 0) or stream_count > 0 or has_downloaded_data:
                    success = True
                else:
                    success = False
            elif proc.returncode < 0:
                cancelled = True
        except Exception:
            pass

        self.msg_queue.put(('download_done', success, cancelled, last_file))

    def _cancel_download(self):
        if self.is_downloading and self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass
            self.status_detail_lbl.configure(text=self._t("cancelled"), text_color="#ef4444")

    # =========================================================================
    # ------------------------- QUEUE POLLER & EVENTS -------------------------
    # =========================================================================
    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                m_type = item[0]

                if m_type == 'quick_info':
                    _, title, author = item
                    if title:
                        self.video_title_lbl.configure(text=title)
                    if author:
                        self.channel_lbl.configure(text=self._t("channel_label", channel=author))

                elif m_type == 'thumb_ready':
                    _, ctk_img = item
                    self.thumb_label.configure(image=ctk_img)

                elif m_type == 'full_info':
                    _, pkg = item
                    self._apply_cached_info(pkg)

                elif m_type == 'fetch_error':
                    self.video_title_lbl.configure(text=self._t("failed"))

                elif m_type == 'progress':
                    _, ratio, overall_pct, speed, eta = item
                    self.progress_bar.set(ratio)
                    self.percent_lbl.configure(text=f"{overall_pct}%")
                    self.status_detail_lbl.configure(text=self._t("speed_eta", speed=speed, eta=eta))

                elif m_type == 'merging':
                    self.progress_bar.set(0.96)
                    self.percent_lbl.configure(text="96%")
                    self.status_detail_lbl.configure(text=self._t("merging"))

                elif m_type == 'download_done':
                    _, success, cancelled, last_file = item
                    self._on_download_complete(success, cancelled, last_file)

        except queue.Empty:
            pass

        self.after(40, self._poll_queue)

    def _on_download_complete(self, success, cancelled, last_file):
        self.is_downloading = False
        self.current_process = None
        self.download_btn.configure(state="normal")
        self.cancel_btn.pack_forget()

        if cancelled:
            self.percent_lbl.configure(text="--", text_color="#ef4444")
            self.status_detail_lbl.configure(text=self._t("cancelled"), text_color="#ef4444")
        elif success:
            self.progress_bar.set(1.0)
            self.percent_lbl.configure(text="100%", text_color="#22c55e")
            self.status_detail_lbl.configure(text=self._t("done"), text_color="#22c55e")
            self.last_downloaded_file = last_file
            self.open_file_btn.pack(side="left", padx=4)
        else:
            self.percent_lbl.configure(text="Error", text_color="#ef4444")
            self.status_detail_lbl.configure(text=self._t("failed"), text_color="#ef4444")

    # =========================================================================
    # ------------------------ NAVIGATION & SETTINGS --------------------------
    # =========================================================================
    def _browse_save_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.download_dir.get())
        if chosen:
            self.download_dir.set(chosen)
            self.path_lbl.configure(text=f"📂 {chosen}")

    def _open_download_dir(self):
        folder = self.download_dir.get()
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showerror("Error", f"Folder not found: {folder}")

    def _open_settings_dialog(self):
        """Displays modern settings popup modal"""
        win = ctk.CTkToplevel(self)
        win.title(self._t("settings_btn"))
        win.geometry("380x300")
        win.resizable(False, False)
        win.configure(fg_color="#141c28")
        win.attributes("-topmost", True)

        lbl = ctk.CTkLabel(
            win,
            text=self._t("settings_btn"),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc"
        )
        lbl.pack(pady=(20, 16))

        # Language Switcher
        lang_frame = ctk.CTkFrame(win, fg_color="#1a2535", corner_radius=12)
        lang_frame.pack(fill="x", padx=24, pady=8)

        l_lbl = ctk.CTkLabel(
            lang_frame,
            text="اللغة / Language:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#cbd5e1"
        )
        l_lbl.pack(side="left", padx=14, pady=12)

        lang_seg = ctk.CTkSegmentedButton(
            lang_frame,
            values=["العربية", "English"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_language_change
        )
        lang_seg.set("العربية" if self.lang == "ar" else "English")
        lang_seg.pack(side="right", padx=14, pady=12)

        # About info
        about_box = ctk.CTkFrame(win, fg_color="#1a2535", corner_radius=12)
        about_box.pack(fill="x", padx=24, pady=8)

        a_lbl = ctk.CTkLabel(
            about_box,
            text="YTB Downloader v2.5\nUltra-Fast High-DPI Engine",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        a_lbl.pack(pady=12)

    def _on_language_change(self, val):
        self.lang = "ar" if val == "العربية" else "en"
        self._apply_language()
        self._update_quality_cards()

    def _apply_language(self):
        self.title_lbl.configure(text=self._t("app_title"))
        self.url_entry.configure(placeholder_text=self._t("url_placeholder"))
        self.paste_btn.configure(text=self._t("paste_btn"))
        self.lbl_v_text.configure(text=self._t("mode_video"))
        self.lbl_a_text.configure(text=self._t("mode_audio"))
        self.lbl_quality_title.configure(text=self._t("quality_title"))
        self.download_btn.configure(text=self._t("start_btn"))
        self.save_path_btn.configure(text=self._t("save_path_btn"))
        self.btn_library.configure(text=self._t("library_btn"))
        self.lbl_empty_msg.configure(text=self._t("empty_preview"))
        self.cancel_btn.configure(text=self._t("cancel_btn"))
        self.open_file_btn.configure(text=self._t("open_folder"))
        self._update_quality_cards()


if __name__ == "__main__":
    app = YTBDownloaderApp()
    app.mainloop()
