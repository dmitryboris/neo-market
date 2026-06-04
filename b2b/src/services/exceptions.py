class DomainException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


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


class SKUNotFound(Exception):
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
