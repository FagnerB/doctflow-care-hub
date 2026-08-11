// Configuração central do TanStack Query.
//
// Existe por um motivo específico: tratar 401 de forma global. Sem isso, um
// token expirado faz cada tela reagir de um jeito diferente (spinner infinito,
// formulário vazio sem explicação) em vez de deslogar e mandar pro /login.
import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api-client";
import { clearTokens, hasAccessToken, isBrowser } from "./auth-storage";

function handlePossibleUnauthorized(error: unknown): void {
  if (!(error instanceof ApiError) || error.status !== 401) return;
  if (!isBrowser() || !hasAccessToken()) return;

  // Reload completo (não router.navigate): garante que todo o estado em
  // memória — cache do React Query, forms abertos — é descartado junto com
  // o token inválido, e a app reinicia do zero já deslogada.
  clearTokens();
  window.location.assign("/login");
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: handlePossibleUnauthorized,
    }),
    mutationCache: new MutationCache({
      onError: handlePossibleUnauthorized,
    }),
  });
}
