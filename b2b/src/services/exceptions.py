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