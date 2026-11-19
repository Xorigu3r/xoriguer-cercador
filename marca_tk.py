"""Tipografia de la marca Xoriguer per als programes tkinter (norma de la casa, 12/11/2026).

Original: Documents/LOGOS-XORIGUER/_eines/tk/marca_tk.py — cada programa en porta una còpia al costat d'app.py
i la font a fonts/Montserrat-ExtraBold.ttf (cal posar ('fonts', 'fonts') a les datas del .spec).

    import marca_tk as MT
    tk.Label(..., font=(MT.TITOL, 16))          # títols: Montserrat ExtraBold (sense "bold": ja ho és)
    tk.Label(..., font=(MT.TEXT, 11))           # text: Segoe UI
    tk.Label(..., font=(MT.TEXT, 11, "bold"))

La Montserrat es carrega només per a aquest procés (no cal instal·lar-la). Si no es pot, títols en Segoe UI Black.
El rètol XORIGUER amb la X original no es pot escriure amb una font: es posa com a imatge (fes_rotul.py).
"""
import sys
from pathlib import Path

TEXT = "Segoe UI"
TEXT_SEMI = "Segoe UI Semibold"


def _base():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _carrega_titol():
    f = _base() / "fonts" / "Montserrat-ExtraBold.ttf"
    try:
        import ctypes
        if f.exists() and ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0) > 0:  # FR_PRIVATE
            return "Montserrat ExtraBold"
    except Exception:
        pass
    return "Segoe UI Black"


TITOL = _carrega_titol()
