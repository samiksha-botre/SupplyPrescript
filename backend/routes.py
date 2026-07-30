from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from pydantic import BaseModel

from .database import SessionLocal
from .models import Medicine

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/medicines")
def get_medicines(db: Session = Depends(get_db)):
    medicines = db.query(Medicine).all()
    return medicines

class MedicineCreate(BaseModel):
    name: str
    company: str
    price: str


@router.post("/medicines")
def create_medicine(medicine: MedicineCreate, db: Session = Depends(get_db)):
    new_medicine = Medicine(
        name=medicine.name,
        company=medicine.company,
        price=medicine.price
    )

    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)

    return new_medicine

@router.delete("/medicines/{medicine_id}")
def delete_medicine(medicine_id: int, db: Session = Depends(get_db)):
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if medicine is None:
        return {"message": "Medicine not found"}

    db.delete(medicine)
    db.commit()

    return {"message": "Medicine deleted successfully"}

@router.put("/medicines/{medicine_id}")
def update_medicine(
    medicine_id: int,
    medicine: MedicineCreate,
    db: Session = Depends(get_db)
):
    existing_medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if existing_medicine is None:
        return {"message": "Medicine not found"}

    existing_medicine.name = medicine.name
    existing_medicine.company = medicine.company
    existing_medicine.price = medicine.price

    db.commit()
    db.refresh(existing_medicine)

    return existing_medicine