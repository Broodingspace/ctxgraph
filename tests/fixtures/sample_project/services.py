"""Service layer for the sample project.

Contains business logic that coordinates models, db, and auth.
"""

from .auth import AuthError, TokenStore, authenticate, hash_password
from .db import Connection, DatabaseError, Repository
from .models import BaseModel, Product, User
from .utils import UtilityClass, helper_function


class UserService:
    """Business logic for user management."""

    def __init__(self, connection: Connection) -> None:
        """Initialize user service.

        Args:
            connection: Database connection.
        """
        self.repo = Repository(connection)
        self.token_store = TokenStore()
        self._util = UtilityClass("user_service")

    def create_user(self, name: str, password: str) -> User:
        """Create a new user.

        Args:
            name: User display name.
            password: Plain-text password.

        Returns:
            Newly created User.

        Raises:
            DatabaseError: If persistence fails.
        """
        user_id = helper_function(len(name), 1)
        hashed, salt = hash_password(password)
        record = self.repo.save({"id": user_id, "name": name, "hash": hashed, "salt": salt})
        return User(id=record["id"], name=record["name"])

    def login(self, user_id: int, password: str) -> str:
        """Authenticate a user and return a session token.

        Args:
            user_id: User ID.
            password: Plain-text password.

        Returns:
            Session token.

        Raises:
            AuthError: If credentials are invalid.
            DatabaseError: If user cannot be found.
        """
        record = self.repo.find_by_id(user_id)
        if record is None:
            raise AuthError(f"User {user_id} not found")

        user = User(id=record["id"], name=record["name"])
        token = authenticate(user, password, record["hash"], record["salt"])
        self.token_store.store(token, user_id)
        return token

    def get_display(self, user_id: int) -> str:
        """Get display name for a user.

        Args:
            user_id: User ID.

        Returns:
            Formatted display name.
        """
        record = self.repo.find_by_id(user_id)
        if record is None:
            return "Unknown"
        user = User(id=record["id"], name=record["name"])
        return user.get_display_name()

    def process_value(self, value: int) -> int:
        """Apply utility processing to a value.

        Args:
            value: Integer value to process.

        Returns:
            Processed value.
        """
        return self._util.process(value)


class ProductService:
    """Business logic for product management."""

    def __init__(self, connection: Connection) -> None:
        """Initialize product service.

        Args:
            connection: Database connection.
        """
        self.repo = Repository(connection)

    def create_product(self, title: str, price: float) -> Product:
        """Create a new product.

        Args:
            title: Product title.
            price: Product price.

        Returns:
            Newly created Product.
        """
        product_id = helper_function(len(title), 100)
        record = self.repo.save({"id": product_id, "title": title, "price": price})
        return Product(id=record["id"], title=record["title"], price=record["price"])

    def get_product(self, product_id: int) -> Product | None:
        """Retrieve a product by ID.

        Args:
            product_id: Product ID.

        Returns:
            Product or None if not found.
        """
        record = self.repo.find_by_id(product_id)
        if record is None:
            return None
        return Product(id=record["id"], title=record["title"], price=record["price"])
