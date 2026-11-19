"""Data real d'una foto o d'un vídeo, sense llibreries: EXIF (JPEG, TIFF i RAW basats en TIFF), àtom mvhd (MP4, MOV,
3GP) i, per als formats restants (HEIC, CR3, PNG amb EXIF...), una cerca del text «AAAA:MM:DD HH:MM:SS» a l'inici del fitxer.

    data_real(cami) -> timestamp (segons) o None si no se'n troba cap de vàlida.
"""
import os
import re
import struct
from datetime import datetime

EXT_TIFF = {"tif", "tiff", "dng", "cr2", "nef", "nrw", "arw", "srf", "sr2", "pef", "srw", "orf", "rw2", "raf"}
EXT_JPEG = {"jpg", "jpeg", "jfif"}
EXT_MP4 = {"mp4", "m4v", "mov", "3gp", "3g2", "qt"}
EXT_ALTRES = {"heic", "heif", "avif", "cr3", "png", "webp"}
EXT_AMB_DATA = EXT_TIFF | EXT_JPEG | EXT_MP4 | EXT_ALTRES

_TEXT_DATA = re.compile(rb"((?:19|20)\d\d):([01]\d):([0-3]\d) ([0-2]\d):([0-5]\d):([0-5]\d)")
_MIN = datetime(1990, 1, 1).timestamp()


def _valida(ts):
    try:
        return ts if _MIN <= ts <= datetime.now().timestamp() + 86400 * 2 else None
    except (OverflowError, OSError, ValueError):
        return None


def _text_a_ts(b):
    m = _TEXT_DATA.search(b)
    if not m:
        return None
    try:
        return _valida(datetime(*map(int, m.groups())).timestamp())
    except ValueError:
        return None


def _exif_tiff(buf):
    """DateTimeOriginal (0x9003), o si no DateTime (0x0132), d'un bloc TIFF (comença per II* o MM*)."""
    if len(buf) < 8:
        return None
    o = {b"II": "<", b"MM": ">"}.get(buf[:2])
    if not o:
        return None

    def ifd(pos):
        if pos + 2 > len(buf):
            return {}
        n = struct.unpack_from(o + "H", buf, pos)[0]
        tags = {}
        for i in range(min(n, 500)):
            p = pos + 2 + i * 12
            if p + 12 > len(buf):
                break
            tag, tipus, cnt = struct.unpack_from(o + "HHI", buf, p)
            tags[tag] = (tipus, cnt, p + 8)
        return tags

    def text(t):
        tipus, cnt, p = t
        if tipus != 2:
            return None
        if cnt > 4:
            p = struct.unpack_from(o + "I", buf, p)[0]
        return buf[p:p + cnt]

    ifd0 = ifd(struct.unpack_from(o + "I", buf, 4)[0])
    candidats = []
    if 0x8769 in ifd0:   # Exif SubIFD
        sub = ifd(struct.unpack_from(o + "I", buf, ifd0[0x8769][2])[0])
        for tag in (0x9003, 0x9004):
            if tag in sub:
                candidats.append(text(sub[tag]))
    if 0x0132 in ifd0:
        candidats.append(text(ifd0[0x0132]))
    for c in candidats:
        ts = _text_a_ts(c or b"")
        if ts:
            return ts
    return None


def _jpeg(f):
    if f.read(2) != b"\xff\xd8":
        return None
    for _ in range(64):
        cap = f.read(4)
        if len(cap) < 4 or cap[0] != 0xFF:
            return None
        marca, mida = cap[1], struct.unpack(">H", cap[2:])[0]
        if marca == 0xE1:
            dades = f.read(mida - 2)
            if dades[:6] == b"Exif\x00\x00":
                return _exif_tiff(dades[6:])
        elif marca in (0xDA, 0xD9):   # comença la imatge: ja no hi haurà EXIF
            return None
        else:
            f.seek(mida - 2, 1)
    return None


def _mp4(f, mida_fitxer):
    """creation_time de moov/mvhd (segons des de 1904, UTC)."""
    def atoms(inici, fi):
        pos = inici
        while pos + 8 <= fi:
            f.seek(pos)
            cap = f.read(8)
            if len(cap) < 8:
                return
            mida, tipus = struct.unpack(">I4s", cap)
            h = 8
            if mida == 1:
                mida = struct.unpack(">Q", f.read(8))[0]
                h = 16
            elif mida == 0:
                mida = fi - pos
            if mida < h:
                return
            yield tipus, pos + h, pos + mida
            pos += mida

    for tipus, ini, fi in atoms(0, mida_fitxer):
        if tipus == b"moov":
            for t2, i2, _ in atoms(ini, fi):
                if t2 == b"mvhd":
                    f.seek(i2)
                    versio = f.read(4)[0]
                    seg = struct.unpack(">Q", f.read(8))[0] if versio == 1 else struct.unpack(">I", f.read(4))[0]
                    if seg:
                        return _valida(seg - 2082844800)   # 1904 → 1970
                    return None
            return None
    return None


def data_real(cami, ext=None):
    ext = (ext or os.path.splitext(cami)[1][1:]).lower()
    if ext not in EXT_AMB_DATA:
        return None
    try:
        with open(cami, "rb") as f:
            if ext in EXT_JPEG:
                return _jpeg(f)
            if ext in EXT_MP4:
                return _mp4(f, os.fstat(f.fileno()).st_size)
            cap = f.read(256 * 1024)
            if ext in EXT_TIFF and cap[:2] in (b"II", b"MM"):
                ts = _exif_tiff(cap)
                if ts:
                    return ts
            return _text_a_ts(cap)
    except (OSError, struct.error, IndexError, ValueError):
        return None


if __name__ == "__main__":
    import sys
    for c in sys.argv[1:]:
        ts = data_real(c)
        print(c, "→", datetime.fromtimestamp(ts) if ts else None)
