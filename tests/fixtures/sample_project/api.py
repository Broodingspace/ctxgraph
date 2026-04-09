"""API handler functions for the sample project.

These are the outermost layer — they receive requests, delegate to services,
and return responses. They depend on services but not on db or auth directly.
"""

from .auth import AuthError, TokenStore
from .db import DatabaseError, get_default_connection
from .models import Product, User
from .services import ProductService, UserService


# Module-level service instances (in a real app, use DI)
_connection = get_default_connection()
_user_service = UserService(_connection)
_product_service = ProductService(_connection)


def create_user(name: str, password: str) -> dict:
    """Handle user creation request.

    Args:
        name: User display name.
        password: Plain-text password.

    Returns:
        Response dict with created user data or error.
    """
    try:
        user = _user_service.create_user(name, password)
        return {"ok": True, "user": {"id": user.id, "name": user.name}}
    except DatabaseError as exc:
        return {"ok": False, "error": str(exc)}


def login(user_id: int, password: str) -> dict:
    """Handle login request.

    Args:
        user_id: User ID.
        password: Plain-text password.

    Returns:
        Response dict with session token or error.
    """
    try:
        token = _user_service.login(user_id, password)
        return {"ok": True, "token": token}
    except AuthError as exc:
        return {"ok": False, "error": str(exc)}
    except DatabaseError as exc:
        return {"ok": False, "error": str(exc)}


def get_user(user_id: int) -> dict:
    """Handle get-user request.

    Args:
        user_id: User ID to retrieve.

    Returns:
        Response dict with display name or error.
    """
    display = _user_service.get_display(user_id)
    return {"ok": True, "display_name": display}


def create_product(title: str, price: float) -> dict:
    """Handle product creation request.

    Args:
        title: Product title.
        price: Product price.

    Returns:
        Response dict with created product data or error.
    """
    try:
        product = _product_service.create_product(title, price)
        return {"ok": True, "product": {"id": product.id, "title": product.title}}
    except DatabaseError as exc:
        return {"ok": False, "error": str(exc)}


def get_product(product_id: int) -> dict:
    """Handle get-product request.

    Args:
        product_id: Product ID to retrieve.

    Returns:
        Response dict with product data or error.
    """
    product = _product_service.get_product(product_id)
    if product is None:
        return {"ok": False, "error": "Product not found"}
    return {"ok": True, "product": {"id": product.id, "title": product.title, "price": product.price}}
