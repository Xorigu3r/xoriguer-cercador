"""Xoriguer Cercador — cerca fitxers per tipus en un disc i els copia a una carpeta (un altre disc o un pendrive).

Executa:  python app.py      ·  Compila:  compilar.bat  (dist/XoriguerCercador.exe)
"""
import ctypes
import json
import os
import shutil
import string
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import marca_tk as MT
from traduccions import IDIOMES, NOMS_IDIOMES, T

VERSIO = "1.0"

# ── Paleta «Blau pissarra» ─────────────────────────────────────────────
FONS = "#1E2A3B"
TARGETA = "#27354A"
FONS3 = "#31405A"
LINIA = "#41506A"
SUAU = "#B9B2A5"
CREMA = "#F6EFE2"
TARONJA = "#FFA82E"
TARONJA2 = "#F2650F"

# ── Tipus de fitxer ───────────────────────────────────────────────────
CATEGORIES = {
    "Imatges": "jpg jpeg jfif png gif bmp tif tiff webp heic heif avif psd svg "
               "raw dng cr2 cr3 nef nrw arw srf sr2 orf rw2 raf pef srw",
    "Vídeos": "mp4 m4v mov avi mkv wmv flv webm mpg mpeg mpe 3gp 3g2 mts m2ts ts vob mod tod divx asf",
    "Música": "mp3 wav flac aac m4a ogg oga opus wma aif aiff alac ape mid midi amr",
    "Documents": "pdf doc docx docm odt rtf txt xls xlsx xlsm ods csv ppt pptx pps ppsx odp epub mobi pages numbers key",
    "Comprimits": "zip rar 7z tar gz tgz bz2 xz zst iso cab",
}
CATEGORIES = {k: set(v.split()) for k, v in CATEGORIES.items()}
ICONES = {"Imatges": "🖼", "Vídeos": "🎬", "Música": "🎵", "Documents": "📄", "Comprimits": "🗜", "Altres": "➕"}

CARPETES_SISTEMA = {
    "windows", "program files", "program files (x86)", "programdata", "$recycle.bin", "recycler",
    "system volume information", "appdata", "$windows.~bt", "$windows.~ws", "$winreagent", "$sysreset",
    "recovery", "msocache", "perflogs", "config.msi", "windows.old", "intel", "amd", "nvidia",
    "node_modules", ".git", "__pycache__", ".cache", ".gradle", ".m2", ".nuget", ".vscode", "site-packages",
}
IMATGE_PETITA = 30 * 1024
MIDA_FAT32 = 4 * 1024 ** 3 - 1


def base_recursos():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def fitxer_ajustos():
    d = Path(os.environ.get("APPDATA", Path.home())) / "Xoriguer Cercador"
    d.mkdir(parents=True, exist_ok=True)
    return d / "ajustos.json"


def idioma_sistema():
    try:
        buf = ctypes.create_unicode_buffer(85)
        ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
        codi = buf.value[:2].lower()
    except Exception:
        codi = "en"
    return codi if codi in IDIOMES else "en"


def camí_llarg(p):
    """Prefix \\\\?\\ per a camins de més de 260 caràcters a Windows."""
    p = os.path.abspath(p)
    if len(p) < 240 or p.startswith("\\\\?\\"):
        return p
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def info_volum(arrel):
    """(etiqueta, sistema de fitxers) d'una unitat."""
    nom = ctypes.create_unicode_buffer(261)
    fs = ctypes.create_unicode_buffer(261)
    try:
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(arrel), nom, 261, None, None, None, fs, 261)
        if ok:
            return nom.value, fs.value
    except Exception:
        pass
    return "", ""


def unitats():
    """Llista de (arrel, tipus, etiqueta) de les unitats disponibles."""
    res = []
    try:
        mask = ctypes.windll.kernel32.GetLogicalDrives()
    except Exception:
        return res
    for i, lletra in enumerate(string.ascii_uppercase):
        if not mask & (1 << i):
            continue
        arrel = f"{lletra}:\\"
        tipus = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(arrel))
        if tipus not in (2, 3, 4):        # 2 extraïble, 3 local, 4 xarxa (sense CD buits)
            continue
        etiqueta, _ = info_volum(arrel)
        res.append((arrel, {2: "Extraïble", 3: "Disc local", 4: "Xarxa"}[tipus], etiqueta))
    return res


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.ajustos = self._llegeix_ajustos()
        self.idioma = self.ajustos.get("idioma", "ca")
        self.title("Xoriguer Cercador")
        self.configure(bg=FONS)
        self.escala = max(1.0, self.winfo_fpixels("1i") / 96)
        amp = min(self.px(880), self.winfo_screenwidth() - 40)
        alt = min(self.px(840), self.winfo_screenheight() - 90)
        self.geometry(f"{amp}x{alt}+{(self.winfo_screenwidth() - amp) // 2}+20")
        self.minsize(min(self.px(720), amp), min(self.px(600), alt))
        try:
            self.iconbitmap(default=str(base_recursos() / "assets" / "icona.ico"))
        except Exception:
            pass
        self._imatges = []

        # Estat (sobreviu als canvis d'idioma)
        cats = self.ajustos.get("cats", ["Imatges", "Vídeos"])
        self.v_cat = {c: tk.BooleanVar(value=c in cats) for c in ICONES}
        self.v_altres = tk.StringVar(value=self.ajustos.get("altres", ""))
        self.v_sistema = tk.BooleanVar(value=self.ajustos.get("sistema", True))
        self.v_petites = tk.BooleanVar(value=self.ajustos.get("petites", True))
        self.v_origen = tk.StringVar()
        self.v_desti = tk.StringVar(value=self.ajustos.get("desti", ""))
        self.v_carpetes = tk.BooleanVar(value=self.ajustos.get("carpetes", True))
        self.v_duplicats = tk.BooleanVar(value=self.ajustos.get("duplicats", True))
        self.v_estat = tk.StringVar()
        self.origens = {}          # text del desplegable → camí
        self.origen_cercat = None  # camí de la darrera cerca
        self.resultats = {}        # categoria → {ext: [(camí, mida), ...]}
        self.marcats = {}          # categoria → bool (a la llista de resultats)
        self.treballant = False
        self.atura = threading.Event()
        self.ultima_desti = None

        self._estils()
        self.construeix()
        self.v_estat.set(self.t("Tria on vols buscar i què vols trobar."))
        self.protocol("WM_DELETE_WINDOW", self.surt)

    def px(self, n):
        return int(n * self.escala)

    # ── Idioma ──────────────────────────────────────────────────────────
    def t(self, text, **kw):
        idi = self.idioma or idioma_sistema()
        if idi != "ca" and text in T:
            text = T[text][IDIOMES.index(idi) - 1]
        return text.format(**kw) if kw else text

    def num(self, x, dec=1):
        s = f"{x:,.{dec}f}" if dec else f"{x:,}"
        if (self.idioma or idioma_sistema()) != "en":
            s = s.replace(",", " ").replace(".", ",")
        return s

    def mida(self, b):
        for u in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{self.num(b, 0 if u == 'B' else 1)} {u}"
            b /= 1024
        return f"{self.num(b, 2)} TB"

    @staticmethod
    def durada(s):
        s = int(s)
        if s < 60:
            return f"{s} s"
        if s < 3600:
            return f"{s // 60} min {s % 60} s"
        return f"{s // 3600} h {s % 3600 // 60} min"

    # ── Ajustos ─────────────────────────────────────────────────────────
    def _llegeix_ajustos(self):
        try:
            return json.loads(fitxer_ajustos().read_text(encoding="utf-8"))
        except Exception:
            return {}

    def desa_ajustos(self):
        a = {
            "idioma": self.idioma,
            "cats": [c for c, v in self.v_cat.items() if v.get()],
            "altres": self.v_altres.get(),
            "sistema": self.v_sistema.get(),
            "petites": self.v_petites.get(),
            "desti": self.v_desti.get(),
            "carpetes": self.v_carpetes.get(),
            "duplicats": self.v_duplicats.get(),
            "origen": self.origens.get(self.v_origen.get(), self.v_origen.get()),
        }
        try:
            fitxer_ajustos().write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def surt(self):
        self.atura.set()
        self.desa_ajustos()
        self.destroy()

    # ── Interfície ──────────────────────────────────────────────────────
    def _estils(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=TARGETA, foreground=CREMA, font=(MT.TEXT, 10))
        s.configure("TCheckbutton", background=TARGETA, foreground=CREMA, font=(MT.TEXT, 10),
                    indicatorbackground=FONS3, indicatorforeground=TARONJA)
        s.map("TCheckbutton", background=[("active", TARGETA)],
              indicatorbackground=[("selected", FONS3), ("active", LINIA)])
        s.configure("Gran.TCheckbutton", font=(MT.TEXT, 11))
        s.configure("TRadiobutton", background=TARGETA, foreground=CREMA,
                    indicatorbackground=FONS3, indicatorforeground=TARONJA)
        s.map("TRadiobutton", background=[("active", TARGETA)])
        s.configure("TCombobox", fieldbackground=FONS3, background=FONS3, foreground=CREMA,
                    arrowcolor=TARONJA, bordercolor=LINIA, lightcolor=FONS3, darkcolor=FONS3,
                    selectbackground=FONS3, selectforeground=CREMA, padding=5)
        s.map("TCombobox", fieldbackground=[("readonly", FONS3)], foreground=[("readonly", CREMA)],
              selectbackground=[("readonly", FONS3)], selectforeground=[("readonly", CREMA)])
        self.option_add("*TCombobox*Listbox.background", FONS3)
        self.option_add("*TCombobox*Listbox.foreground", CREMA)
        self.option_add("*TCombobox*Listbox.selectBackground", TARONJA2)
        self.option_add("*TCombobox*Listbox.font", (MT.TEXT, 10))
        s.configure("TEntry", fieldbackground=FONS3, foreground=CREMA, insertcolor=CREMA,
                    bordercolor=LINIA, lightcolor=FONS3, darkcolor=FONS3, padding=5)
        s.configure("Treeview", background=FONS3, fieldbackground=FONS3, foreground=CREMA,
                    bordercolor=LINIA, rowheight=self.px(26), font=(MT.TEXT, 10))
        s.map("Treeview", background=[("selected", LINIA)], foreground=[("selected", CREMA)])
        s.configure("Treeview.Heading", background=TARGETA, foreground=SUAU, relief="flat",
                    font=(MT.TEXT, 9, "bold"), bordercolor=LINIA)
        s.map("Treeview.Heading", background=[("active", FONS3)])
        s.configure("Horizontal.TProgressbar", troughcolor=FONS3, background=TARONJA,
                    bordercolor=LINIA, lightcolor=TARONJA, darkcolor=TARONJA2, thickness=self.px(14))
        s.configure("Vertical.TScrollbar", background=LINIA, troughcolor=FONS3, bordercolor=FONS3,
                    arrowcolor=SUAU, lightcolor=LINIA, darkcolor=LINIA)

    def boto(self, pare, text, ordre, principal=True):
        b = tk.Button(pare, text=text, command=ordre, relief="flat", bd=0, cursor="hand2",
                      font=(MT.TEXT, 11 if principal else 10, "bold"), padx=18, pady=7 if principal else 4,
                      bg=TARONJA2 if principal else FONS3, fg=CREMA,
                      activebackground=TARONJA if principal else LINIA, activeforeground=FONS,
                      disabledforeground=SUAU)
        return b

    def targeta(self, titol, **pack):
        f = tk.Frame(self.cos, bg=TARGETA, highlightbackground=LINIA, highlightthickness=1, padx=16, pady=12)
        f.pack(fill="x", pady=(0, 10), **pack)
        tk.Label(f, text=titol, bg=TARGETA, fg=TARONJA, font=(MT.TITOL, 13)).pack(anchor="w", pady=(0, 8))
        return f

    def construeix(self):
        for w in self.winfo_children():
            w.destroy()

        # Capçalera
        cap = tk.Frame(self, bg=FONS, padx=20, pady=14)
        cap.pack(fill="x")
        try:
            im = tk.PhotoImage(file=str(base_recursos() / "assets" / "rotul.png"))
            self._imatges.append(im)
            tk.Label(cap, image=im, bg=FONS).pack(side="left")
        except Exception:
            tk.Label(cap, text="XORIGUER  CERCADOR", bg=FONS, fg=CREMA, font=(MT.TITOL, 18)).pack(side="left")
        noms = [self.t("Sistema") if k == "" else v for k, v in NOMS_IDIOMES.items()]
        cb = ttk.Combobox(cap, values=noms, state="readonly", width=10)
        cb.current(list(NOMS_IDIOMES).index(self.idioma))
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda e: self.canvia_idioma(list(NOMS_IDIOMES)[cb.current()]))
        tk.Label(cap, text=self.t("Idioma"), bg=FONS, fg=SUAU, font=(MT.TEXT, 9)).pack(side="right", padx=6)

        self.cos = tk.Frame(self, bg=FONS, padx=20)
        self.cos.pack(fill="both", expand=True)

        # 1. Origen
        f = self.targeta(self.t("1. On busco?"))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x")
        self.cb_origen = ttk.Combobox(fila, textvariable=self.v_origen, state="readonly", font=(MT.TEXT, 10))
        self.cb_origen.pack(side="left", fill="x", expand=True)
        self.boto(fila, self.t("Carpeta…"), self.tria_origen, False).pack(side="left", padx=(8, 0))
        self.omple_origens(self.ajustos.get("origen"))

        # 2. Tipus
        f = self.targeta(self.t("2. Què busco?"))
        graella = tk.Frame(f, bg=TARGETA)
        graella.pack(fill="x")
        for i, c in enumerate(ICONES):
            ttk.Checkbutton(graella, text=f"{ICONES[c]}  {self.t(c)}", variable=self.v_cat[c],
                            style="Gran.TCheckbutton").grid(row=0, column=i, sticky="w", padx=(0, 18))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(8, 0))
        tk.Label(fila, text=self.t("Altres extensions (p. ex. dwg, gpx):"), bg=TARGETA, fg=SUAU,
                 font=(MT.TEXT, 9)).pack(side="left")
        e = ttk.Entry(fila, textvariable=self.v_altres, width=30)
        e.pack(side="left", padx=8, fill="x", expand=True)
        e.bind("<KeyRelease>", lambda ev: self.v_cat["Altres"].set(bool(self.v_altres.get().strip())))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(fila, text=self.t("Omet carpetes del sistema i programes"),
                        variable=self.v_sistema).pack(side="left")
        ttk.Checkbutton(fila, text=self.t("Omet imatges petites (icones, < 30 KB)"),
                        variable=self.v_petites).pack(side="left", padx=(18, 0))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(10, 0))
        self.b_cerca = self.boto(fila, "🔍  " + self.t("Cerca"), self.cerca)
        self.b_cerca.pack(side="left")
        self.b_atura = self.boto(fila, self.t("Atura"), self.atura.set, False)

        # 3. Destinació
        f = self.targeta(self.t("3. On ho copio?"), side="bottom")
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x")
        ttk.Entry(fila, textvariable=self.v_desti).pack(side="left", fill="x", expand=True)
        self.boto(fila, self.t("Tria"), self.tria_desti, False).pack(side="left", padx=(8, 0))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(8, 0))
        tk.Label(fila, text=self.t("Organització:"), bg=TARGETA, fg=SUAU, font=(MT.TEXT, 9)).pack(side="left")
        ttk.Radiobutton(fila, text=self.t("Per tipus, mantenint les carpetes"), variable=self.v_carpetes,
                        value=True).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(fila, text=self.t("Per tipus, tot junt"), variable=self.v_carpetes,
                        value=False).pack(side="left", padx=(12, 0))
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(fila, text=self.t("Omet duplicats (mateix nom i mida)"),
                        variable=self.v_duplicats).pack(side="left")
        fila = tk.Frame(f, bg=TARGETA)
        fila.pack(fill="x", pady=(10, 0))
        self.b_copia = self.boto(fila, "📥  " + self.t("Copia"), self.copia)
        self.b_copia.pack(side="left")
        self.b_obre = self.boto(fila, self.t("Obre la carpeta"), self.obre_desti, False)
        if self.ultima_desti:
            self.b_obre.pack(side="left", padx=8)
        # Resultats
        f = tk.Frame(self.cos, bg=TARGETA, highlightbackground=LINIA, highlightthickness=1, padx=12, pady=10)
        f.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(f, text=self.t("Marca o desmarca els tipus de la llista abans de copiar."), bg=TARGETA, fg=SUAU,
                 font=(MT.TEXT, 9)).pack(anchor="w", pady=(0, 6))
        marc = tk.Frame(f, bg=TARGETA)
        self.arbre = ttk.Treeview(marc, columns=("n", "mida"), height=7)
        self.arbre.heading("#0", text=self.t("Tipus"), anchor="w")
        self.arbre.heading("n", text=self.t("Fitxers"), anchor="e")
        self.arbre.heading("mida", text=self.t("Mida"), anchor="e")
        self.arbre.column("#0", width=self.px(380), stretch=True)
        self.arbre.column("n", width=self.px(110), anchor="e", stretch=False)
        self.arbre.column("mida", width=self.px(130), anchor="e", stretch=False)
        self.arbre.tag_configure("cat", font=(MT.TEXT, 10, "bold"))
        self.arbre.tag_configure("off", foreground=SUAU)
        sb = ttk.Scrollbar(marc, orient="vertical", command=self.arbre.yview)
        self.arbre.configure(yscrollcommand=sb.set)
        self.arbre.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.arbre.bind("<Button-1>", self.clic_arbre)
        self.arbre.bind("<space>", lambda e: self.commuta(self.arbre.focus()))
        self.progres = ttk.Progressbar(f, mode="determinate")
        tk.Label(f, textvariable=self.v_estat, bg=TARGETA, fg=CREMA, font=(MT.TEXT, 10),
                 anchor="w", justify="left", wraplength=self.px(780)).pack(side="bottom", fill="x")
        self.progres.pack(side="bottom", fill="x", pady=(10, 4))
        marc.pack(fill="both", expand=True)
        self.omple_arbre()

        tk.Label(self, text=f"v{VERSIO}", bg=FONS, fg=LINIA, font=(MT.TEXT, 8)).pack(side="bottom", anchor="e",
                                                                                   padx=10)
        self.posa_treballant(self.treballant)

    def canvia_idioma(self, idi):
        self.idioma = idi
        estat = self.v_estat.get()
        self.construeix()
        self.v_estat.set(estat)
        self.desa_ajustos()

    def omple_origens(self, preferit=None):
        self.origens = {}
        for arrel, tipus, etiqueta in unitats():
            text = f"{arrel}   {self.t(tipus)}" + (f" · {etiqueta}" if etiqueta else "")
            self.origens[text] = arrel
        if preferit and preferit not in self.origens.values() and os.path.isdir(preferit):
            self.origens[preferit] = preferit
        self.cb_origen["values"] = list(self.origens)
        for text, cami in self.origens.items():
            if cami == preferit:
                self.v_origen.set(text)
                break
        else:
            if self.origens and self.v_origen.get() not in self.origens:
                self.v_origen.set(next(iter(self.origens)))

    def tria_origen(self):
        d = filedialog.askdirectory(parent=self)
        if d:
            d = os.path.normpath(d)
            self.omple_origens(d)

    def tria_desti(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.v_desti.get() or None)
        if d:
            self.v_desti.set(os.path.normpath(d))

    def obre_desti(self):
        if self.ultima_desti and os.path.isdir(self.ultima_desti):
            subprocess.Popen(["explorer", self.ultima_desti])

    def posa_treballant(self, sí):
        self.treballant = sí
        estat = "disabled" if sí else "normal"
        self.b_cerca.configure(state=estat)
        self.b_copia.configure(state=estat)
        if sí:
            self.b_atura.pack(side="left", padx=8)
        else:
            self.b_atura.pack_forget()

    # ── Llista de resultats ─────────────────────────────────────────────
    def omple_arbre(self):
        self.arbre.delete(*self.arbre.get_children())
        for cat, exts in self.resultats.items():
            n = sum(len(v) for v in exts.values())
            if not n:
                continue
            mida = sum(m for v in exts.values() for _, m in v)
            on = self.marcats.get(cat, True)
            nom = ("☑  " if on else "☐  ") + ICONES[cat] + "  " + self.t(cat)
            self.arbre.insert("", "end", iid=cat, text=nom, values=(self.num(n, 0), self.mida(mida)),
                              tags=("cat",) if on else ("cat", "off"))
            for ext, llista in sorted(exts.items(), key=lambda kv: -len(kv[1])):
                self.arbre.insert(cat, "end", text="." + ext, values=(
                    self.num(len(llista), 0), self.mida(sum(m for _, m in llista))),
                    tags=() if on else ("off",))

    def clic_arbre(self, ev):
        iid = self.arbre.identify_row(ev.y)
        if iid in self.resultats and self.arbre.identify_element(ev.x, ev.y) != "Treeitem.indicator":
            self.commuta(iid)

    def commuta(self, iid):
        if iid in self.resultats and not self.treballant:
            self.marcats[iid] = not self.marcats.get(iid, True)
            obert = {c for c in self.resultats if self.arbre.exists(c) and self.arbre.item(c, "open")}
            self.omple_arbre()
            for c in obert:
                self.arbre.item(c, open=True)

    # ── Cerca ───────────────────────────────────────────────────────────
    def cerca(self):
        origen = self.origens.get(self.v_origen.get())
        if not origen or not os.path.isdir(origen):
            return messagebox.showwarning("Xoriguer Cercador", self.t("Tria on buscar."), parent=self)
        ext_cat = {}
        for c, exts in CATEGORIES.items():
            if self.v_cat[c].get():
                for e in exts:
                    ext_cat.setdefault(e, c)
        if self.v_cat["Altres"].get():
            for e in self.v_altres.get().replace(";", ",").replace(" ", ",").split(","):
                e = e.strip().lstrip("*").lstrip(".").lower()
                if e:
                    ext_cat.setdefault(e, "Altres")
        if not ext_cat:
            return messagebox.showwarning("Xoriguer Cercador", self.t("Tria almenys un tipus de fitxer."),
                                          parent=self)
        self.desa_ajustos()
        desti = self.v_desti.get().strip()
        excloure = os.path.normcase(os.path.abspath(desti)) if desti else None
        self.resultats = {c: {} for c in ICONES}
        self.marcats = {}
        self.origen_cercat = origen
        self.trobats = 0
        self.omple_arbre()
        self.atura.clear()
        self.posa_treballant(True)
        self.progres.configure(mode="indeterminate")
        self.progres.start(12)
        self.inici = time.time()
        fil = threading.Thread(target=self._cerca_fil, daemon=True, args=(
            origen, ext_cat, self.v_sistema.get(), self.v_petites.get(), excloure))
        fil.start()
        self._segueix_cerca(fil)

    def _cerca_fil(self, origen, ext_cat, sistema, petites, excloure):
        pila = [origen]
        res = self.resultats
        while pila and not self.atura.is_set():
            carpeta = pila.pop()
            try:
                it = os.scandir(carpeta)
            except OSError:
                continue
            with it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if e.is_junction() or e.is_symlink():
                                continue
                            nom = e.name.lower()
                            if sistema and (nom in CARPETES_SISTEMA or nom.startswith("$")):
                                continue
                            if excloure and os.path.normcase(e.path) == excloure:
                                continue
                            pila.append(e.path)
                        else:
                            p = e.name.rfind(".")
                            if p <= 0:
                                continue
                            ext = e.name[p + 1:].lower()
                            cat = ext_cat.get(ext)
                            if not cat:
                                continue
                            mida = e.stat(follow_symlinks=False).st_size
                            if petites and cat == "Imatges" and mida < IMATGE_PETITA:
                                continue
                            res[cat].setdefault(ext, []).append((e.path, mida))
                            self.trobats += 1
                    except OSError:
                        continue

    def _segueix_cerca(self, fil):
        if fil.is_alive():
            self.v_estat.set(self.t("Cercant… {n} fitxers trobats", n=self.num(self.trobats, 0)))
            self.after(150, self._segueix_cerca, fil)
            return
        self.progres.stop()
        self.progres.configure(mode="determinate", value=0)
        self.posa_treballant(False)
        self.omple_arbre()
        n = self.trobats
        mida = sum(m for exts in self.resultats.values() for v in exts.values() for _, m in v)
        if self.atura.is_set():
            self.v_estat.set(f"{self.t('Aturat.')}  {self.t('Fitxers')}: {self.num(n, 0)} · {self.mida(mida)}")
        elif n:
            self.v_estat.set(self.t("Fet: {n} fitxers ({mida}) en {t}. Tria la destinació i prem Copia.",
                                    n=self.num(n, 0), mida=self.mida(mida), t=self.durada(time.time() - self.inici)))
        else:
            self.v_estat.set(self.t("No s'ha trobat cap fitxer."))

    # ── Còpia ───────────────────────────────────────────────────────────
    def copia(self):
        if not any(self.resultats.get(c) for c in ICONES):
            return messagebox.showwarning("Xoriguer Cercador", self.t("Primer fes una cerca."), parent=self)
        desti = self.v_desti.get().strip()
        if not desti:
            self.tria_desti()
            desti = self.v_desti.get().strip()
            if not desti:
                return
        try:
            os.makedirs(desti, exist_ok=True)
        except OSError as err:
            return messagebox.showerror("Xoriguer Cercador", str(err), parent=self)
        desti = os.path.abspath(desti)
        feina = [(cat, cami, mida) for cat, exts in self.resultats.items() if self.marcats.get(cat, True)
                 for v in exts.values() for cami, mida in v]
        if not feina:
            return messagebox.showwarning("Xoriguer Cercador", self.t("No hi ha res marcat per copiar."),
                                          parent=self)
        self.desa_ajustos()
        # Espai i FAT32
        total = sum(m for _, _, m in feina)
        try:
            lliure = shutil.disk_usage(desti).free
        except OSError:
            lliure = total
        if total > lliure and not messagebox.askyesno(
                self.t("Espai insuficient"),
                self.t("Cal {cal} i a la destinació només hi ha {lliure} lliures.\n\n"
                       "Vols copiar igualment el que hi càpiga?", cal=self.mida(total), lliure=self.mida(lliure)),
                parent=self):
            return
        _, fs = info_volum(os.path.splitdrive(desti)[0] + "\\")
        fat32 = fs.upper() in ("FAT32", "FAT")
        if fat32:
            grans = sum(1 for _, _, m in feina if m > MIDA_FAT32)
            if grans:
                messagebox.showinfo(self.t("Pendrive FAT32"), self.t(
                    "La destinació és FAT32 i hi ha {n} fitxers de més de 4 GB que no s'hi poden copiar. "
                    "Se saltaran.", n=grans), parent=self)
        self.atura.clear()
        self.posa_treballant(True)
        self.progres.configure(mode="determinate", maximum=max(total, 1), value=0)
        self.estat_copia = {"i": 0, "bytes": 0, "copiats": 0, "bytes_copiats": 0, "omesos": 0, "errors": []}
        self.inici = time.time()
        self.ultima_desti = desti
        fil = threading.Thread(target=self._copia_fil, daemon=True, args=(
            feina, desti, self.origen_cercat, self.v_carpetes.get(), self.v_duplicats.get(), fat32))
        fil.start()
        self.n_feina = len(feina)
        self._segueix_copia(fil)

    def _copia_fil(self, feina, desti, origen, carpetes, duplicats, fat32):
        st = self.estat_copia
        vistos = set()
        usats = set()          # camins de destinació ja fets servir en aquesta còpia
        for cat, cami, mida in feina:
            if self.atura.is_set():
                break
            st["i"] += 1
            try:
                nom = os.path.basename(cami)
                clau = (nom.lower(), mida)
                if (duplicats and clau in vistos) or (fat32 and mida > MIDA_FAT32):
                    st["omesos"] += 1
                    continue
                vistos.add(clau)
                carpeta_cat = os.path.join(desti, self.t(cat))
                if carpetes:
                    rel = os.path.relpath(os.path.dirname(cami), origen)
                    rel = "" if rel == "." else rel
                    final = os.path.join(carpeta_cat, rel, nom)
                else:
                    final = os.path.join(carpeta_cat, nom)
                # Ja hi és (d'una còpia anterior)? Mateixa mida → no cal tornar-lo a copiar.
                if os.path.normcase(final) not in usats and os.path.exists(camí_llarg(final)):
                    if os.path.getsize(camí_llarg(final)) == mida:
                        st["omesos"] += 1
                        usats.add(os.path.normcase(final))
                        continue
                arrel, ext = os.path.splitext(final)
                k = 2
                while os.path.normcase(final) in usats or os.path.exists(camí_llarg(final)):
                    final = f"{arrel} ({k}){ext}"
                    k += 1
                usats.add(os.path.normcase(final))
                os.makedirs(camí_llarg(os.path.dirname(final)), exist_ok=True)
                shutil.copy2(camí_llarg(cami), camí_llarg(final))
                st["copiats"] += 1
                st["bytes_copiats"] += mida
            except Exception as err:
                st["errors"].append(f"{cami}: {err}")
            finally:
                st["bytes"] += mida

    def _segueix_copia(self, fil):
        st = self.estat_copia
        self.progres.configure(value=st["bytes"])
        t = time.time() - self.inici
        if fil.is_alive():
            vel = st["bytes_copiats"] / t if t > 0.5 else 0
            self.v_estat.set(self.t("Copiant {i} de {n} · {mida} · {vel}/s", i=self.num(st["i"], 0),
                                    n=self.num(self.n_feina, 0), mida=self.mida(st["bytes"]), vel=self.mida(vel)))
            self.after(150, self._segueix_copia, fil)
            return
        self.posa_treballant(False)
        self.b_obre.pack(side="left", padx=8)
        text = self.t("Copiats {c} fitxers ({mida}) en {t}. Omesos: {o}. Errors: {e}.",
                      c=self.num(st["copiats"], 0), mida=self.mida(st["bytes_copiats"]), t=self.durada(t),
                      o=self.num(st["omesos"], 0), e=self.num(len(st["errors"]), 0))
        if self.atura.is_set():
            text = self.t("Aturat.") + " " + text
        self.v_estat.set(text)
        if st["errors"]:
            messagebox.showwarning(self.t("Errors"), self.t(
                "Hi ha hagut {e} errors. Els primers:\n\n{llista}", e=len(st["errors"]),
                llista="\n".join(st["errors"][:8])), parent=self)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
