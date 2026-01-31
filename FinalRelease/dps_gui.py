import socket, threading, struct, time, os, sys, json, ctypes
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, colorchooser
from collections import defaultdict

# --- CONFIGURACIÓN ---

REAL_PORT = 16383
CONFIG_FILE = "dps_names.json"
SETTINGS_FILE = "dps_settings.json"

# Estilos Colors
COLOR_BG = "#1e1e1e"
COLOR_FG = "#ffffff"
COLOR_LIST_BG = "#2d2d2d"
COLOR_PLAYER_DEFAULT = "#4CAF50" 
COLOR_MONSTER = "#F44336"
COLOR_DPS_BAR = "#66BB6A"

FONT_TITLE = ("Segoe UI", 9, "bold")
FONT_MONO = ("Consolas", 9)
FONT_OVERLAY = ("Segoe UI", 9, "bold")

# --- CTYPES STRUCTURES FOR NPCAP ---
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

# --- CLASE BASE REDIMENSIONABLE ---
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

# --- IMPLEMENTACION BARRA VIDA ---
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

# --- IMPLEMENTACION CAST BAR (SEPARADA) ---
class CastBarOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y):
        super().__init__(parent, "CAST", initial_x, initial_y, 250, 30, "#000000")
        self.bar_id = self.canvas.create_rectangle(0, 0, 0, 0, fill="#D32F2F", outline="") # Rojo Casteo
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
        self.progress += 0.05 # 50ms step
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
            self.canvas.coords(self.bar_id, 0, 0, 0, 0) # Clear
            self.canvas.itemconfigure(self.text_id, text="")

    def on_resize(self):
        if self.bar_id: self.redraw_grip()

# --- IMPLEMENTACION DPS DETAILS ---
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

# --- APP PRINCIPAL ---
class DpsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DETAILS DPS DREADMYST v5.0 (Custom Edition)")
        self.root.geometry("850x650")
        self.root.configure(bg=COLOR_BG)
        
        self.player_hits = defaultdict(int)
        self.monster_hits = defaultdict(int)
        self.start_times = {}
        self.names_map = self.load_names()
        
        # Settings
        self.settings = self.load_settings()
        self.hp_color = self.settings.get("hp_color", COLOR_PLAYER_DEFAULT)
        self.hp_alpha = self.settings.get("hp_alpha", 0.7)
        
        self.is_paused = False
        self.my_id = None
        self.player_hp_current = 0
        self.player_hp_max = 1 
        
        self.setup_ui()
        
        # Overlays
        # Overlays
        self.ov_hp = HealthBarOverlay(self.root, 300, 500, self.hp_color, self.hp_alpha)
        self.ov_cast = CastBarOverlay(self.root, 300, 460) # New independent bar
        
        # DPS Overlays
        self.ov_dps = DpsOverlay(self.root, 20, 200, title="Player DMG detail")
        self.ov_dps_m = DpsOverlay(self.root, 20, 380, title="Monster Detail DMG")
        
        self.ov_dps.withdraw()
        self.ov_dps_m.withdraw()
        self.ov_cast.withdraw()

        if is_admin():
            self.root.after(100, self.ask_device_and_start)
        else:
            messagebox.showerror("Error", "Ejecuta como Administrador")

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
                json.dump({"hp_color": self.hp_color, "hp_alpha": self.hp_alpha}, f)
        except: pass

    def ask_color_style(self):
        # 1. Color
        col = colorchooser.askcolor(title="Elige color de Barra HP", initialcolor=self.hp_color)
        if not col[1]: return # Cancelado
        
        # 2. Alpha (Simple Dialog)
        alpha = simpledialog.askfloat("Transparencia", "Nivel de transparencia (0.1 a 1.0):", 
                                      minvalue=0.1, maxvalue=1.0, initialvalue=self.hp_alpha)
        if alpha is not None:
            self.hp_color = col[1]
            self.hp_alpha = alpha
            self.save_settings()
            self.ov_hp.update_style(self.hp_color, self.hp_alpha)

    def setup_ui(self):
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        lbl_p = tk.Label(main, text="PLAYER DAMAGE", bg=COLOR_BG, fg=COLOR_PLAYER_DEFAULT, font=FONT_TITLE, anchor="w")
        lbl_p.pack(fill="x")
        
        frame_p = tk.Frame(main, bg=COLOR_BG)
        frame_p.pack(fill="both", expand=True, pady=(0, 10))
        
        self.list_p = tk.Listbox(frame_p, bg=COLOR_LIST_BG, fg="white", font=FONT_MONO, bd=0, selectbackground=COLOR_PLAYER_DEFAULT)
        self.list_p.pack(side="left", fill="both", expand=True)
        self.list_p.bind('<Double-1>', lambda e: self.rename_entry(self.list_p, True))
        
        scroll_p = tk.Scrollbar(frame_p, orient="vertical", command=self.list_p.yview)
        scroll_p.pack(side="left", fill="y")
        self.list_p.config(yscrollcommand=scroll_p.set)
        
        btn_frame_p = tk.Frame(frame_p, bg=COLOR_BG, width=150)
        btn_frame_p.pack(side="right", fill="y", padx=(10, 0))
        btn_frame_p.pack_propagate(False)
        
        tk.Button(btn_frame_p, text="RESET PLAYERS", command=self.reset_p, bg="#2E7D32", fg="white", font=FONT_TITLE, bd=0).pack(fill="x", pady=2, ipady=5)
        self.btn_pause = tk.Button(btn_frame_p, text="PAUSE", command=self.toggle_pause, bg="#FBC02D", fg="black", font=FONT_TITLE, bd=0)
        self.btn_pause.pack(fill="x", pady=2, ipady=5)
        
        tk.Frame(btn_frame_p, bg=COLOR_BG, height=20).pack()
        
        # Checkboxes Overlays
        f_ov = tk.Frame(btn_frame_p, bg=COLOR_BG)
        f_ov.pack(fill="x")
        
        self.chk_hp = tk.BooleanVar(value=True)
        tk.Checkbutton(f_ov, text="Ver Barra HP", variable=self.chk_hp, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w").pack(side="left", fill="x", expand=True)
        
        # Boton Config Estilo (Paleta) y Sniffer
        tk.Button(f_ov, text="🎨", command=self.ask_color_style, bg="#444", fg="white", bd=0, width=3).pack(side="right")
        
        self.chk_dps_mini = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame_p, text="Ver Mini DPS (Jugador)", variable=self.chk_dps_mini, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w").pack(fill="x")
        
        self.chk_dps_m = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame_p, text="Ver Mini DPS (Monstruo)", variable=self.chk_dps_m, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w").pack(fill="x")
        
        tk.Button(btn_frame_p, text="RESET ID", command=self.reset_id, bg="#550000", fg="white", bd=0).pack(fill="x", pady=5)
        
        lbl_m = tk.Label(main, text="MONSTER DAMAGE", bg=COLOR_BG, fg=COLOR_MONSTER, font=FONT_TITLE, anchor="w")
        lbl_m.pack(fill="x")
        
        frame_m = tk.Frame(main, bg=COLOR_BG)
        frame_m.pack(fill="both", expand=True)
        
        self.list_m = tk.Listbox(frame_m, bg=COLOR_LIST_BG, fg="white", font=FONT_MONO, bd=0, selectbackground=COLOR_MONSTER)
        self.list_m.pack(side="left", fill="both", expand=True)
        self.list_m.bind('<Double-1>', lambda e: self.rename_entry(self.list_m, False))
        
        scroll_m = tk.Scrollbar(frame_m, orient="vertical", command=self.list_m.yview)
        scroll_m.pack(side="left", fill="y")
        self.list_m.config(yscrollcommand=scroll_m.set)
        
        btn_frame_m = tk.Frame(frame_m, bg=COLOR_BG, width=150)
        btn_frame_m.pack(side="right", fill="y", padx=(10, 0))
        btn_frame_m.pack_propagate(False)
        tk.Button(btn_frame_m, text="RESET MONSTERS", command=self.reset_m, bg="#C62828", fg="white", font=FONT_TITLE, bd=0).pack(fill="x", pady=2, ipady=5)

        self.lbl_status = tk.Label(self.root, text="Status: Ready", bg="black", fg="#4CAF50", anchor="w")
        self.lbl_status.pack(side="bottom", fill="x")
        
        self.root.after(1000, self.update_dps_loop)
        
        self.win_sniffer = None

    def toggle_sniffer(self):
        if self.win_sniffer and self.win_sniffer.winfo_exists():
            self.win_sniffer.destroy()
            self.win_sniffer = None
            return

        self.win_sniffer = tk.Toplevel(self.root)
        self.win_sniffer.title("Packet Sniffer - DEBUG")
        self.win_sniffer.geometry("600x400")
        self.win_sniffer.configure(bg="black")
        
        tk.Label(self.win_sniffer, text="Capturando paquetes desconocidos... (Usa esto para ver Casts)", bg="black", fg="#0f0").pack(fill="x")
        
        frame = tk.Frame(self.win_sniffer, bg="black")
        frame.pack(fill="both", expand=True)
        
        self.txt_log = tk.Text(frame, bg="#111", fg="#0f0", font=FONT_MONO)
        self.txt_log.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(frame, command=self.txt_log.yview)
        sb.pack(side="right", fill="y")
        self.txt_log.config(yscrollcommand=sb.set)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="RESUME" if self.is_paused else "PAUSE")

    def toggle_overlays(self):
        if self.chk_hp.get(): self.ov_hp.deiconify()
        else: self.ov_hp.withdraw()
        
        if self.chk_dps_mini.get(): self.ov_dps.deiconify()
        else: self.ov_dps.withdraw()
        
        if self.chk_dps_m.get(): self.ov_dps_m.deiconify()
        else: self.ov_dps_m.withdraw()

    def reset_p(self):
        self.player_hits.clear()
        self.list_p.delete(0, tk.END)

    def reset_m(self):
        self.monster_hits.clear()
        self.list_m.delete(0, tk.END)

    def reset_id(self):
        self.my_id = None
        self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text="GOLPEA PARA BLOQUEAR...")

    def rename_entry(self, listbox, is_player):
        sel = listbox.curselection()
        if not sel: return
        line = listbox.get(sel[0])
        if line.startswith("NOMBRE"): return
        name_display = line.split('|')[0].strip()
        
        tid = None
        for rid, n in self.names_map.items():
            if n == name_display: tid = int(rid); break
        
        if not tid:
            d = self.player_hits if is_player else self.monster_hits
            for k in d:
                if self.names_map.get(str(k), f"..{str(k)[-4:]}") == name_display: tid = k; break
        
        if tid:
            new = simpledialog.askstring("Rename", "New Name:", parent=self.root)
            if new:
                self.names_map[str(tid)] = new
                self.save_names()

    def update_dps_loop(self):
        py, my = self.list_p.yview(), self.list_m.yview()
        h = f"{'NOMBRE/ID':<20} | {'DAÑO':<10} | {'DPS':<10}"
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
            
        self.root.after(1000, self.update_dps_loop)



    def parse(self, pl):
        op = pl[0:2].hex()
        
        # LOGGING PARA SNIFFER (Solo si la ventana está abierta)
        if self.win_sniffer and self.win_sniffer.winfo_exists():
            if len(pl) > 2 and op != "8d00": # Ignorar Spam 8d00
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

        # Helpers ID
        def is_player(nid):
            # STRICT 6 DIGITS ONLY (As requested by User)
            # Rango: 100,000 a 999,999
            return (1 <= nid <= 999999)

        # [HP / STATS UPDATE]
        if op == "6a00" and len(pl) >= 11:
            try:
                eid = struct.unpack('<I', pl[2:6])[0]
                tp = pl[6]
                val = struct.unpack('<i', pl[7:11])[0]
                
                # Auto-Detect ID from Stats (More reliable than combat)
                if self.my_id is None:
                    # Assign ID if it looks like a valid HP update (Strict 6 digits)
                    if tp in [1, 16] and (100000 <= eid <= 999999) and (0 < val < 1000000): 
                         self.my_id = eid
                         log_msg(f"ID AUTO-DETECT (HP Packet): {eid}")
                         self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text="SINCRO OK")

                if self.my_id and eid == self.my_id:
                    if tp == 1: 
                        self.player_hp_current = val
                        if self.player_hp_current > self.player_hp_max: self.player_hp_max = self.player_hp_current
                        self.ov_hp.update_data(val, self.player_hp_max, False)
                    elif tp == 16:
                        self.player_hp_max = val
                        self.ov_hp.update_data(self.player_hp_current, val, False)
            except: pass
            
        # [DAMAGE PACKET]
        elif op == "6c00" and len(pl) >= 15:
            if self.is_paused: return
            try:
                atk = struct.unpack('<I', pl[2:6])[0]
                vic = struct.unpack('<I', pl[6:10])[0]
                val = abs(struct.unpack('<i', pl[11:15])[0])
                
                # Debug Log for IDs
                if self.win_sniffer and self.win_sniffer.winfo_exists():
                     log_msg(f"[DMG] Atk:{atk} Vic:{vic} Dmg:{val}")

                # Auto-Detect ID from Combat (Fallback)
                if self.my_id is None:
                    if is_player(atk) and not is_player(vic):
                        self.my_id = atk
                        log_msg(f"ID AUTO-DETECT (Dmg Packet): {atk}")
                        self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text="SINCRO OK")

                if val > 0:
                    if is_player(atk):
                        self.player_hits[atk] += val
                        if atk not in self.start_times: self.start_times[atk] = time.time()
                    else:
                        self.monster_hits[atk] += val 
            except Exception as e: log_msg(f"Error Parse 6c00: {e}")

        # MONSTER CAST DETECTION
        elif op == "8800" and len(pl) >= 6:
            try:
                actor = struct.unpack('<I', pl[2:6])[0]
                # Si alguien castea y NO soy yo, y NO es un jugador (presumiblemente)
                if self.my_id and actor != self.my_id and not is_player(actor):
                    self.trigger_cast_alert(actor)
            except: pass
            


    def trigger_cast_alert(self, actor_id):
        nm = self.names_map.get(str(actor_id), "MONSTER")
        if nm.startswith(".."): nm = "MONSTER"
        
        # Alerta Visual en Label de Monstruos
        # orig_bg = self.list_m.cget("bg")
        # self.list_m.config(bg="#aa0000") # Flash Rojo NO MORE
        # self.root.after(500, lambda: self.list_m.config(bg=orig_bg))
        
        # Alerta en Overlay Independiente
        if self.chk_cast.get():
            self.ov_cast.start_cast(f"{nm} CASTING!", duration=2.0)

    # --- PCAP ENGINE (THREAD-SAFE UI) ---
    def ask_device_and_start(self):
        log_msg("DEBUG: ask_device_and_start initiated")
        # 1. Cargar wpcap
        try:
            self.wpcap = CDLL("wpcap.dll")
        except Exception as e:
            messagebox.showerror("Error", f"Falta wpcap.dll: {e}")
            log_msg(f"DEBUG: Failed to load wpcap.dll: {e}")
            return

        # 2. Listar
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
            messagebox.showerror("Error", "No Network Devices found.")
            return

        # 3. Ventana Selección (MAIN THREAD)
        if self.win_sniffer: self.win_sniffer.destroy() # Close old debug if open
        
        self.win_sel = tk.Toplevel(self.root)
        self.win_sel.title("Elige tu Tarjeta de Red")
        self.win_sel.geometry("500x400")
        
        tk.Label(self.win_sel, text="Selecciona tu conexión de Internet:", font=("Segoe UI", 10, "bold")).pack(pady=10)
        
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
                # START THREAD
                threading.Thread(target=self.sniffer_loop, args=(dname,), daemon=True).start()
            else:
                log_msg("DEBUG: Confirm clicked but no selection")
        
        lbox.bind('<Double-Button-1>', lambda e: confirm())
        tk.Button(self.win_sel, text="INICIAR CAPTURA", command=confirm, bg=COLOR_PLAYER_DEFAULT, fg="white", font=("Segoe UI", 11, "bold")).pack(pady=15, ipadx=20)

    def sniffer_loop(self, dev_name):
        log_msg(f"DEBUG: Starting sniffer loop on {dev_name}")
        errbuf = create_string_buffer(256)
        
        # Define types for pcap_open_live BEFORE calling it
        self.wpcap.pcap_open_live.restype = c_void_p
        self.wpcap.pcap_open_live.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]

        # Open
        handle = self.wpcap.pcap_open_live(dev_name.encode("utf-8"), 65536, 1, 1000, errbuf)
        
        if not handle:
            log_msg(f"DEBUG: Error pcap_open_live: {errbuf.value}")
            return
            
        # Filter REMOVED for Debugging
        # fp = bpf_program()
        # filter_exp = b"tcp port 16383"
        
        self.lbl_status.config(text="Status: SNIFFER ACTIVO (Espiando...)")
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
                    
                    if protocol == 6: # TCP
                        src_ip = socket.inet_ntoa(ip_header[12:16])
                        tcp_packet = ip_header[ihl:]
                        src_port = struct.unpack('!H', tcp_packet[0:2])[0]
                        dst_port = struct.unpack('!H', tcp_packet[2:4])[0]
                        
                        # DEBUG VISUAL
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

                        # LOGIC
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
