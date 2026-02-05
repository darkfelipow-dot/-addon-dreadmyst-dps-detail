import socket, threading, struct, time, os, sys, json, ctypes
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, colorchooser
from collections import defaultdict
REAL_PORT = 16383
CONFIG_FILE = "dps_names.json"
SETTINGS_FILE = "dps_settings.json"
COLOR_BG = "#1e1e1e"
COLOR_FG = "#ffffff"
COLOR_LIST_BG = "#2d2d2d"
COLOR_PLAYER_DEFAULT = "#4CAF50" 
COLOR_MONSTER = "#F44336"
COLOR_DPS_BAR = "#66BB6A"
FONT_TITLE = ("Segoe UI", 9, "bold")
FONT_MONO = ("Consolas", 9)
FONT_OVERLAY = ("Segoe UI", 9, "bold")
TRANSLATIONS = {
    "ESP": {
        "PLAYER_DAMAGE": "DAÑO JUGADOR",
        "RESET_PLAYERS": "RESETEAR JUGADORES",
        "PAUSE": "PAUSAR",
        "RESUME": "REANUDAR",
        "SHOW_HP": "Overlay HP",
        "SHOW_MINI_P": "Overlay DPS (Jugador)",
        "SHOW_MINI_M": "Overlay DPS (Monstruo)",
        "SHOW_MINI_H": "Overlay Heal",
        "RESET_ID": "RESETEAR ID",
        "MONSTER_DAMAGE": "DAÑO MONSTRUO",
        "RESET_MONSTERS": "RESETEAR MONSTRUOS",
        "STATUS_READY": "Estado: Listo",
        "STATUS_ACTIVE": "Estado: SNIFFER ACTIVO (Espiando...)",
        "DEBUG_MSG": "Capturando paquetes desconocidos...",
        "COL_NAME": "NOMBRE/ID",
        "COL_DMG": "DAÑO",
        "COL_DPS": "DPS",
        "SYNC_OK": "SINCRO OK",
        "HIT_TO_LOCK": "GOLPEA PARA BLOQUEAR...",
        "CHOOSE_NET": "Elige tu Tarjeta de Red",
        "START_CAP": "INICIAR CAPTURA",
        "SELECT_CONN": "Selecciona tu conexión de Internet:",
        "ASK_ADMIN": "Ejecuta como Administrador",
        "NO_DEVICES": "No se encontraron dispositivos de red",
        "WIN_TITLE_SEL": "Elige tu Tarjeta de Red",
        "BTN_LANG": "IDIOMA/LANG",
        "RENAME": "Renombrar",
        "NEW_NAME": "Nuevo Nombre:",
        "ASK_COLOR": "Elige color de Barra HP",
        "ASK_ALPHA": "Transparencia",
        "ASK_ALPHA_MSG": "Nivel de transparencia (0.1 a 1.0):",
        "OV_TITLE_PLAYER": "Detalle Daño Jugador",
        "OV_TITLE_MONSTER": "Detalle Daño Monstruo",
        "DEBUG_TITLE": "Packet Sniffer - DEBUG",
        "DEBUG_INFO": "Capturando paquetes desconocidos... (Usa esto para ver Casts)"
    },
    "ENG": {
        "PLAYER_DAMAGE": "PLAYER DAMAGE",
        "RESET_PLAYERS": "RESET PLAYERS",
        "PAUSE": "PAUSE",
        "RESUME": "RESUME",
        "SHOW_HP": "Overlay HP",
        "SHOW_MINI_P": "Overlay DPS (Player)",
        "SHOW_MINI_M": "Overlay DPS (Monster)",
        "SHOW_MINI_H": "Overlay Heal",
        "RESET_ID": "RESET ID",
        "MONSTER_DAMAGE": "MONSTER DAMAGE",
        "RESET_MONSTERS": "RESET MONSTERS",
        "STATUS_READY": "Status: Ready",
        "STATUS_ACTIVE": "Status: SNIFFER ACTIVE (Spying...)",
        "DEBUG_MSG": "Capturing unknown packets...",
        "COL_NAME": "NAME/ID",
        "COL_DMG": "DAMAGE",
        "COL_DPS": "DPS",
        "SYNC_OK": "SYNC OK",
        "HIT_TO_LOCK": "HIT TO LOCK...",
        "CHOOSE_NET": "Choose Network Card",
        "START_CAP": "START CAPTURE",
        "SELECT_CONN": "Select your Internet connection:",
        "ASK_ADMIN": "Run as Administrator",
        "NO_DEVICES": "No Network Devices found",
        "WIN_TITLE_SEL": "Choose Network Card",
        "BTN_LANG": "LANG/IDIOMA",
        "RENAME": "Rename",
        "NEW_NAME": "New Name:",
        "ASK_COLOR": "Choose HP Bar Color",
        "ASK_ALPHA": "Transparency",
        "ASK_ALPHA_MSG": "Transparency Level (0.1 to 1.0):",
        "OV_TITLE_PLAYER": "Player DMG Detail",
        "OV_TITLE_MONSTER": "Monster DMG Detail",
        "DEBUG_TITLE": "Packet Sniffer - DEBUG",
        "DEBUG_INFO": "Capturing unknown packets... (Use to see Casts)"
    }
}
from ctypes import *
class sockaddr(Structure):
    _fields_ = [("sa_family", c_ushort), ("sa_data", c_ubyte * 14)]
class sockaddr_in(Structure):
    _fields_ = [("sin_family", c_short), ("sin_port", c_ushort), ("sin_addr", c_ubyte * 4), ("sin_zero", c_char * 8)]
class pcap_addr(Structure):
    pass
pcap_addr._fields_ = [("next", POINTER(pcap_addr)), ("addr", POINTER(sockaddr)), ("netmask", POINTER(sockaddr)), ("broadaddr", POINTER(sockaddr)), ("dstaddr", POINTER(sockaddr))]
class pcap_if(Structure):
    pass
pcap_if._fields_ = [("next", POINTER(pcap_if)), ("name", c_char_p), ("description", c_char_p), ("addresses", POINTER(pcap_addr)), ("flags", c_uint)]
class pcap_pkthdr(Structure):
    _fields_ = [("ts_sec", c_long), ("ts_usec", c_long), ("caplen", c_uint), ("len", c_uint)]
class bpf_program(Structure):
    _fields_ = [("bf_len", c_uint), ("bf_insns", c_void_p)]
def log_msg(msg):
    try:
        with open("dps_debug.txt", "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
    except: pass
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False
class ResizableWindow(tk.Toplevel):
    def __init__(self, parent, title, initial_x, initial_y, width, height, bg_color="#000000"):
        super().__init__(parent)
        self.overrideredirect(True)
        self.geometry(f"{width}x{height}+{initial_x}+{initial_y}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.7) 
        self.configure(bg=bg_color)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=1, highlightbackground="#333")
        self.canvas.pack(fill="both", expand=True)
        self.grip_size = 15
        self.grip = self.canvas.create_polygon(0,0,0,0,0,0, fill="#666", outline="") 
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_motion)
        self.bind("<Configure>", self.on_window_resize)
        self._is_resizing = False
        self._start_x = 0
        self._start_y = 0
        self.redraw_grip()
    def redraw_grip(self):
        w = self.winfo_width()
        h = self.winfo_height()
        gs = self.grip_size
        self.canvas.coords(self.grip, w, h, w-gs, h, w, h-gs)
        self.canvas.tag_raise(self.grip)
    def on_window_resize(self, event):
        self.redraw_grip()
        self.on_resize()
    def on_press(self, event):
        self._start_x = event.x
        self._start_y = event.y
        w, h = self.winfo_width(), self.winfo_height()
        if event.x > w - self.grip_size and event.y > h - self.grip_size:
            self._is_resizing = True
        else:
            self._is_resizing = False
    def on_motion(self, event):
        if self._is_resizing:
            new_w = max(50, event.x)
            new_h = max(20, event.y)
            self.geometry(f"{new_w}x{new_h}")
        else:
            deltax = event.x - self._start_x
            deltay = event.y - self._start_y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry(f"+{x}+{y}")
    def on_resize(self):
        pass
class HealthBarOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y, color, alpha):
        super().__init__(parent, "HP", initial_x, initial_y, 250, 40, "#000000")
        self.fill_color = color
        self.set_alpha(alpha)
        self.bar_id = self.canvas.create_rectangle(0, 0, 0, 0, fill=self.fill_color, outline="")
        self.text_id = self.canvas.create_text(10, 10, text="HP INIT", fill="white", font=FONT_OVERLAY)
        self.last_curr = 0; self.last_max = 100
    def set_alpha(self, a):
        self.attributes("-alpha", float(a))
    def update_style(self, color, alpha):
        self.fill_color = color
        self.canvas.itemconfigure(self.bar_id, fill=color)
        self.set_alpha(alpha)
        self.redraw()
    def update_data(self, current, maximum, is_pred):
        self.last_curr = current; self.last_max = maximum
        self.redraw()
    def redraw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        pct = 0
        if self.last_max > 0: pct = max(0, min(1, self.last_curr / self.last_max))
        self.canvas.coords(self.bar_id, 0, 0, w * pct, h)
        self.canvas.coords(self.text_id, w/2, h/2)
        self.canvas.itemconfigure(self.text_id, text=f"{int(self.last_curr)} / {int(self.last_max)} ({int(pct*100)}%)")
        self.redraw_grip()
    def on_resize(self):
        self.redraw()
class CastBarOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y):
        super().__init__(parent, "CAST", initial_x, initial_y, 250, 30, "#000000")
        self.bar_id = self.canvas.create_rectangle(0, 0, 0, 0, fill="#D32F2F", outline="") 
        self.text_id = self.canvas.create_text(10, 10, text="", fill="white", font=FONT_OVERLAY)
        self.progress = 0.0
        self.duration = 2.0
        self.is_casting = False
        self._anim_job = None
    def start_cast(self, name="CASTING!", duration=2.0):
        self.duration = duration
        self.progress = 0.0
        self.is_casting = True
        self.canvas.itemconfigure(self.text_id, text=name)
        if self._anim_job: self.after_cancel(self._anim_job)
        self.animate()
    def animate(self):
        if not self.is_casting: return
        self.progress += 0.05 
        pct = min(1.0, self.progress / self.duration)
        w = self.winfo_width()
        h = self.winfo_height()
        self.canvas.coords(self.bar_id, 0, 0, w * pct, h)
        self.canvas.coords(self.text_id, w/2, h/2)
        self.redraw_grip()
        if pct < 1.0:
            self._anim_job = self.after(50, self.animate)
        else:
            self.is_casting = False
            self.canvas.coords(self.bar_id, 0, 0, 0, 0) 
            self.canvas.itemconfigure(self.text_id, text="")
    def on_resize(self):
        if self.bar_id: self.redraw_grip()
class CooldownBarOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y):
        super().__init__(parent, "TIMER", initial_x, initial_y, 250, 30, "#000000")
        self.bar_id = self.canvas.create_rectangle(0, 0, 0, 0, fill="#2196F3", outline="") 
        self.text_id = self.canvas.create_text(10, 10, text="", fill="white", font=FONT_OVERLAY)
        self.progress = 0.0
        self.duration = 60.0
        self.is_running = False
        self._anim_job = None
    def start_timer(self, duration=60.0):
        self.duration = duration
        self.progress = duration
        self.is_running = True
        self.deiconify()
        if self._anim_job: self.after_cancel(self._anim_job)
        self.animate()
    def stop_timer(self):
        self.is_running = False
        self.progress = 0
        self.canvas.coords(self.bar_id, 0, 0, 0, 0)
        self.canvas.itemconfigure(self.text_id, text="LISTO / READY")
        if self._anim_job: self.after_cancel(self._anim_job)
        self._anim_job = None
    def animate(self):
        if not self.is_running: return
        self.progress -= 0.1
        pct = max(0.0, self.progress / self.duration)
        w = self.winfo_width()
        h = self.winfo_height()
        self.canvas.coords(self.bar_id, 0, 0, w * pct, h)
        self.canvas.coords(self.text_id, w/2, h/2)
        self.canvas.itemconfigure(self.text_id, text=f"ESPERA: {self.progress:.1f}s")
        self.redraw_grip()
        if self.progress > 0:
            self._anim_job = self.after(100, self.animate)
        else:
            self.stop_timer() 
    def on_resize(self):
        if self.bar_id: self.redraw_grip()
class DpsOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y, title="DPS"):
        super().__init__(parent, title, initial_x, initial_y, 250, 160, "#000000")
        self.rows = [] 
    def update_list(self, sorted_data, names_map, start_times):
        self.canvas.delete("content") 
        w = self.winfo_width()
        row_h = 22
        y = 0
        max_dps = 1
        processed = []
        curr_time = time.time()
        for eid, dmg in sorted_data:
            dur = max(1, curr_time - start_times.get(eid, curr_time))
            dps = dmg / dur
            if dps > max_dps: max_dps = dps
            name = names_map.get(str(eid), f"{str(eid)}")
            if name.startswith(".."): name = name[-4:] 
            processed.append((name, dmg, dps))
        for name, dmg, dps in processed:
            if y + row_h > self.winfo_height(): break
            bar_w = (dps / max_dps) * w
            self.canvas.create_rectangle(0, y, bar_w, y+row_h, fill="#444444", outline="", tags="content")
            self.canvas.create_text(5, y + row_h/2, text=f"{name}", anchor="w", fill="white", font=("Segoe UI", 9, "bold"), tags="content")
            dmg_txt = f"{dmg/1000:.1f}k" if dmg > 1000 else f"{dmg}"
            self.canvas.create_text(w-55, y + row_h/2, text=dmg_txt, anchor="e", fill="#ccc", font=("Consolas", 9), tags="content")
            self.canvas.create_text(w-5, y + row_h/2, text=f"{int(dps)}", anchor="e", fill="white", font=("Segoe UI", 9, "bold"), tags="content")
            y += row_h + 1 
    def on_resize(self): pass
class DpsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DETAILS DPS DREADMYST v5.0 (Custom Edition)")
        self.root.geometry("900x680")
        self.root.configure(bg=COLOR_BG)
        self.player_hits = defaultdict(int)
        self.monster_hits = defaultdict(int)
        self.player_heals = defaultdict(int) 
        self.start_times = {}
        self.names_map = self.load_names()
        self.HEAL_TYPE_ID = 0 
        self.settings = self.load_settings()
        self.hp_color = self.settings.get("hp_color", COLOR_PLAYER_DEFAULT)
        self.hp_alpha = self.settings.get("hp_alpha", 0.7)
        self.is_paused = False
        self.my_id = None
        self.player_hp_current = 0
        self.player_hp_max = 1 
        self.player_hp_max = 1 
        self.lang = self.settings.get("lang", "ESP") 
        self.setup_ui()
        self.ov_hp = HealthBarOverlay(self.root, 300, 500, self.hp_color, self.hp_alpha)
        self.ov_cast = CastBarOverlay(self.root, 300, 460) 
        self.ov_timer = CooldownBarOverlay(self.root, 300, 420) 
        self.ov_timer.stop_timer() 
        self.ov_dps = DpsOverlay(self.root, 20, 200, title=self.tr("OV_TITLE_PLAYER"))
        self.ov_dps_m = DpsOverlay(self.root, 20, 380, title=self.tr("OV_TITLE_MONSTER"))
        self.ov_h = DpsOverlay(self.root, 20, 560, title="HEALING") 
        self.ov_dps.withdraw()
        self.ov_dps_m.withdraw()
        self.ov_h.withdraw()
        self.ov_cast.withdraw()
        self.ov_timer.withdraw()
        if is_admin():
            self.root.after(100, self.ask_device_and_start)
        else:
            messagebox.showerror("Error", self.tr("ASK_ADMIN"))
        self.refresh_ui_text()
    def tr(self, key):
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["ESP"]).get(key, key)
    def set_lang(self, target):
        self.lang = target
        self.save_settings() 
        self.refresh_ui_text()
    def refresh_ui_text(self):
        if self.lang == "ESP":
            self.lbl_esp.config(fg="#4CAF50")
            self.lbl_eng.config(fg="#555555")
        else:
            self.lbl_esp.config(fg="#555555")
            self.lbl_eng.config(fg="#4CAF50")
        self.lbl_p.config(text=self.tr("PLAYER_DAMAGE"))
        self.btn_reset_p.config(text=self.tr("RESET_PLAYERS"))
        self.btn_pause.config(text=self.tr("RESUME") if self.is_paused else self.tr("PAUSE"))
        self.chk_hp_w.config(text=self.tr("SHOW_HP"))
        self.chk_dps_mini_w.config(text=self.tr("SHOW_MINI_P"))
        self.chk_dps_m_w.config(text=self.tr("SHOW_MINI_M"))
        self.chk_h_mini_w.config(text=self.tr("SHOW_MINI_H")) 
        self.btn_reset_id.config(text=self.tr("RESET_ID"))
        self.lbl_m.config(text=self.tr("MONSTER_DAMAGE"))
        self.btn_reset_m.config(text=self.tr("RESET_MONSTERS"))
        if "SNIFFER" in self.lbl_status.cget("text"):
             self.lbl_status.config(text=self.tr("STATUS_ACTIVE"))
        else:
             self.lbl_status.config(text=self.tr("STATUS_READY"))
        if not self.my_id:
             self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text=self.tr("HIT_TO_LOCK"))
        self.ov_dps.title(self.tr("OV_TITLE_PLAYER"))
        self.ov_dps_m.title(self.tr("OV_TITLE_MONSTER"))
        self.ov_h.title("HEALING")
        if self.win_sniffer and self.win_sniffer.winfo_exists():
            self.win_sniffer.title(self.tr("DEBUG_TITLE"))
            self.lbl_sniffer_info.config(text=self.tr("DEBUG_INFO"))
    def load_names(self):
        try:
            with open(CONFIG_FILE, 'r') as f: return json.load(f)
        except: return {}
    def save_names(self):
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(self.names_map, f)
        except: pass
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f: return json.load(f)
        except: return {"hp_color": COLOR_PLAYER_DEFAULT, "hp_alpha": 0.7}
    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f: 
                json.dump({
                    "hp_color": self.hp_color, 
                    "hp_alpha": self.hp_alpha,
                    "lang": self.lang
                }, f)
        except: pass
    def ask_color_style(self):
        col = colorchooser.askcolor(title=self.tr("ASK_COLOR"), initialcolor=self.hp_color)
        if not col[1]: return 
        alpha = simpledialog.askfloat(self.tr("ASK_ALPHA"), self.tr("ASK_ALPHA_MSG"), 
                                      minvalue=0.1, maxvalue=1.0, initialvalue=self.hp_alpha)
        if alpha is not None:
            self.hp_color = col[1]
            self.hp_alpha = alpha
            self.save_settings()
            self.ov_hp.update_style(self.hp_color, self.hp_alpha)
    def setup_ui(self):
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)
        self.tab_dps = tk.Frame(self.notebook, bg=COLOR_BG)
        self.tab_dps = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.tab_dps, text="  ⚔️ DASHBOARD  ")
        header_p = tk.Frame(self.tab_dps, bg=COLOR_BG)
        header_p.pack(fill="x", pady=5)
        self.lbl_p = tk.Label(header_p, text=self.tr("PLAYER_DAMAGE"), bg=COLOR_BG, fg=COLOR_PLAYER_DEFAULT, font=FONT_TITLE, anchor="w")
        self.lbl_p.pack(side="left", fill="x", expand=True)
        f_lang = tk.Frame(header_p, bg=COLOR_BG)
        f_lang.pack(side="right")
        self.lbl_esp = tk.Label(f_lang, text="ESP", font=("Segoe UI", 9, "bold"), bg=COLOR_BG, fg="#4CAF50", cursor="hand2")
        self.lbl_esp.pack(side="left")
        self.lbl_esp.bind("<Button-1>", lambda e: self.set_lang("ESP"))
        tk.Label(f_lang, text="|", font=("Segoe UI", 9), bg=COLOR_BG, fg="#555").pack(side="left", padx=5)
        self.lbl_eng = tk.Label(f_lang, text="EN", font=("Segoe UI", 9, "bold"), bg=COLOR_BG, fg="#555", cursor="hand2")
        self.lbl_eng.pack(side="left")
        self.lbl_eng.bind("<Button-1>", lambda e: self.set_lang("ENG"))
        frame_p = tk.Frame(self.tab_dps, bg=COLOR_BG)
        frame_p.pack(fill="both", expand=True, pady=(0, 10))
        self.list_p = tk.Listbox(frame_p, bg=COLOR_LIST_BG, fg="white", font=FONT_MONO, bd=0, selectbackground=COLOR_PLAYER_DEFAULT)
        self.list_p.pack(side="left", fill="both", expand=True)
        self.list_p.bind('<Double-1>', lambda e: self.rename_entry(self.list_p, True))
        scroll_p = tk.Scrollbar(frame_p, orient="vertical", command=self.list_p.yview)
        scroll_p.pack(side="left", fill="y")
        self.list_p.config(yscrollcommand=scroll_p.set)
        btn_frame_p = tk.Frame(frame_p, bg=COLOR_BG, width=150)
        btn_frame_p.pack(side="right", fill="y", padx=(10, 10))
        self.btn_reset_p = tk.Button(btn_frame_p, text=self.tr("RESET_PLAYERS"), command=self.reset_p, bg="#2E7D32", fg="white", font=FONT_TITLE, bd=0)
        self.btn_reset_p.pack(fill="x", pady=2, ipady=5)
        self.btn_pause = tk.Button(btn_frame_p, text=self.tr("PAUSE"), command=self.toggle_pause, bg="#FBC02D", fg="black", font=FONT_TITLE, bd=0)
        self.btn_pause.pack(fill="x", pady=2, ipady=5)
        tk.Frame(btn_frame_p, bg=COLOR_BG, height=20).pack()
        f_ov = tk.Frame(btn_frame_p, bg=COLOR_BG)
        f_ov.pack(fill="x")
        self.chk_hp = tk.BooleanVar(value=True)
        self.chk_hp_w = tk.Checkbutton(f_ov, text=self.tr("SHOW_HP"), variable=self.chk_hp, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w")
        self.chk_hp_w.pack(side="left", fill="x", expand=True)
        f_mini_btns = tk.Frame(f_ov, bg=COLOR_BG)
        f_mini_btns.pack(side="right")
        tk.Button(f_mini_btns, text="🎨", command=self.ask_color_style, bg="#444", fg="white", bd=0, width=3).pack(side="right")
        self.chk_dps_mini = tk.BooleanVar(value=False)
        self.chk_dps_mini_w = tk.Checkbutton(btn_frame_p, text=self.tr("SHOW_MINI_P"), variable=self.chk_dps_mini, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w")
        self.chk_dps_mini_w.pack(fill="x")
        self.chk_dps_m = tk.BooleanVar(value=False)
        self.chk_dps_m_w = tk.Checkbutton(btn_frame_p, text=self.tr("SHOW_MINI_M"), variable=self.chk_dps_m, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w")
        self.chk_dps_m_w.pack(fill="x")
        self.chk_h_mini = tk.BooleanVar(value=False)
        self.chk_h_mini_w = tk.Checkbutton(btn_frame_p, text=self.tr("SHOW_MINI_H"), variable=self.chk_h_mini, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w")
        self.chk_h_mini_w.pack(fill="x")
        self.btn_reset_id = tk.Button(btn_frame_p, text=self.tr("RESET_ID"), command=self.reset_id, bg="#550000", fg="white", bd=0)
        self.btn_reset_id.pack(fill="x", pady=5)
        split_bottom = tk.Frame(self.tab_dps, bg=COLOR_BG)
        split_bottom.pack(fill="both", expand=True, pady=(10, 0))
        frame_left = tk.Frame(split_bottom, bg=COLOR_BG)
        frame_left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.lbl_h = tk.Label(frame_left, text="❤️ HEALING", bg=COLOR_BG, fg="#E91E63", font=FONT_TITLE, anchor="w")
        self.lbl_h.pack(fill="x")
        frame_h_list = tk.Frame(frame_left, bg=COLOR_BG)
        frame_h_list.pack(fill="both", expand=True)
        self.list_h = tk.Listbox(frame_h_list, bg=COLOR_LIST_BG, fg="#F48FB1", font=FONT_MONO, bd=0, selectbackground="#880E4F")
        self.list_h.pack(side="left", fill="both", expand=True)
        self.list_h.bind('<Double-Button-1>', self.on_edit_name_h)
        sb_h = tk.Scrollbar(frame_h_list, orient="vertical", command=self.list_h.yview)
        sb_h.pack(side="right", fill="y")
        self.list_h.config(yscrollcommand=sb_h.set)
        tk.Button(frame_left, text="RST HEAL", command=self.reset_h, bg="#880E4F", fg="white", font=("Consolas", 8, "bold"), bd=0).pack(fill="x", pady=2)
        frame_right = tk.Frame(split_bottom, bg=COLOR_BG)
        frame_right.pack(side="right", fill="both", expand=True, padx=(5, 10))
        self.lbl_m = tk.Label(frame_right, text=self.tr("MONSTER_DAMAGE"), bg=COLOR_BG, fg=COLOR_MONSTER, font=FONT_TITLE, anchor="w")
        self.lbl_m.pack(fill="x")
        frame_m_list = tk.Frame(frame_right, bg=COLOR_BG)
        frame_m_list.pack(fill="both", expand=True)
        self.list_m = tk.Listbox(frame_m_list, bg=COLOR_LIST_BG, fg="white", font=FONT_MONO, bd=0, selectbackground=COLOR_MONSTER)
        self.list_m.pack(side="left", fill="both", expand=True)
        self.list_m.bind('<Double-1>', lambda e: self.rename_entry(self.list_m, False))
        sb_m = tk.Scrollbar(frame_m_list, orient="vertical", command=self.list_m.yview)
        sb_m.pack(side="right", fill="y")
        self.list_m.config(yscrollcommand=sb_m.set)
        self.btn_reset_m = tk.Button(frame_right, text=self.tr("RESET_MONSTERS"), command=self.reset_m, bg="#C62828", fg="white", font=("Consolas", 8, "bold"), bd=0)
        self.btn_reset_m.pack(fill="x", pady=2)
        self.status_frame = tk.Frame(self.root, bg="#222")
        self.status_frame.pack(side="bottom", fill="x")
        self.lbl_status = tk.Label(self.status_frame, text=self.tr("STATUS_READY"), bg="#222", fg="#888", font=("Segoe UI", 8))
        self.lbl_status.pack(side="left", padx=5)
        self.root.after(1000, self.update_dps_loop)
        self.win_sniffer = None
    def toggle_sniffer(self):
        if self.win_sniffer and self.win_sniffer.winfo_exists():
            self.win_sniffer.destroy()
            self.win_sniffer = None
            return
        self.win_sniffer = tk.Toplevel(self.root)
        self.win_sniffer.title(self.tr("DEBUG_TITLE"))
        self.win_sniffer.geometry("600x400")
        self.win_sniffer.configure(bg="black")
        self.lbl_sniffer_info = tk.Label(self.win_sniffer, text=self.tr("DEBUG_INFO"), bg="black", fg="#0f0")
        self.lbl_sniffer_info.pack(fill="x")
        frame = tk.Frame(self.win_sniffer, bg="black")
        frame.pack(fill="both", expand=True)
        self.txt_log = tk.Text(frame, bg="#111", fg="#0f0", font=FONT_MONO)
        self.txt_log.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(frame, command=self.txt_log.yview)
        sb.pack(side="right", fill="y")
        self.txt_log.config(yscrollcommand=sb.set)
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text=self.tr("RESUME") if self.is_paused else self.tr("PAUSE"))
    def toggle_overlays(self):
        if self.chk_hp.get(): self.ov_hp.deiconify()
        else: self.ov_hp.withdraw()
        if self.chk_dps_mini.get(): self.ov_dps.deiconify()
        else: self.ov_dps.withdraw()
        if self.chk_dps_m.get(): self.ov_dps_m.deiconify()
        else: self.ov_dps_m.withdraw()
        if self.chk_h_mini.get(): self.ov_h.deiconify()
        else: self.ov_h.withdraw()
    def reset_p(self):
        self.player_hits.clear()
        self.list_p.delete(0, tk.END)
    def reset_m(self):
        self.monster_hits.clear()
        self.list_m.delete(0, tk.END)
    def reset_h(self):
        self.player_heals.clear()
        self.list_h.delete(0, tk.END)
    def reset_id(self):
        self.my_id = None
        self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text=self.tr("HIT_TO_LOCK"))
    def on_edit_name(self, event):
        selection = self.list_p.curselection()
        if not selection: return
        self._edit_name_logic(self.list_p.get(selection[0]))
    def on_edit_name_h(self, event):
        selection = self.list_h.curselection()
        if not selection: return
        self._edit_name_logic(self.list_h.get(selection[0]))
    def _edit_name_logic(self, item_text):
        if not item_text or "|" not in item_text: return
        full_name = item_text.split("|")[0].strip()
        target_id = None
        for i, n in self.names_map.items():
            if n == full_name:
                target_id = i
                break
        if not target_id:
             if full_name.startswith(".."): target_id = full_name 
             else: target_id = full_name 
        new_name = simpledialog.askstring(self.tr("EDIT_NAME"), f"Nombre para ID {target_id}:", parent=self.root)
        if new_name:
            pass 
            found_id = None
            for eid, name in self.names_map.items():
                if name == full_name:
                    found_id = eid
                    break
            if not found_id:
                 if full_name.isdigit(): found_id = full_name
            if found_id:
                self.names_map[found_id] = new_name
                self.save_names()
                self.title_update() 
            else:
                 messagebox.showinfo("Info", "No se pudo identificar el ID original. Asegúrate de editar nombres ya guardados o IDs completos.")
    def update_dps_loop(self):
        py, my = self.list_p.yview(), self.list_m.yview()
        h = f"{self.tr('COL_NAME'):<20} | {self.tr('COL_DMG'):<10} | {self.tr('COL_DPS'):<10}"
        self.list_p.delete(0, tk.END); self.list_p.insert(tk.END, h); self.list_p.insert(tk.END,"-"*50)
        sorted_p = sorted(self.player_hits.items(), key=lambda x:x[1], reverse=True)
        for eid, dmg in sorted_p:
            dur = max(1, time.time() - self.start_times.get(eid, time.time()))
            nm = self.names_map.get(str(eid), f"..{str(eid)[-4:]}")
            self.list_p.insert(tk.END, f"{nm:<20} | {dmg:<10} | {dmg/dur:<10.1f}")
        self.list_m.delete(0, tk.END); self.list_m.insert(tk.END, h); self.list_m.insert(tk.END,"-"*50)
        for eid, dmg in sorted(self.monster_hits.items(), key=lambda x:x[1], reverse=True):
            dur = max(1, time.time() - self.start_times.get(eid, time.time()))
            nm = self.names_map.get(str(eid), f"..{str(eid)[-4:]}")
            self.list_m.insert(tk.END, f"{nm:<20} | {dmg:<10} | {dmg/dur:<10.1f}")
        self.list_p.yview_moveto(py[0]); self.list_m.yview_moveto(my[0])
        if self.chk_dps_mini.get():
            self.ov_dps.update_list(sorted_p, self.names_map, self.start_times)
        if self.chk_dps_m.get():
            sorted_m = sorted(self.monster_hits.items(), key=lambda x:x[1], reverse=True)
            self.ov_dps_m.update_list(sorted_m, self.names_map, self.start_times)
        ph = self.list_h.yview()
        self.list_h.delete(0, tk.END)
        self.list_h.insert(tk.END, f"{'NOMBRE/ID':<20} | {'HEAL':<10}")
        self.list_h.insert(tk.END, "-"*40)
        sorted_heals = sorted(self.player_heals.items(), key=lambda x:x[1], reverse=True)
        for eid, amount in sorted_heals:
             nm = self.names_map.get(str(eid), f"..{str(eid)[-4:]}")
             self.list_h.insert(tk.END, f"{nm:<20} | {amount:<10}")
        self.list_h.yview_moveto(ph[0])
        if self.chk_h_mini.get():
             self.ov_h.update_list(sorted_heals, self.names_map, self.start_times)
        self.root.after(1000, self.update_dps_loop)
    def parse(self, pl):
        op = pl[0:2].hex()
        if self.win_sniffer and self.win_sniffer.winfo_exists():
            if len(pl) > 2 and op != "8d00": 
                try:
                    raw_hex = pl.hex(" ")
                    tag = ""
                    if op == "6c00": tag = "[DMG]"
                    if op == "6a00": tag = "[HP]"
                    if op == "8800": tag = "[CAST]"
                    msg = f"{tag} [Op: {op}] {raw_hex}"
                    self.txt_log.insert(tk.END, msg + "\n")
                    self.txt_log.see(tk.END)
                except: pass
        def is_player(nid):
            return (1 <= nid <= 999999)
        if op == "6a00" and len(pl) >= 11:
            try:
                eid = struct.unpack('<I', pl[2:6])[0]
                tp = pl[6]
                val = struct.unpack('<i', pl[7:11])[0]
                if self.my_id is None:
                    if tp in [1, 16] and (100000 <= eid <= 999999) and (0 < val < 1000000): 
                         self.my_id = eid
                         log_msg(f"ID AUTO-DETECT (HP Packet): {eid}")
                         self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text=self.tr("SYNC_OK"))
                if self.my_id and eid == self.my_id:
                    if tp == 1: 
                        self.player_hp_current = val
                        if self.player_hp_current > self.player_hp_max: self.player_hp_max = self.player_hp_current
                        self.ov_hp.update_data(val, self.player_hp_max, False)
                    elif tp == 16:
                        self.player_hp_max = val
                        self.ov_hp.update_data(self.player_hp_current, val, False)
            except: pass
        elif op == "6c00" and len(pl) >= 15:
            if self.is_paused: return
            try:
                atk = struct.unpack('<I', pl[2:6])[0]
                vic = struct.unpack('<I', pl[6:10])[0]
                pkt_type = pl[10] # Byte 10 usually indicates Type
                val_signed = struct.unpack('<i', pl[11:15])[0]
                val = abs(val_signed)
                pkt_subtype = pl[15] if len(pl) > 15 else 0 
                if self.win_sniffer and self.win_sniffer.winfo_exists():
                     log_msg(f"[DMG] Type:{pkt_type} SubT:{pkt_subtype} Val:{val} ({val_signed})")
                     log_msg(f"HEX: {pl.hex()}")
                if pkt_type in [3, 34, 6, 250]: 
                    log_msg(f"IGNORED MANA/DRAIN Type {pkt_type} Val {val}")
                    return
                if pkt_subtype == 17:
                    log_msg(f"IGNORED MANA/DRAIN SubType {pkt_subtype} Val {val}")
                    return
                is_healing = (pkt_type == self.HEAL_TYPE_ID)
                if not is_player(vic): is_healing = False 
                if is_healing:
                    if not is_player(atk): return
                    if atk == vic: return
                    self.player_heals[atk] += val
                    if atk not in self.start_times: self.start_times[atk] = time.time()
                else:
                    if atk == vic: return
                    if self.my_id is None:
                        if is_player(atk) and not is_player(vic):
                            self.my_id = atk
                            log_msg(f"ID AUTO-DETECT (Dmg Packet): {atk}")
                            self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text=self.tr("SYNC_OK"))
                    if val > 0:
                        if is_player(atk):
                            self.player_hits[atk] += val
                            if atk not in self.start_times: self.start_times[atk] = time.time()
                        else:
                            self.monster_hits[atk] += val 
            except Exception as e: log_msg(f"Error Parse 6c00: {e}")
        elif op == "8800" and len(pl) >= 6:
            try:
                actor = struct.unpack('<I', pl[2:6])[0]
                if self.my_id and actor != self.my_id and not is_player(actor):
                    self.trigger_cast_alert(actor)
            except: pass
    def trigger_cast_alert(self, actor_id):
        nm = self.names_map.get(str(actor_id), "MONSTER")
        if nm.startswith(".."): nm = "MONSTER"
        if self.chk_cast.get():
            self.ov_cast.start_cast(f"{nm} CASTING!", duration=2.0)
    def ask_device_and_start(self):
        log_msg("DEBUG: ask_device_and_start initiated")
        try:
            self.wpcap = CDLL("wpcap.dll")
        except Exception as e:
            messagebox.showerror("Error", f"Falta wpcap.dll: {e}")
            log_msg(f"DEBUG: Failed to load wpcap.dll: {e}")
            return
        errbuf = create_string_buffer(256)
        alldevs = POINTER(pcap_if)()
        self.wpcap.pcap_findalldevs.argtypes = [POINTER(POINTER(pcap_if)), c_char_p]
        if self.wpcap.pcap_findalldevs(byref(alldevs), errbuf) == -1:
            log_msg(f"DEBUG: Error findalldevs: {errbuf.value}")
            return
        self.pcap_devices = []
        dev = alldevs
        while dev:
            d = dev.contents
            desc = d.description.decode('utf-8', 'ignore') if d.description else "Sin Descripción"
            name = d.name.decode('utf-8', 'ignore') if d.name else "?"
            self.pcap_devices.append((name, desc))
            dev = d.next
        self.wpcap.pcap_freealldevs(alldevs)
        log_msg(f"DEBUG: Found {len(self.pcap_devices)} devices")
        if not self.pcap_devices:
            messagebox.showerror("Error", self.tr("NO_DEVICES"))
            return
        if self.win_sniffer: self.win_sniffer.destroy() 
        self.win_sel = tk.Toplevel(self.root)
        self.win_sel.title(self.tr("WIN_TITLE_SEL"))
        self.win_sel.geometry("500x400")
        tk.Label(self.win_sel, text=self.tr("SELECT_CONN"), font=("Segoe UI", 10, "bold")).pack(pady=10)
        frame_list = tk.Frame(self.win_sel)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)
        sb = tk.Scrollbar(frame_list)
        sb.pack(side="right", fill="y")
        lbox = tk.Listbox(frame_list, width=60, height=10, yscrollcommand=sb.set, font=("Consolas", 10))
        lbox.pack(side="left", fill="both", expand=True)
        sb.config(command=lbox.yview)
        for _, desc in self.pcap_devices:
            lbox.insert(tk.END, desc)
        def confirm():
            sel = lbox.curselection()
            if sel:
                dname = self.pcap_devices[sel[0]][0]
                desc = self.pcap_devices[sel[0]][1]
                log_msg(f"DEBUG: User selected: {desc} ({dname})")
                self.win_sel.destroy()
                threading.Thread(target=self.sniffer_loop, args=(dname,), daemon=True).start()
            else:
                log_msg("DEBUG: Confirm clicked but no selection")
        lbox.bind('<Double-Button-1>', lambda e: confirm())
        tk.Button(self.win_sel, text=self.tr("START_CAP"), command=confirm, bg=COLOR_PLAYER_DEFAULT, fg="white", font=("Segoe UI", 11, "bold")).pack(pady=15, ipadx=20)
    def sniffer_loop(self, dev_name):
        log_msg(f"DEBUG: Starting sniffer loop on {dev_name}")
        errbuf = create_string_buffer(256)
        self.wpcap.pcap_open_live.restype = c_void_p
        self.wpcap.pcap_open_live.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]
        handle = self.wpcap.pcap_open_live(dev_name.encode("utf-8"), 65536, 1, 1000, errbuf)
        if not handle:
            log_msg(f"DEBUG: Error pcap_open_live: {errbuf.value}")
            return
        self.lbl_status.config(text=self.tr("STATUS_ACTIVE"))
        log_msg("DEBUG: Sniffer started successfully. Listening...")
        header = POINTER(pcap_pkthdr)()
        pkt_data = POINTER(c_ubyte)()
        self.wpcap.pcap_next_ex.argtypes = [c_void_p, POINTER(POINTER(pcap_pkthdr)), POINTER(POINTER(c_ubyte))]
        self.wpcap.pcap_next_ex.restype = c_int
        last_log = 0
        while True:
            res = self.wpcap.pcap_next_ex(handle, byref(header), byref(pkt_data))
            if res == 1:
                try:
                    data_ptr = cast(pkt_data, POINTER(c_ubyte * header.contents.caplen)).contents
                    raw = bytes(data_ptr)
                    if len(raw) < 34: continue
                    ip_header = raw[14:]
                    ver_ihl = ip_header[0]
                    ihl = (ver_ihl & 0xF) * 4
                    protocol = ip_header[9]
                    if protocol == 6: 
                        src_ip = socket.inet_ntoa(ip_header[12:16])
                        tcp_packet = ip_header[ihl:]
                        src_port = struct.unpack('!H', tcp_packet[0:2])[0]
                        dst_port = struct.unpack('!H', tcp_packet[2:4])[0]
                        if self.win_sniffer and self.win_sniffer.winfo_exists():
                            ct = time.time()
                            if src_port == 16383 or (ct - last_log > 0.05):
                                last_log = ct
                                tag = "[GAME]" if src_port == 16383 else "[TCP]"
                                msg = f"{tag} {src_ip}:{src_port} -> :{dst_port}\n"
                                try:
                                    self.txt_log.insert(tk.END, msg)
                                    self.txt_log.see(tk.END)
                                except: pass
                        if src_port == 16383:
                            off = (tcp_packet[12] >> 4) * 4
                            payload = tcp_packet[off:]
                            if payload: self.extract_chunks(payload)
                except: pass
    def process_packet(self, raw): pass
    def extract_chunks(self, buf):
        while len(buf) >= 4:
            try:
                sz = struct.unpack('<I', buf[:4])[0]
                if sz > 16000 or sz == 0: 
                    buf = buf[1:]
                    continue
                if len(buf) >= sz + 4:
                    packet_data = buf[4:sz+4]
                    self.parse(packet_data)
                    buf = buf[sz+4:]
                else:
                    break
            except: 
                buf = buf[1:]
                break
if __name__ == "__main__":
    r = tk.Tk()
    a = DpsApp(r)
    r.protocol("WM_DELETE_WINDOW", lambda: (r.destroy(), os._exit(0)))
    r.mainloop()