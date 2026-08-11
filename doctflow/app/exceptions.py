class AppError(Exception):
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ValidationError(AppError):
    """Erro de regra de negócio na entrada — vira 400, não 500."""

    def __init__(self, message: str = "Dados inválidos", code: str = "validation_error") -> None:
        super().__init__(message, code=code, status_code=400)


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso não encontrado", code: str = "not_found") -> None:
        super().__init__(message, code=code, status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Não autorizado", code: str = "unauthorized") -> None:
        super().__init__(message, code=code, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Acesso negado", code: str = "forbidden") -> None:
        super().__init__(message, code=code, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflito de dados", code: str = "conflict") -> None:
        super().__init__(message, code=code, status_code=409)


class TooManyRequestsError(AppError):
    def __init__(self, message: str = "Muitas requisições", code: str = "rate_limited") -> None:
        super().__init__(message, code=code, status_code=429)
