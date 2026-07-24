export const MESES_ES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
] as const;

export const MESES_ES_CAPITAL = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
] as const;

export const DIAS_SEMANA = [
  'domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado',
] as const;

export const DIAS_SEMANA_CAPITAL = [
  'Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado',
] as const;

export function formatFechaLegible(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${MESES_ES[m - 1]} ${y}`;
}

export function formatFechaLegibleDe(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} de ${MESES_ES[m - 1]} de ${y}`;
}

export function formatFechaCorta(iso: string): string {
  const [, m, d] = iso.split('-').map(Number);
  return `${d} ${MESES_ES[m - 1]}`;
}

export function getDiaSemana(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return DIAS_SEMANA_CAPITAL[date.getDay()];
}

export function getMonthSlug(monthNum: number): string {
  return MESES_ES[monthNum - 1];
}

export function getMonthFromSlug(slug: string): number | null {
  const idx = MESES_ES.indexOf(slug as typeof MESES_ES[number]);
  return idx >= 0 ? idx + 1 : null;
}

export function isDomingo(iso: string): boolean {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.getDay() === 0;
}