class CategoryNotFound(Exception):
    pass

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
class ProductNotFound(Exception):
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