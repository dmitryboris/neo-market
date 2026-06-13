from shared.exceptions import DomainException


class ModeratorNotFound(DomainException):
    def __init__(self, message="Moderator not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class EmailAlreadyExists(DomainException):
    def __init__(self, message="Email already registered"):
        super().__init__(code="EMAIL_EXISTS", message=message, status_code=409)


class Forbidden(DomainException):
    def __init__(self, message="Forbidden"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)
