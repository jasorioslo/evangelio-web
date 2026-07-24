import { defineCollection, z } from 'astro:content';

// Colección: Evangelio del día
// Un archivo .md por fecha en src/content/evangelio/YYYY-MM-DD.md
const evangelio = defineCollection({
  type: 'content',
  schema: z.object({
    // SEO
    title: z.string(),
    description: z.string().max(165),
    canonical: z.string().url(),
    keywords: z.array(z.string()).optional(),

    // Fecha y liturgia
    fecha: z.string(), // YYYY-MM-DD
    titulo_dia: z.string().default(''), // "Fiesta de Santa María Magdalena"
    ciclo: z.string().optional(), // "A" | "B" | "C"
    ano: z.string().optional(), // "I" | "II"
    color: z.string().optional(), // "Verde" | "Blanco" | etc.
    semana: z.string().optional(), // "XVI Semana del Tiempo Ordinario"

    // Autor
    autor: z.string().default('padre-jose-miguel'),

    // Media
    imagen: z.string().optional(), // /img/dias/YYYY-MM-DD/evangelio.webp
    imagen_primera: z.string().optional(),
    imagen_segunda: z.string().optional(),
    audio_reflexion: z.string().optional(), // /audio/YYYY-MM-DD-reflexion.mp3
    audio_reflexion_duracion: z.string().optional(), // ISO 8601 "PT11M15S"
    youtube_id: z.string().optional(),

    // Primera lectura
    primera_lectura: z.object({
      referencia: z.string(),
      texto: z.string(),
    }),

    // Salmo responsorial
    salmo: z.object({
      referencia: z.string(),
      estribillo: z.string().optional(),
      versiculos: z.array(
        z.object({
          tipo: z.enum(['R', 'normal']),
          texto: z.string(),
        })
      ).default([]),
    }),

    // Aclamación antes del evangelio (misma estructura que el salmo: R/normal)
    aclamacion: z.object({
      referencia: z.string().optional(),
      versiculos: z.array(
        z.object({
          tipo: z.enum(['R', 'normal']),
          texto: z.string(),
        })
      ).default([]),
    }),

    // Segunda lectura (solo domingos y solemnidades)
    segunda_lectura: z
      .object({
        referencia: z.string(),
        texto: z.string(),
      })
      .optional(),

    // Evangelio
    evangelio: z.object({
      referencia: z.string(),
      texto: z.string(),
    }),

    // Reflexión del Padre Jose Miguel
    reflexion: z.string(),
  }),
});

// Colección: Autores
const autor = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),
    rol: z.string().default('Sacerdote Católico'),
    avatar: z.string(),
    bio: z.string(),
    bio_corta: z.string().max(250),
    redes: z
      .object({
        youtube: z.string().url().optional(),
      })
      .optional(),
  }),
});

export const collections = { evangelio, autor };