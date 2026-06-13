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


class TicketNotFound(DomainException):
    def __init__(self, message="Ticket not found"):
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class TicketNotInReview(DomainException):
    def __init__(self, message="Ticket is not in review status"):
        super().__init__(code="INVALID_STATUS", message=message, status_code=409)


class TicketHardBlocked(DomainException):
    def __init__(self, message="Ticket is permanently blocked"):
        super().__init__(code="HARD_BLOCKED", message=message, status_code=409)


class NotAssignedToModerator(DomainException):
    def __init__(self, message="This ticket is not assigned to you"):
        super().__init__(code="NOT_ASSIGNED", message=message, status_code=403)


class TicketHasNoSKUs(DomainException):
    def __init__(self, message="Product has no SKUs, cannot approve"):
        super().__init__(code="NO_SKUS", message=message, status_code=409)


class B2BServiceUnavailable(DomainException):
    def __init__(self, message="B2B service unavailable"):
        super().__init__(code="SERVICE_UNAVAILABLE", message=message, status_code=500)
