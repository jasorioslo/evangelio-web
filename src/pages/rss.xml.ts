import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getCollection } from 'astro:content';

export async function GET(context: APIContext) {
  const entries = (await getCollection('evangelio')).sort((a, b) =>
    a.id > b.id ? -1 : 1
  );

  return rss({
    title: 'Evangelio para Hoy — Evangelio diario con el Padre Jose Miguel',
    description: 'Las lecturas, el evangelio y la reflexión de cada día para acompañarte en tu camino de fe.',
    site: context.site ?? 'https://evangelioparahoy.com',
    items: entries.map((entry) => ({
      title: entry.data.title,
      description: entry.data.description,
      pubDate: new Date(entry.data.fecha),
      link: `/evangelio/${entry.slug}/`,
    })),
    customData: '<language>es-MX</language>',
  });
}