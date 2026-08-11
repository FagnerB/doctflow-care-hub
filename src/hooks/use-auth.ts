// Hooks de autenticação: login, usuário atual e logout.
// O token em si vive em localStorage (src/lib/auth-storage.ts) — o React
// Query só cacheia os dados que dependem dele (o usuário logado).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { authApi } from "@/lib/api";
import { clearTokens, hasAccessToken, isBrowser, setTokens } from "@/lib/auth-storage";

export const authKeys = {
  me: ["auth", "me"] as const,
};

/**
 * Usuário logado. `enabled` é limitado a `isBrowser()` para nunca disparar
 * durante o SSR (sem token no servidor) e a `hasAccessToken()` para não gerar
 * 401 desnecessário quando não há sessão.
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: authApi.me,
    enabled: isBrowser() && hasAccessToken(),
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.login(email, password),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token);
      queryClient.setQueryData(authKeys.me, { user: data.user });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return () => {
    clearTokens();
    queryClient.clear();
    navigate({ to: "/login" });
  };
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => authApi.forgotPassword(email),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: authApi.resetPassword,
  });
}
