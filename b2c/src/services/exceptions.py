from shared.exceptions import DomainException


class CatalogUnavailable(DomainException):
    def __init__(self, code="SERVICE_UNAVAILABLE", message="B2B service unavailable", status_code=503):
        super().__init__(code=code, message=message, status_code=status_code)


class InvalidSort(DomainException):
    def __init__(self, allowed: list[str]):
        super().__init__(
            code="INVALID_REQUEST",
            message=f"Invalid sort parameter. Allowed: {', '.join(allowed)}",
            status_code=400,
        )

class ProductNotFound(DomainException):
    def __init__(self, message: str = "Product not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)