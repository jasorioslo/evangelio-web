#!/usr/bin/env python3
"""
lectura_a_markdown.py
Convierte los JSONs del pipeline organizar-evangelios en archivos Markdown
para el sitio Astro “Evangelio para Hoy”.

Uso:
    python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --all
    python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --date 2026-07-22
    python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --month 2026-07

Requiere уровень Python 3.10+ y Pillow (para convertir PNG -> WebP):
    pip install pillow pyyaml

Genera en el repo web:
    src/content/evangelio/YYYY-MM-DD.md
    public/img/dias/YYYY-MM-DD/{primera_lectura,segunda_lectura,evangelio}.webp
    public/audio/YYYY-MM-DD-reflexion.mp3
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except ImportError:
    Image = None  # conversion a WebP opcional si Pillow no esta


# ------------------------------------------------------------------ helpers


def _iso_fecha(fecha_es: str) -> str:
    """22/07/2026 -> 2026-07-22"""
    d, m, y = fecha_es.split("/")
    return f"{y}-{m.zfill(2)}-{d.zfill(2)}"


def _fecha_pipeline_to_dir(fecha_es: str) -> str:
    """22/07/2026 -> 22-07-2026 (formato carpetas del pipeline)"""
    d, m, y = fecha_es.split("/")
    return f"{d.zfill(2)}-{m.zfill(2)}-{y}"


def _slug_titulo_dia(titulo: str) -> str:
    """Normaliza titulo_dia para keywords/urls: minúsculas, sin acentos."""
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ñ": "N",
    }
    for k, v in replacements.items():
        titulo = titulo.replace(k, v)
    return titulo.lower()


def _build_title(datos: dict, iso: str) -> str:
    """title SEO de la pagina archivo, <= 75 caracteres idealmente."""
    fecha_legible = _fecha_legible_es(iso)  # "22 julio 2026"
    base = f"Evangelio {fecha_legible}"
    titulo_dia = datos.get("titulo_dia", "").strip()
    if titulo_dia:
        base += f" — {titulo_dia}"
    if len(base) > 75:
        base = base[:72] + "..."
    if "Evangelio para Hoy" not in base:
        base += " | Evangelio para Hoy"
    return base


def _build_description(datos: dict, iso: str) -> str:
    """Meta description <= 165 caracteres."""
    fecha_legible = _fecha_legible_es(iso)
    ev = datos.get("evangelio", {}).get("referencia", "")
    titulo = datos.get("titulo_dia", "").strip()
    parts = [f"Lecturas, salmo y evangelio del {fecha_legible}"]
    if titulo:
        parts.append(f"({titulo})")
    if ev:
        parts.append(f"segun {ev}")
    desc = " ".join(parts) + ". Reflexion del Padre Jose Miguel con audio y video."
    if len(desc) > 165:
        desc = desc[:162] + "..."
    return desc


def _build_keywords(datos: dict, iso: str) -> list:
    """Lista de keywords long-tail para el frontmatter."""
    kw = [
        f"evangelio {iso}",
        f"lecturas {iso}",
    ]
    titulo_dia = datos.get("titulo_dia", "").strip()
    if titulo_dia:
        kw.append(titulo_dia.lower())
        kw.append(f"{titulo_dia.lower()} {iso}")
    ev_ref = datos.get("evangelio", {}).get("referencia", "")
    if ev_ref:
        kw.append(f"reflexion evangelio {ev_ref}")
    salmo_ref = datos.get("salmo", {}).get("referencia", "")
    if salmo_ref:
        kw.append(f"salmo responsorial {salmo_ref}")
    return kw[:10]


# ----------------------------------------------- markdown body generators


_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_legible_es(iso: str) -> str:
    """2026-07-22 -> '22 julio 2026' (para alt text SEO)."""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.day} {_MESES_ES[d.month - 1]} {d.year}"
    except ValueError:
        return iso


def _md_cita(texto: str) -> str:
    """Convierte el texto biblico a un bloque blockquote con un <p> por parrafo.

    El texto de USCCB usa \n para separar versiculos/estrofas y \n\n para
    saltos de parrafo mas amplios. Cada uno se convierte en un parrafo propio
    dentro de la cita, asi el CSS puede dar espacio vertical entre ellos.
    """
    out = ['>']  # abre blockquote
    # Usamos blank-line dentro de blockquote como separador de parrafo
    parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    if not parrafos:
        # Caso sin \n\n: split por \n unico
        parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    for i, parrafo in enumerate(parrafos):
        # Convierto los \n internos en <br> dentro del parrafo para no perder versiculos
        texto_html = parrafo.replace("\n", "  \n> ")
        out.append(f"> {texto_html}")
        out.append(">")  # linea en blanco dentro del blockquote -> nuevo <p>
    return "\n".join(out).rstrip()


def _md_salmo_versiculos(versiculos: list) -> str:
    """Renderiza los versiculos del salmo/aclamacion con separacion clara."""
    out = []
    for v in versiculos:
        tipo = v.get("tipo", "normal")
        texto = v["texto"].strip()
        if tipo == "R":
            out.append(f"**R.** *{texto}*")
        else:
            out.append(texto)
        out.append("")  # linea en blanco = parrafo separado
    return "\n\n".join(out)


def _build_body_markdown(datos: dict, iso: str, imagen_primera: str | None = None, imagen_segunda: str | None = None) -> str:
    """Cuerpo de la pagina en markdown (despues del frontmatter)."""
    pl = datos.get("primera_lectura", {})
    salmo = datos.get("salmo", {})
    aclamacion = datos.get("aclamacion", {})
    segunda = datos.get("segunda_lectura")
    ev = datos.get("evangelio", {})
    reflexion = datos.get("reflexion", "")

    fecha_legible = _fecha_legible_es(iso)
    body = []

    # --- Primera lectura ---
    body.append("## Primera Lectura\n")
    body.append(f"**Lectura {pl.get('referencia', '')}**\n")
    if imagen_primera:
        ref = pl.get("referencia", "")
        alt = f"Primera lectura de hoy {fecha_legible}"
        if ref:
            alt += f" — {ref}"
        alt += " (ilustración)"
        body.append(f"![{alt}]({imagen_primera})\n")
    body.append(_md_cita(pl.get("texto", "")) + "\n")
    body.append("> *Palabra de Dios. Te alabamos, Señor.*\n")

    # --- Salmo ---
    body.append("## Salmo Responsorial\n")
    body.append(f"**Salmo responsorial — {salmo.get('referencia', '')}**\n")
    body.append(_md_salmo_versiculos(salmo.get("versiculos", [])) + "\n")

    # --- Aclamación ---
    body.append("## Aclamación antes del Evangelio\n")
    if aclamacion.get("referencia"):
        body.append(f"**{aclamacion['referencia']}**\n")
    body.append(_md_salmo_versiculos(aclamacion.get("versiculos", [])) + "\n")

    # --- Segunda lectura (condicional) ---
    if segunda and segunda.get("texto"):
        body.append("## Segunda Lectura\n")
        body.append(f"**Lectura {segunda.get('referencia', '')}**\n")
        if imagen_segunda:
            ref = segunda.get("referencia", "")
            alt = f"Segunda lectura de hoy {fecha_legible}"
            if ref:
                alt += f" — {ref}"
            alt += " (ilustración)"
            body.append(f"![{alt}]({imagen_segunda})\n")
        body.append(_md_cita(segunda.get("texto", "")) + "\n")
        body.append("> *Palabra de Dios. Te alabamos, Señor.*\n")

    # --- Evangelio ---
    body.append("## Evangelio\n")
    body.append(f"**Lectura del santo evangelio según {ev.get('referencia', '')}**\n")
    body.append(_md_cita(ev.get("texto", "")) + "\n")
    body.append("> *Palabra del Señor. Gloria a ti, Señor Jesús.*\n")

    # --- Reflexión ---
    body.append("## Reflexión del Padre Jose Miguel\n")
    if reflexion:
        for parrafo in reflexion.split("\n\n"):
            parrafo = parrafo.strip()
            if parrafo:
                body.append(parrafo + "\n")
    else:
        body.append("*Reflexión próximamente.*\n")

    return "\n".join(body)


# ----------------------------------------------- frontmatter generator


def _yaml_escape(s: str) -> str:
    """Escapa comillas dobles para YAML."""
    return s.replace('"', '\\"')


def _build_frontmatter(datos: dict, iso: str, autor_slug: str = "padre-jose-miguel") -> str:
    """Devuelve el bloque YAML frontmatter (entre ---)"""
    title = _yaml_escape(_build_title(datos, iso))
    description = _yaml_escape(_build_description(datos, iso))
    canonical = f"https://evangelioparahoy.com/evangelio/{iso}/"
    keywords = _build_keywords(datos, iso)

    titulo_dia = _yaml_escape(datos.get("titulo_dia", ""))

    pl = datos.get("primera_lectura", {})
    salmo = datos.get("salmo", {})
    aclamacion = datos.get("aclamacion", {})
    segunda = datos.get("segunda_lectura")
    ev = datos.get("evangelio", {})

    # Paths AI media (nombres SEO-optimizados con fecha)
    imagen_primera = f"/img/dias/{iso}/primera-lectura-del-dia-{iso}.webp"
    imagen_segunda = f"/img/dias/{iso}/segunda-lectura-del-dia-{iso}.webp" if segunda and segunda.get("texto") else None
    imagen = f"/img/dias/{iso}/evangelio-del-dia-{iso}.webp"
    audio_reflexion = f"/audio/{iso}-reflexion.mp3"

    fm = []
    fm.append("---")
    fm.append(f'title: "{title}"')
    fm.append(f'description: "{description}"')
    fm.append(f"canonical: {canonical}")
    fm.append("keywords:")
    for k in keywords:
        fm.append(f"  - {k}")
    fm.append(f'fecha: "{iso}"')
    fm.append(f'titulo_dia: "{titulo_dia}"')
    fm.append(f"autor: {autor_slug}")
    fm.append(f"imagen: {imagen}")
    fm.append(f"imagen_primera: {imagen_primera}")
    if imagen_segunda:
        fm.append(f"imagen_segunda: {imagen_segunda}")
    fm.append(f"audio_reflexion: {audio_reflexion}")
    fm.append("youtube_id: ''")  # rellenar manualmente al subir
    fm.append("primera_lectura:")
    fm.append(f'  referencia: "{_yaml_escape(pl.get("referencia", ""))}"')
    fm.append("  texto: |")
    for line in pl.get("texto", "").split("\n"):
        fm.append(f"    {line}")
    fm.append("salmo:")
    fm.append(f'  referencia: "{_yaml_escape(salmo.get("referencia", ""))}"')
    salmo_vers = salmo.get("versiculos") or []
    if not salmo_vers:
        fm.append("  versiculos: []")
    else:
        fm.append("  versiculos:")
        for v in salmo_vers:
            fm.append(f"    - tipo: {v.get('tipo', 'normal')}")
            fm.append("      texto: |")
            for line in v["texto"].split("\n"):
                fm.append(f"        {line}")
    fm.append("aclamacion:")
    fm.append(f'  referencia: "{_yaml_escape(aclamacion.get("referencia", "") or "")}"')
    acl_vers = aclamacion.get("versiculos") or []
    if not acl_vers:
        fm.append("  versiculos: []")
    else:
        fm.append("  versiculos:")
        for v in acl_vers:
            fm.append(f"    - tipo: {v.get('tipo', 'normal')}")
            fm.append("      texto: |")
            for line in v["texto"].split("\n"):
                fm.append(f"        {line}")
    if segunda and segunda.get("texto"):
        fm.append("segunda_lectura:")
        fm.append(f'  referencia: "{_yaml_escape(segunda.get("referencia", ""))}"')
        fm.append("  texto: |")
        for line in segunda.get("texto", "").split("\n"):
            fm.append(f"    {line}")
    fm.append("evangelio:")
    fm.append(f'  referencia: "{_yaml_escape(ev.get("referencia", ""))}"')
    fm.append("  texto: |")
    for line in ev.get("texto", "").split("\n"):
        fm.append(f"    {line}")
    fm.append("reflexion: |")
    for line in (datos.get("reflexion", "") or "").split("\n"):
        fm.append(f"  {line}")
    fm.append("---")
    return "\n".join(fm)


# ----------------------------------------------- media sync


def _optimize_png_to_webp(src: Path, dst: Path, max_width: int = 1600, quality: int = 85) -> bool:
    """Convierte PNG a WebP redimensionando. Retorna True si tuvo exito.

    Genera 3 tamanos responsive: 400px, 800px, 1600px (sufijos -400.webp, -800.webp, -1600.webp).
    El archivo base (sin sufijo) es el de 1600px.
    """
    if not src.exists():
        return False
    if Image is None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst.with_suffix(".png"))
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        img = Image.open(src)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Generar 3 tamanos responsive
        base_name = dst.stem  # e.g. "evangelio-del-dia-2026-07-22"
        sizes = [400, 800, 1600]
        for size in sizes:
            ratio = size / img.width
            new_h = int(img.height * ratio)
            resized = img.resize((size, new_h), Image.LANCZOS)
            sized_dst = dst.parent / f"{base_name}-{size}.webp"
            resized.save(sized_dst, "webp", quality=quality if size <= 800 else 88, method=6)

        # Guardar tambien el base (1600px) para compatibilidad
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
        img.save(dst, "webp", quality=quality, method=6)
        return True
    except Exception as e:
        print(f"  WARN: no se pudo convertir {src.name}: {e}")
        return False


def _copy_reflexion_audio(pipeline_audio_dir: Path, fecha_pipeline_dir: str, dst: Path) -> bool:
    """Copia el MP3 de reflexion del pipeline a public/audio/."""
    carpeta = pipeline_audio_dir / fecha_pipeline_dir
    if not carpeta.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    for f in sorted(os.listdir(carpeta)):
        if f.endswith("_reflexion.mp3"):
            shutil.copy2(carpeta / f, dst)
            return True
    return False


def _copy_media(datos: dict, pipeline_dir: Path, web_dir: Path, fecha_iso: str) -> dict:
    """Copia/comprime imagenes y audio a public/. Retorna dict con rutas usadas."""
    fecha_pipeline_dir = _fecha_pipeline_to_dir(datos.get("fecha", fecha_iso))
    img_src_dir = pipeline_dir / "audio" / "img" / fecha_pipeline_dir
    audio_src_dir = pipeline_dir / "audio" / "clips" / fecha_pipeline_dir

    img_dst_dir = web_dir / "public" / "img" / "dias" / fecha_iso
    audio_dst_dir = web_dir / "public" / "audio"

    media = {"imagenes": [], "audio_reflexion": False}

    # Imagenes AI -> nombres SEO: {seccion}-del-dia-YYYY-MM-DD.webp
    secciones_img = [
        ("primera_lectura", f"primera-lectura-del-dia-{fecha_iso}.webp"),
        ("evangelio", f"evangelio-del-dia-{fecha_iso}.webp"),
        ("segunda_lectura", f"segunda-lectura-del-dia-{fecha_iso}.webp"),
    ]
    for field, webp_name in secciones_img:
        src = img_src_dir / f"{fecha_pipeline_dir}_{field}.png"
        dst = img_dst_dir / webp_name
        if _optimize_png_to_webp(src, dst):
            media["imagenes"].append(field)

    # Audio de la reflexion
    audio_dst = audio_dst_dir / f"{fecha_iso}-reflexion.mp3"
    if _copy_reflexion_audio(audio_src_dir.parent, fecha_pipeline_dir, audio_dst):
        media["audio_reflexion"] = True

    return media


# ----------------------------------------------- main process day


def procesar_dia(pipeline_dir: Path, web_dir: Path, fecha_iso: str, force: bool = False) -> bool:
    """Procesa un dia: lee el JSON del pipeline y genera el .md + media."""
    # JSON: output/lecturas_YYYY-MM-DD.json
    json_path = pipeline_dir / "output" / f"lecturas_{fecha_iso}.json"
    if not json_path.exists():
        print(f"  SKIP: {fecha_iso} (no existe {json_path.name})")
        return False

    md_path = web_dir / "src" / "content" / "evangelio" / f"{fecha_iso}.md"
    if md_path.exists() and not force:
        print(f"  SKIP: {fecha_iso} (ya existe .md, usar --force)")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        datos = json.load(f)

    if not datos.get("evangelio", {}).get("texto"):
        print(f"  WARN: {fecha_iso} evangelio vacio -> se genera igual (placeholder)")
    if not datos.get("reflexion"):
        print(f"  WARN: {fecha_iso} sin reflexion")

    # Media
    media = _copy_media(datos, pipeline_dir, web_dir, fecha_iso)

    # Rutas SEO para las imagenes inline (solo si se copiaron con exito)
    imgs = set(media.get("imagenes", []))
    imagen_primera = f"/img/dias/{fecha_iso}/primera-lectura-del-dia-{fecha_iso}.webp" if "primera_lectura" in imgs else None
    imagen_segunda = f"/img/dias/{fecha_iso}/segunda-lectura-del-dia-{fecha_iso}.webp" if "segunda_lectura" in imgs else None

    # Frontmatter + body
    frontmatter = _build_frontmatter(datos, fecha_iso)
    body = _build_body_markdown(datos, fecha_iso, imagen_primera=imagen_primera, imagen_segunda=imagen_segunda)
    contenido = frontmatter + "\n\n" + body + "\n"

    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenido)

    imagenes_str = ", ".join(media["imagenes"]) if media["imagenes"] else "(sin imagenes)"
    audio_str = "OK" if media["audio_reflexion"] else "FALTA"
    print(f"  OK: {fecha_iso} -> {md_path.name}  imgs:[{imagenes_str}]  audio:{audio_str}")
    return True


# ----------------------------------------------- CLI fechas


def _listar_fechas_disponibles(pipeline_dir: Path) -> list:
    """Lista todas las fechas YYYY-MM-DD con JSON disponible en el pipeline."""
    out_dir = pipeline_dir / "output"
    fechas = []
    for f in sorted(os.listdir(out_dir)):
        if f.startswith("lecturas_") and f.endswith(".json"):
            fechas.append(f[len("lecturas_") : -len(".json")])
    return fechas


def _fechas_de_mes(mes_arg: str, pipeline_dir: Path) -> list:
    """Filtra fechas JSON disponibles para un mes YYYY-MM."""
    disponibles = set(_listar_fechas_disponibles(pipeline_dir))
    resultado = []
    dia = 1
    while True:
        try:
            fecha = datetime.strptime(f"{mes_arg}-{dia:02d}", "%Y-%m-%d")
        except ValueError:
            break
        iso = fecha.strftime("%Y-%m-%d")
        if iso in disponibles:
            resultado.append(iso)
        dia += 1
        if dia > 31:
            break
    return resultado


# ----------------------------------------------- entry point


def main():
    parser = argparse.ArgumentParser(
        description="Convierte JSONs del pipeline organizar-evangelios en Markdown para el sitio web Astro.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --all
  python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --date 2026-07-22 --force
  python scripts/lectura_a_markdown.py --pipeline-dir ../organizar-evangelios --month 2026-07
        """,
    )
    parser.add_argument("--pipeline-dir", required=True, help="Ruta al repo organizar-evangelios")
    parser.add_argument("--out", default=".", help="Ruta raiz del repo evangelio-web (default: actual)")
    parser.add_argument("--date", dest="date_arg", help="Fecha YYYY-MM-DD a procesar")
    parser.add_argument("--month", dest="month_arg", help="Mes YYYY-MM a procesar (todas las fechas disponibles)")
    parser.add_argument("--all", action="store_true", help="Procesa todos los JSONs disponibles")
    parser.add_argument("--force", action="store_true", help="Sobreescribir .md existentes")
    args = parser.parse_args()

    pipeline_dir = Path(args.pipeline_dir).resolve()
    web_dir = Path(args.out).resolve()

    if not pipeline_dir.exists():
        print(f"ERROR: no existe el directorio pipeline: {pipeline_dir}")
        sys.exit(1)

    if not (pipeline_dir / "output").exists():
        print(f"ERROR: {pipeline_dir} no contiene carpeta output/lecturas_*.json")
        sys.exit(1)

    # Resolver lista de fechas a procesar
    if args.date_arg:
        fechas = [args.date_arg]
    elif args.month_arg:
        fechas = _fechas_de_mes(args.month_arg, pipeline_dir)
        if not fechas:
            print(f"Advertencia: no hay JSONs para el mes {args.month_arg}")
    elif args.all:
        fechas = _listar_fechas_disponibles(pipeline_dir)
    else:
        parser.error("Debe especificar --date YYYY-MM-DD, --month YYYY-MM o --all")

    if not fechas:
        print("No hay fechas para procesar.")
        sys.exit(0)

    print(f"\nPipeline dir: {pipeline_dir}")
    print(f"Repo web:    {web_dir}")
    print(f"Fechas:      {len(fechas)}\n")

    ok = 0
    skip = 0
    for fecha_iso in fechas:
        try:
            if procesar_dia(pipeline_dir, web_dir, fecha_iso, force=args.force):
                ok += 1
            else:
                skip += 1
        except Exception as e:
            print(f"  ERROR {fecha_iso}: {e}")

    print(f"\nProcesadas: {ok} OK, {skip} skip, total {len(fechas)} fechas.")
    print("\nSiguiente paso:")
    print(f"  cd {web_dir}")
    print("  npm run dev   # o 'npm run build' y commit+push")


if __name__ == "__main__":
    main()