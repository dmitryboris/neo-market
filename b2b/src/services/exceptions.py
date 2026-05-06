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