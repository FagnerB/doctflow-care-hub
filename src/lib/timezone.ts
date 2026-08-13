// O backend sempre serializa scheduled_at/start_time/end_time no fuso do
// consultório (America/Sao_Paulo, UTC-3), já com o offset explícito no ISO
// (ex.: "2026-08-20T09:00:00-03:00"). Se déssemos `new Date(iso)` direto para
// o date-fns `format`, o horário exibido dependeria do fuso do NAVEGADOR do
// paciente, não do consultório — violando a regra de negócio "horários no
// fuso de Brasília".
//
// A solução sem adicionar date-fns-tz: extraímos os componentes de data/hora
// já em wall-clock de Brasília (ignorando o offset, que sempre representa o
// mesmo fuso) e construímos um Date com o construtor LOCAL. Isso faz os
// getters locais (usados por `format`) devolverem exatamente esses números,
// em qualquer navegador — mas o Date resultante NÃO é o instante real, então
// ele serve só para exibição/agrupamento, nunca para enviar de volta à API.

const ISO_LOCAL_PATTERN = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/;

/** Data "de exibição" com os campos de wall-clock de Brasília, para usar com date-fns `format`. */
export function toBrasiliaDisplayDate(iso: string): Date {
  const match = ISO_LOCAL_PATTERN.exec(iso);
  if (!match) return new Date(iso);
  const [, year, month, day, hour, minute, second] = match.map(Number);
  return new Date(year, month - 1, day, hour, minute, second);
}

/**
 * Constrói um ISO com offset fixo de Brasília (-03:00) a partir de uma data
 * (só os campos de calendário são usados) e um horário "HH:mm" digitado
 * livremente — caso do agendamento manual, onde o horário não vem pronto de
 * um slot da API. Offset fixo é seguro aqui: o Brasil não usa mais horário de
 * verão desde 2019, então America/Sao_Paulo é sempre UTC-3.
 */
export function buildBrasiliaIso(date: Date, timeStr: string): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${timeStr}:00-03:00`;
}
