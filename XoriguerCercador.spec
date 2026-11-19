# -*- mode: python ; coding: utf-8 -*-
# Compilar:  py -m PyInstaller --noconfirm --clean XoriguerCercador.spec   (o compilar.bat)
a = Analysis(
    ['app.py'],
    datas=[('assets', 'assets'), ('fonts', 'fonts')],
    hiddenimports=['marca_tk', 'traduccions'],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'openpyxl', 'reportlab'],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='XoriguerCercador',
    console=False,
    upx=False,
    icon='assets/icona.ico',
)
