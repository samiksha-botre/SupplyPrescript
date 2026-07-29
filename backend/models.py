from sqlalchemy import Column, Integer, String
from .database import Base

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    company = Column(String(100))
    price = Column(String(20))