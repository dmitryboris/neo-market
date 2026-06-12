class DomainException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class TokenInvalid(DomainException):
    def __init__(self, code: str = "INVALID_TOKEN", message: str = "Invalid token", status_code: int = 401):
        super().__init__(code=code, message=message, status_code=status_code)


class TokenExpired(DomainException):
    def __init__(self, code: str = "TOKEN_EXPIRED", message: str = "Token has expired", status_code: int = 401):
        super().__init__(code=code, message=message, status_code=status_code)


class TokenRevoked(DomainException):
    def __init__(self, code: str = "TOKEN_REVOKED", message: str = "Token has been revoked", status_code: int = 401):
        super().__init__(code=code, message=message, status_code=status_code)


class InvalidCredentials(DomainException):
    def __init__(self, code: str = "INVALID_CREDENTIALS", message: str = "Invalid email or password",
                 status_code: int = 401):
        super().__init__(code=code, message=message, status_code=status_code)


class UserBlocked(DomainException):
    def __init__(self, code: str = "USER_BLOCKED", message: str = "User is blocked", status_code: int = 403):
        super().__init__(code=code, message=message, status_code=status_code)


class EmailAlreadyExists(DomainException):
    def __init__(self, code: str = "EMAIL_ALREADY_EXISTS", message: str = "Email already registered",
                 status_code: int = 409):
        super().__init__(code=code, message=message, status_code=status_code)


class Forbidden(DomainException):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Forbidden", status_code: int = 403):
        super().__init__(code=code, message=message, status_code=status_code)
        