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