#!/usr/bin/env python3
"""
generar_og_images.py
Genera imagenes Open Graph (1200x630px) para cada dia de evangelio.

Para cada dia con ilustracion AI del evangelio:
  - Redimensiona/recorta la imagen a 1200x630
  - Overlay oscuro para legibilidad
  - Texto: "Evangelio de hoy DD MMM YYYY" + titulo_dia
  - Logo "Evangelio para Hoy" esquina inferior

Uso:
    python scripts/generar_og_images.py --web-dir . --all
    python scripts/generar_og_images.py --web-dir . --date 2026-07-22
    python scripts/generar_og_images.py --web-dir . --month 2026-07

Requiere Pillow:
    pip install pillow

Output: public/img/dias/YYYY-MM-DD/og-image.webp
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ImportError:
    print("ERROR: Pillow no instalado. Ejecuta: pip install pillow")
    sys.exit(1)


MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_legible(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MESES_ES[int(m) - 1]} {y}"


def _find_font(web_dir: Path, bold: bool = True) -> Path | None:
    """Busca la fuente Cormorant Garamond."""
    candidates = [
        web_dir / "public" / "fonts" / "CormorantGaramond-Bold.ttf" if bold else web_dir / "public" / "fonts" / "CormorantGaramond-Regular.ttf",
        web_dir / "fonts" / "CormorantGaramond-Bold.ttf" if bold else web_dir / "fonts" / "CormorantGaramond-Regular.ttf",
    ]
    # Also check parent pipeline project
    candidates.append(
        Path(__file__).resolve().parent.parent.parent / "fonts" / "CormorantGaramond-Bold.ttf"
        if bold
        else Path(__file__).resolve().parent.parent.parent / "fonts" / "CormorantGaramond-Regular.ttf"
    )
    for c in candidates:
        if c.exists():
            return c
    return None


def generar_og_image(
    src_img: Path,
    dst_path: Path,
    fecha_iso: str,
    titulo_dia: str,
    font_path: Path | None,
) -> bool:
    """Genera una imagen OG de 1200x630 con overlay y texto."""
    try:
        img = Image.open(src_img).convert("RGB")
    except Exception as e:
        print(f"  WARN: no se pudo abrir {src_img.name}: {e}")
        return False

    # Crop a 1200x630 (centrado)
    target_w, target_h = 1200, 630
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    scaled = img.resize((int(src_w * scale), int(src_h * scale)), Image.LANCZOS)
    # Crop center
    left = (scaled.width - target_w) // 2
    top = (scaled.height - target_h) // 2
    og = scaled.crop((left, top, left + target_w, top + target_h))

    # Overlay oscuro gradient (mas oscuro abajo)
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(target_h):
        alpha = int(180 * (y / target_h))
        draw.line([(0, y), (target_w, y)], fill=(0, 0, 0, alpha))
    og = Image.alpha_composite(og.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(og)

    # Texto
    fecha_legible = _fecha_legible(fecha_iso)
    line1 = f"Evangelio de hoy {fecha_legible}"

    # Fuente
    font_size = 48
    font = None
    if font_path:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()

    # Calcular posicion (centrado inferior)
    try:
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        w1 = bbox1[2] - bbox1[0]
    except Exception:
        w1 = len(line1) * font_size * 0.5
    x1 = (target_w - w1) // 2
    y1 = target_h - 140

    draw.text((x1, y1), line1, fill=(255, 255, 255), font=font)

    # Subtitulo (titulo_dia) si existe
    if titulo_dia:
        font_small = None
        if font_path:
            try:
                font_small = ImageFont.truetype(str(font_path), 32)
            except Exception:
                pass
        if font_small is None:
            font_small = ImageFont.load_default()

        try:
            bbox2 = draw.textbbox((0, 0), titulo_dia, font=font_small)
            w2 = bbox2[2] - bbox2[0]
        except Exception:
            w2 = len(titulo_dia) * 32 * 0.5
        x2 = (target_w - w2) // 2
        draw.text((x2, target_h - 80), titulo_dia, fill=(212, 165, 116), font=font_small)

    # Logo esquina inferior derecha
    logo_text = "Evangelio para Hoy"
    font_logo = None
    if font_path:
        try:
            font_logo = ImageFont.truetype(str(font_path), 24)
        except Exception:
            pass
    if font_logo is None:
        font_logo = ImageFont.load_default()
    draw.text((20, 20), logo_text, fill=(212, 165, 116), font=font_logo)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    og.save(dst_path, "webp", quality=90, method=6)
    return True


def procesar_dia(web_dir: Path, fecha_iso: str, force: bool = False) -> bool:
    """Genera og-image.webp para un dia."""
    img_dir = web_dir / "public" / "img" / "dias" / fecha_iso
    og_path = img_dir / "og-image.webp"

    if og_path.exists() and not force:
        return True

    # Buscar imagen del evangelio
    evangelio_img = img_dir / f"evangelio-del-dia-{fecha_iso}.webp"
    if not evangelio_img.exists():
        # fallback: buscar cualquier webp
        webps = list(img_dir.glob("*.webp"))
        if webps:
            evangelio_img = webps[0]
        else:
            print(f"  SKIP {fecha_iso}: sin imagen base")
            return False

    # Leer titulo_dia del markdown
    md_path = web_dir / "src" / "content" / "evangelio" / f"{fecha_iso}.md"
    titulo_dia = ""
    if md_path.exists():
        with open(md_path, "r", encoding="utf-8") as f:
            in_fm = False
            fm_count = 0
            for line in f:
                if line.strip() == "---":
                    fm_count += 1
                    in_fm = fm_count == 1
                    continue
                if in_fm and line.startswith("titulo_dia:"):
                    val = line.split(":", 1)[1].strip().strip('"')
                    titulo_dia = val
                    break

    font_path = _find_font(web_dir)
    ok = generar_og_image(evangelio_img, og_path, fecha_iso, titulo_dia, font_path)
    if ok:
        print(f"  OK: {fecha_iso} -> og-image.webp")
    return ok


def _listar_fechas(web_dir: Path) -> list:
    """Lista fechas con imagen disponible."""
    img_base = web_dir / "public" / "img" / "dias"
    if not img_base.exists():
        return []
    return sorted([d.name for d in img_base.iterdir() if d.is_dir() and d.name[0].isdigit()])


def _fechas_de_mes(mes: str, fechas: list) -> list:
    return [f for f in fechas if f.startswith(mes)]


def main():
    parser = argparse.ArgumentParser(description="Genera imagenes Open Graph 1200x630 para evangelios.")
    parser.add_argument("--web-dir", default=".", help="Ruta raiz del repo evangelio-web")
    parser.add_argument("--date", dest="date_arg", help="Fecha YYYY-MM-DD")
    parser.add_argument("--month", dest="month_arg", help="Mes YYYY-MM")
    parser.add_argument("--all", action="store_true", help="Procesa todas las fechas")
    parser.add_argument("--force", action="store_true", help="Regenerar existentes")
    args = parser.parse_args()

    web_dir = Path(args.web_dir).resolve()
    if not web_dir.exists():
        print(f"ERROR: no existe {web_dir}")
        sys.exit(1)

    if args.date_arg:
        fechas = [args.date_arg]
    elif args.month_arg:
        todas = _listar_fechas(web_dir)
        fechas = _fechas_de_mes(args.month_arg, todas)
    elif args.all:
        fechas = _listar_fechas(web_dir)
    else:
        parser.error("Debe especificar --date, --month o --all")

    print(f"\nRepo web: {web_dir}")
    print(f"Fechas: {len(fechas)}\n")

    ok = 0
    for fecha in fechas:
        if procesar_dia(web_dir, fecha, force=args.force):
            ok += 1
    print(f"\nProcesadas: {ok}/{len(fechas)}")


if __name__ == "__main__":
    main()