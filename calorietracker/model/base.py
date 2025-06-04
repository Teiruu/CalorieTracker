from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Base class for all ORM models, providing a consistent declarative foundation.
    """
    pass

# Initialize SQLAlchemy, using our custom Declarative Base
db = SQLAlchemy(model_class=Base)