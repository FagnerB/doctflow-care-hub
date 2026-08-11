// Cliente HTTP central da API do DoctFlow. Todos os módulos de domínio
// (src/lib/api.ts) passam por aqui — é o único lugar que sabe montar a URL,
// anexar o JWT e tratar erro/retry.
import type { ApiErrorBody } from "./api-types";
import { getAccessToken } from "./auth-storage";

// Preenchida via variável de ambiente VITE_API_URL (injetada pelo Vite em
// build/dev). Sem ela, cai no backend local — útil para rodar `uvicorn` +
// `vite dev` lado a lado sem configurar nada.
const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(message: string, status: number, code: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** Mensagem amigável para exibir em toast, a partir de qualquer erro capturado. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Erro inesperado. Tente novamente.";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | undefined | null>;
  /** Anexa o JWT salvo localmente. Default true — os endpoints públicos simplesmente o ignoram. */
  auth?: boolean;
}

const MAX_RETRIES_ON_RATE_LIMIT = 2;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function performFetch(url: string, method: string, headers: HeadersInit, body: unknown): Promise<Response> {
  return fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/**
 * Faz a chamada HTTP e devolve o corpo já tipado.
 *
 * Em erro 429 (rate limit), tenta novamente com backoff — respeitando o
 * header `Retry-After` quando presente, senão 1s / 2s. No máximo 2 tentativas
 * extras: o rate limit é intencional (proteção anti-abuso), então insistir
 * demais devolveria o mesmo 429 e só atrasaria o feedback ao usuário.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, auth = true } = options;
  const url = buildUrl(path, query);

  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (auth) {
    const token = getAccessToken();
    if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  let attempt = 0;
  let lastResponse: Response;
  while (true) {
    lastResponse = await performFetch(url, method, headers, body);

    if (lastResponse.status === 429 && attempt < MAX_RETRIES_ON_RATE_LIMIT) {
      const retryAfterHeader = lastResponse.headers.get("Retry-After");
      const retryAfterSeconds = retryAfterHeader ? Number(retryAfterHeader) : NaN;
      const waitMs = Number.isFinite(retryAfterSeconds) ? retryAfterSeconds * 1000 : 2 ** attempt * 1000;
      await sleep(waitMs);
      attempt += 1;
      continue;
    }
    break;
  }

  if (lastResponse.status === 204) return undefined as T;

  const text = await lastResponse.text();
  const data = text ? (JSON.parse(text) as unknown) : undefined;

  if (!lastResponse.ok) {
    const errorBody = data as Partial<ApiErrorBody> | undefined;
    throw new ApiError(
      errorBody?.error ?? "Erro inesperado. Tente novamente.",
      lastResponse.status,
      errorBody?.code ?? "unknown_error",
      errorBody?.details,
    );
  }

  return data as T;
}

export const apiGet = <T>(path: string, query?: RequestOptions["query"], auth?: boolean) =>
  apiRequest<T>(path, { method: "GET", query, auth });

export const apiPost = <T>(path: string, body?: unknown, auth?: boolean) =>
  apiRequest<T>(path, { method: "POST", body, auth });

export const apiPut = <T>(path: string, body?: unknown, auth?: boolean) =>
  apiRequest<T>(path, { method: "PUT", body, auth });

export const apiDelete = <T>(path: string, auth?: boolean) => apiRequest<T>(path, { method: "DELETE", auth });
