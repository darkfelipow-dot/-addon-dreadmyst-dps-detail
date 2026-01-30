import socket, threading, struct, time, os, sys, json, ctypes
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, colorchooser
from collections import defaultdict

# --- CONFIGURACIÓN ---
REAL_HOSTNAME = "game.dreadmyst.com"
REAL_PORT = 16383
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
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

# --- IMPLEMENTACION DPS DETAILS ---
class DpsOverlay(ResizableWindow):
    def __init__(self, parent, initial_x, initial_y):
        super().__init__(parent, "DPS", initial_x, initial_y, 250, 160, "#000000")
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
        self.ov_hp = HealthBarOverlay(self.root, 300, 500, self.hp_color, self.hp_alpha)
        self.ov_dps = DpsOverlay(self.root, 20, 200)
        self.ov_dps.withdraw() 
        
        if is_admin():
            threading.Thread(target=self.proxy_init, daemon=True).start()
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
        
        # Boton Config Estilo (Paleta)
        tk.Button(f_ov, text="🎨", command=self.ask_color_style, bg="#444", fg="white", bd=0, width=3).pack(side="right")
        
        self.chk_dps_mini = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame_p, text="Ver Mini DPS", variable=self.chk_dps_mini, command=self.toggle_overlays, bg=COLOR_BG, fg="white", selectcolor="#333", anchor="w").pack(fill="x")
        
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

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="RESUME" if self.is_paused else "PAUSE")

    def toggle_overlays(self):
        if self.chk_hp.get(): self.ov_hp.deiconify()
        else: self.ov_hp.withdraw()
        
        if self.chk_dps_mini.get(): self.ov_dps.deiconify()
        else: self.ov_dps.withdraw()

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
        self.root.after(1000, self.update_dps_loop)

    def proxy_init(self):
        self.lbl_status.config(text="Status: Conectando...")
        real_ip = self.find_ip()
        if not real_ip: return
        try:
            self.set_hosts(True)
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('127.0.0.1', REAL_PORT))
            srv.listen(5)
            self.lbl_status.config(text="Status: LISTO - Entra al juego")
            while True:
                c, _ = srv.accept()
                r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    r.connect((real_ip, REAL_PORT))
                    threading.Thread(target=self.pipe, args=(c,r,True)).start()
                    threading.Thread(target=self.pipe, args=(r,c,False)).start()
                except: c.close()
        except: pass
        finally: self.set_hosts(False)

    def pipe(self, s, d, to_srv):
        buf = b""
        while True:
            try:
                data = s.recv(8192)
                if not data: break
                if not to_srv:
                    buf += data
                    while len(buf) >= 4:
                        try:
                            sz = struct.unpack('<I', buf[:4])[0]
                            if sz > 16000 or sz == 0: buf=buf[1:]; continue
                            if len(buf) >= sz+4: self.parse(buf[4:sz+4]); buf=buf[sz+4:]
                            else: break
                        except: buf=buf[1:]
                d.sendall(data)
            except: break

    def parse(self, pl):
        op = pl[0:2].hex()
        if op == "6a00" and len(pl) >= 11:
            try:
                eid = struct.unpack('<I', pl[2:6])[0]
                tp = pl[6]
                val = struct.unpack('<i', pl[7:11])[0]
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
                val = abs(struct.unpack('<i', pl[11:15])[0])
                if self.my_id is None and atk < 1000000 and vic > 1000000:
                    self.my_id = atk
                    self.ov_hp.canvas.itemconfigure(self.ov_hp.text_id, text="SINCRO OK")
                if val > 0:
                    if atk < 1000000:
                        self.player_hits[atk] += val
                        if atk not in self.start_times: self.start_times[atk] = time.time()
                    else:
                        self.monster_hits[atk] += val 
            except: pass

    def find_ip(self):
        self.set_hosts(False); time.sleep(0.5)
        l = ["185.43.108.17", "64.176.6.148"]
        try: 
            hh = socket.gethostbyname(REAL_HOSTNAME)
            if "127." not in hh: l.insert(0, hh)
        except: pass
        for ip in l:
            try: 
                s=socket.socket(); s.settimeout(1)
                if s.connect_ex((ip, REAL_PORT))==0: s.close(); return ip
            except: pass
        return None

    def set_hosts(self, e):
        try:
            if os.path.exists(HOSTS_PATH): os.chmod(HOSTS_PATH, 0o777)
            if not os.path.exists(HOSTS_PATH): open(HOSTS_PATH,'w').close()
            with open(HOSTS_PATH,'r') as f: ll = f.readlines()
            o = [l for l in ll if REAL_HOSTNAME not in l]
            if e: o.append(f"\n127.0.0.1 {REAL_HOSTNAME}\n")
            with open(HOSTS_PATH,'w') as f: f.writelines(o)
            os.system("ipconfig /flushdns")
            return True
        except: return False

if __name__ == "__main__":
    r = tk.Tk()
    a = DpsApp(r)
    r.protocol("WM_DELETE_WINDOW", lambda: (a.set_hosts(False), r.destroy(), os._exit(0)))
    r.mainloop()
