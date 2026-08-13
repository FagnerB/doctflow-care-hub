// Formatação de exibição de telefone BR — diferente de PhoneInput.tsx, que
// aplica máscara enquanto o usuário digita. Aqui a entrada já vem pronta da
// API no formato E.164 (+55DDDNUMERO) e só precisamos formatar para leitura.
export function formatPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  // Remove o código do país (55) só quando ele realmente está presente —
  // um número de 10/11 dígitos já sem código de país não deve perder os 2
  // primeiros dígitos por engano.
  const local = digits.startsWith("55") && digits.length > 11 ? digits.slice(2) : digits;

  if (local.length === 11) {
    // Celular: DDD + 9 dígitos.
    return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  }
  if (local.length === 10) {
    // Fixo: DDD + 8 dígitos.
    return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  // Formato inesperado — devolve como veio em vez de exibir algo quebrado.
  return phone;
}

/** Mascara os últimos dígitos, para exibir em telas públicas sem expor o número inteiro. */
export function maskPhoneForPublic(phone: string): string {
  const formatted = formatPhone(phone);
  const digits = formatted.replace(/\D/g, "");
  if (digits.length < 6) return formatted;
  // (11) 9****-**00 — mantém DDD e os 2 últimos dígitos, esconde o resto.
  const ddd = digits.slice(0, 2);
  const primeiroDigitoCelular = digits.length === 11 ? digits[2] : "";
  const ultimosDois = digits.slice(-2);
  return primeiroDigitoCelular
    ? `(${ddd}) ${primeiroDigitoCelular}****-**${ultimosDois}`
    : `(${ddd}) ****-**${ultimosDois}`;
}
