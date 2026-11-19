"""Icona de Xoriguer Cercador: carpeta taronja amb una lupa (lent blava), sense falcó. Fons «Blau pissarra».

Ús:  python -I eines/genera_icona.py   → assets/icona.ico, assets/icona_64.png, assets/icona_192.png, assets/icona_512.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ARREL = Path(__file__).resolve().parent.parent
ASSETS = ARREL / 'assets'
FONS = (30, 42, 59, 255)        # #1E2A3B
FONS2 = (39, 53, 74, 255)       # #27354A
CREMA = (246, 239, 226, 255)
TARONJA = (255, 168, 46, 255)
TARONJA_FOSC = (242, 101, 15, 255)
BLAU = (127, 178, 255, 255)
S = 4


def degradat(N, c1, c2, y0, y1):
    g = Image.new('RGBA', (1, N))
    for y in range(N):
        t = min(1, max(0, (y - y0) / max(1, y1 - y0)))
        g.putpixel((0, y), tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4)))
    return g.resize((N, N))


def dibuixa(mida, rodo=True):
    N, k = 512 * S, S
    im = Image.new('RGBA', (N, N), FONS)
    # resplendor
    g = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([70 * k, 90 * k, 442 * k, 440 * k], fill=TARONJA[:3] + (70,))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(48 * k)))
    # carpeta: pestanya + cos amb degradat
    m = Image.new('L', (N, N), 0)
    dm = ImageDraw.Draw(m)
    dm.rounded_rectangle([58 * k, 112 * k, 230 * k, 190 * k], radius=22 * k, fill=255)
    dm.rounded_rectangle([58 * k, 150 * k, 420 * k, 400 * k], radius=30 * k, fill=255)
    im.paste(degradat(N, TARONJA, TARONJA_FOSC, 112 * k, 400 * k), (0, 0), m)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([58 * k, 150 * k, 420 * k, 400 * k], radius=30 * k, outline=CREMA, width=8 * k)
    d.line([(76 * k, 190 * k), (402 * k, 190 * k)], fill=CREMA[:3] + (120,), width=5 * k)
    # fitxers dins (ratlles)
    for i, w in enumerate((190, 150, 120)):
        y = 236 + i * 40
        d.rounded_rectangle([96 * k, y * k, (96 + w) * k, (y + 14) * k], radius=7 * k, fill=FONS2)
    # lupa
    cx, cy, r = 322, 318, 82
    llum = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(llum).ellipse([(cx - r - 14) * k, (cy - r - 14) * k, (cx + r + 14) * k, (cy + r + 14) * k],
                                 fill=BLAU[:3] + (120,))
    im.alpha_composite(llum.filter(ImageFilter.GaussianBlur(12 * k)))
    d = ImageDraw.Draw(im)
    d.line([((cx + 56) * k, (cy + 56) * k), ((cx + 128) * k, (cy + 128) * k)], fill=FONS, width=50 * k)
    d.line([((cx + 58) * k, (cy + 58) * k), ((cx + 124) * k, (cy + 124) * k)], fill=CREMA, width=34 * k)
    d.ellipse([(cx - r - 10) * k, (cy - r - 10) * k, (cx + r + 10) * k, (cy + r + 10) * k], fill=FONS)
    d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=FONS2, outline=CREMA, width=16 * k)
    d.ellipse([(cx - r + 18) * k, (cy - r + 18) * k, (cx + r - 18) * k, (cy + r - 18) * k], outline=BLAU, width=6 * k)
    d.arc([(cx - 48) * k, (cy - 48) * k, (cx + 48) * k, (cy + 48) * k], 200, 260, fill=CREMA, width=10 * k)
    if rodo:
        mk = Image.new('L', (N, N), 0)
        ImageDraw.Draw(mk).rounded_rectangle([0, 0, N - 1, N - 1], radius=N // 5, fill=255)
        im.putalpha(mk)
    return im.resize((mida, mida), Image.LANCZOS)


if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    gran = dibuixa(1024)
    gran.save(ASSETS / 'icona.ico', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    dibuixa(512).save(ASSETS / 'icona_512.png')
    dibuixa(192, rodo=False).save(ASSETS / 'icona_192.png')
    dibuixa(64).save(ASSETS / 'icona_64.png')
    print('Icones a', ASSETS)
