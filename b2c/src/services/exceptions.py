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


class CartInvalidException(DomainException):
    def __init__(self, cart_validation_response: dict):
        super().__init__(
            code="CART_INVALID",
            message="Cart is not valid",
            status_code=422,
            details=cart_validation_response
        )
        self.cart_validation = cart_validation_response


class CartMismatchException(DomainException):
    def __init__(self):
        super().__init__(
            code="CART_MISMATCH",
            message="Cart snapshot mismatch",
            status_code=409
        )


class ReserveFailed(DomainException):
    def __init__(self, failed_items: list[dict]):
        super().__init__(
            code="RESERVE_FAILED",
            message="Failed to reserve items",
            status_code=409,
            details={"failed_items": failed_items}
        )
        self.failed_items = failed_items


class B2BUnavailable(DomainException):
    def __init__(self):
        super().__init__(
            code="B2B_UNAVAILABLE",
            message="B2B service is unavailable",
            status_code=503
        )
        