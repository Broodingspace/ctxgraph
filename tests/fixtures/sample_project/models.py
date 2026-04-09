"""Data models for the sample project."""

from .utils import UtilityClass


class BaseModel:
    """Base model class."""

    def __init__(self, id: int) -> None:
        """Initialize base model.

        Args:
            id: Model ID.
        """
        self.id = id

    def save(self) -> None:
        """Save the model."""
        pass


class User(BaseModel):
    """User model."""

    def __init__(self, id: int, name: str) -> None:
        """Initialize user.

        Args:
            id: User ID.
            name: User name.
        """
        super().__init__(id)
        self.name = name

    def get_display_name(self) -> str:
        """Get display name.

        Returns:
            Display name.
        """
        return f"User<{self.id}>: {self.name}"


class Product(BaseModel):
    """Product model."""

    def __init__(self, id: int, title: str, price: float) -> None:
        """Initialize product.

        Args:
            id: Product ID.
            title: Product title.
            price: Product price.
        """
        super().__init__(id)
        self.title = title
        self.price = price
