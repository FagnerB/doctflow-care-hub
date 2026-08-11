// Armazenamento do JWT da API (não é o token do Supabase — é o par emitido
// por POST /auth/login). Todo acesso é guardado por `typeof window` porque
// este app roda com SSR (TanStack Start): no servidor não existe localStorage.

const ACCESS_TOKEN_KEY = "doctflow.access_token";
const REFRESH_TOKEN_KEY = "doctflow.refresh_token";

export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function hasAccessToken(): boolean {
  return !!getAccessToken();
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Extrai um token de recuperação de senha (do Supabase) da URL atual.
 *
 * O link do e-mail chega em um destes dois formatos, dependendo da
 * configuração do projeto Supabase:
 * - fragmento: `/reset-password#access_token=...&type=recovery`
 * - query string: `/reset-password?token_hash=...&type=recovery`
 *
 * Só deve ser chamada dentro de um efeito (client-side) — no servidor
 * `window.location` não existe.
 */
export function parseRecoveryTokenFromLocation(): {
  accessToken?: string;
  tokenHash?: string;
  type: string;
} | null {
  if (!isBrowser()) return null;

  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const hashParams = new URLSearchParams(hash);
  const searchParams = new URLSearchParams(window.location.search);

  const accessToken = hashParams.get("access_token") ?? undefined;
  const tokenHash = searchParams.get("token_hash") ?? undefined;
  const type = hashParams.get("type") ?? searchParams.get("type") ?? "recovery";

  if (!accessToken && !tokenHash) return null;
  return { accessToken, tokenHash, type };
}

/** Decodifica (sem verificar assinatura) o payload de um JWT só para leitura de claims não sensíveis. */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(normalized)
        .split("")
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join(""),
    );
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}
