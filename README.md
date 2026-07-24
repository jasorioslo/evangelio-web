# Evangelio para Hoy — Sitio web

Sitio estático generado con **[Astro](https://astro.build)** y hospedado en **Cloudflare Pages**.
Acompaña al pipeline Python `organizar-evangelios` — convierte los JSONs de lecturas en páginas HTML optimizadas para SEO.

- Dominio (próximamente): `evangelioparahoy.com`
- Autor de las reflexiones: **Padre Jose Miguel**
- Stack: Astro 5 + Tailwind + Cloudflare Pages

## Desarrollo local

```bash
npm install
npm run dev    # http://localhost:4321
npm run build  # genera dist/
```

## Sincronizar contenido del pipeline

```bash
# Desde la raiz de este repo
python scripts/lectura_a_markdown.py \
  --pipeline-dir ../organizar-evangelios \
  --all --force

# O para un mes especifico
python scripts/lectura_a_markdown.py \
  --pipeline-dir ../organizar-evangelios \
  --month 2026-07
```

El script:
1. Lee `output/lecturas_YYYY-MM-DD.json` del pipeline Python
2. Genera `src/content/evangelio/YYYY-MM-DD.md` (frontmatter + body)
3. Copia y optimiza `.png` AI → `.webp` en `public/img/dias/YYYY-MM-DD/`
4. Copia el audio de la reflexión a `public/audio/YYYY-MM-DD-reflexion.mp3`

## Estructura

```
evangelio-web/
├── src/
│   ├── content/
│   │   ├── config.ts                    Schema de Content Collections
│   │   ├── autor/padre-jose-miguel.md   Bio del autor
│   │   └── evangelio/YYYY-MM-DD.md      Un archivo por día
│   ├── layouts/
│   │   └── BaseLayout.astro
│   ├── pages/
│   │   ├── index.astro                  Home / placeholder
│   │   ├── hoy.astro                    Redirects al día actual
│   │   ├── evangelio/[fecha].astro     Página individual
│   │   ├── autor/[slug].astro
│   │   ├── calendario.astro
│   │   └── sobre.astro
│   ├── components/
│   │   ├── Header.astro
│   │   └── Footer.astro
│   └── styles/global.css
├── public/
│   ├── img/dias/                        Iluminarias AI por día (.webp)
│   ├── audio/                           Audios MP3 de reflexión
│   └── fonts/CormorantGaramond-*.ttf
├── scripts/lectura_a_markdown.py       Conversor JSON→MD
└── astro.config.mjs
```

## SEO

- **URLs keyword-rich:** `/evangelio/2026-07-22/`
- **Schema.org:** Article + AudioObject + BreadcrumbList
- **Sitemap.xml** automático via `@astrojs/sitemap`
- **RSS** (próximamente) en `/rss.xml`
- OpenGraph image por día

## Plan completo

Ver `../web.md` (estrategia) y `../tasks-web.md` (checklist).