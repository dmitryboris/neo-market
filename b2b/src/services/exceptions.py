from shared.exceptions import DomainException


class ProductTitleEmpty(DomainException):
    def __init__(self, message="title is required"):
        super().__init__(code="INVALID_REQUEST", message=message)


class ProductTitleInvalid(DomainException):
    def __init__(self, message="title must be 1-255 characters"):
        super().__init__(code="INVALID_REQUEST", message=message)


class CategoryNotFound(DomainException):
    def __init__(self, message="Category not found"):
        super().__init__(code="INVALID_REQUEST", message=message)


class ProductImageNotFound(DomainException):
    def __init__(self, message="At least one image is required"):
        super().__init__(code="INVALID_REQUEST", message=message)


class CategoryInvalid(DomainException):
    def __init__(self, message="category_id must be a valid UUID"):
        super().__init__(code="INVALID_REQUEST", message=message)


class ProductNotFound(DomainException):
    def __init__(self, message="Product not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class ProductHardBlocked(DomainException):
    def __init__(self, message="Cannot add SKU to hard-blocked product"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class SKUPriceInvalid(DomainException):
    def __init__(self, message="price must be a positive integer (kopecks)"):
        super().__init__(code="INVALID_REQUEST", message=message)


class SKUCostPriceInvalid(DomainException):
    def __init__(self, message="cost_price must be a positive integer (kopecks)"):
        super().__init__(code="INVALID_REQUEST", message=message)


class SKUNameEmpty(DomainException):
    def __init__(self, message="name is required"):
        super().__init__(code="INVALID_REQUEST", message=message)


class SKUNameInvalid(DomainException):
    def __init__(self, message="name must be 1-255 characters"):
        super().__init__(code="INVALID_REQUEST", message=message)


class SKUImageNotFound(DomainException):
    def __init__(self, message="image is required"):
        super().__init__(code="INVALID_REQUEST", message=message)


class UUIDInvalid(DomainException):
    def __init__(self, message="id must be a valid UUID"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class UnauthorizedServiceKey(DomainException):
    def __init__(self, message="Invalid service key"):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class UnauthorizedAccess(DomainException):
    def __init__(self, message="Not authenticated"):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class SKUNotFound(DomainException):
    def __init__(self, message="SKU not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class NotOwner(DomainException):
    def __init__(self, message: str = "Product does not belong to the authenticated seller"):
        super().__init__(code="NOT_OWNER", message=message, status_code=403)


class ProductAlreadyDeleted(DomainException):
    def __init__(self, message="Product already deleted"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class InvalidModerationEvent(DomainException):
    def __init__(self, message="Unknown event_type"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class IdempotencyKeyMissing(DomainException):
    def __init__(self, message="idempotency_key is required"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class ProductIdMissing(DomainException):
    def __init__(self, message="product_id is required"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class EventTypeMissing(DomainException):
    def __init__(self, message="event_type is required"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class OccurredAtMissing(DomainException):
    def __init__(self, message="occurred_at is required"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class BlockingReasonIdMissing(DomainException):
    def __init__(self, message="blocking_reason_id is required for BLOCKED event"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class FieldReportsMissing(DomainException):
    def __init__(self, message="field_reports is required for BLOCKED event"):
        super().__init__(code="INVALID_REQUEST", message=message, status_code=400)


class InsufficientStock(DomainException):
    def __init__(self, failed_items: list[dict]):
        super().__init__(code="INSUFFICIENT_STOCK", message="Insufficient stock for one or more SKUs",
                         status_code=409, details={"failed_items": failed_items}
                         )


class OutOfStock(DomainException):
    def __init__(self, failed_items: list[dict]):
        super().__init__(code="OUT_OF_STOCK", message="One or more SKUs are out of stock",
                         status_code=409, details={"failed_items": failed_items}
                         )


class SKUHasActiveReserves(DomainException):
    def __init__(self, message="Cannot delete SKU with active reserves"):
        super().__init__(code="CONFLICT", message=message, status_code=409)


class CategoryParentNotFound(Exception):
    pass


class CategorySelfParentError(Exception):
    pass


class CategoryHasProducts(Exception):
    pass


class CategoryHasChildren(Exception):
    pass


class InvoiceNotFound(Exception):
    pass


class InvoiceAccessDenied(Exception):
    pass


class ForbiddenOperation(Exception):
    pass


class InvoiceAlreadyAccepted(Exception):
    pass


class InvoiceCannotDeleteAccepted(Exception):
    pass


class SKUNotBelongsToSeller(Exception):
    pass


class DuplicateSKUInInvoice(Exception):
    pass


class ImageNotFound(Exception):
    pass


class AccessDenied(Exception):
    pass


class NoFieldsToUpdate(Exception):
    pass


class InvalidFileType(Exception):
    pass


class FileTooLarge(Exception):
    pass
