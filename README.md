# Xoriguer Cercador

Cerca fitxers per tipus en un disc dur (imatges, vídeos, música, documents, comprimits o les extensions que vulguis)
i els copia a una carpeta, a un altre disc o a un pendrive. Ràpid, senzill i gratis. Per a Windows.

**Baixa'l:** https://xoriguer.dev/#utils

- Tria el disc o la carpeta, marca els tipus i prem **Cerca** (un disc sencer en pocs segons).
- Desmarca el que no vulguis i prem **Copia**: es fa una carpeta per tipus, mantenint les carpetes originals o tot junt.
- Omet les carpetes del sistema, les icones petites i els duplicats (mateix nom i mida).
- Avisa si no hi ha espai i si el pendrive és FAT32 (fitxers de més de 4 GB).
- Si la còpia s'atura, en tornar-la a fer continua on s'havia quedat.
- En català, castellà, francès i anglès.

---

**ES** · Busca archivos por tipo en un disco (imágenes, vídeos, música, documentos…) y los copia a otro disco o a un pendrive.
**FR** · Recherche des fichiers par type sur un disque (images, vidéos, musique, documents…) et les copie vers un autre disque ou une clé USB.
**EN** · Finds files by type on a drive (images, videos, music, documents…) and copies them to another drive or a USB stick.

## Compilar
```
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean XoriguerCercador.spec
```
Icones: `python -I eines/genera_icona.py`. Fet amb Python 3.12 i tkinter.
