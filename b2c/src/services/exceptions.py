from shared.exceptions import DomainException


class InvalidAuth(DomainException):
    def __init__(self, message="Either authentication or X-Session-Id required"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class InsufficientStock(DomainException):
    def __init__(self, message):
        super().__init__(code="INSUFFICIENT_STOCK", message=message, status_code=409)


class SkuNotFound(DomainException):
    def __init__(self, message):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class InvalidQuantity(DomainException):
    def __init__(self, message="Quantity must be positive"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class ItemNotFound(DomainException):
    def __init__(self, message="Item not found in cart"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)