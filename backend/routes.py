from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, cast, Integer, func
from pydantic import BaseModel, Field 

from .database import SessionLocal
from .models import Medicine

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MedicineCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    company: str = Field(..., min_length=2, max_length=100)
    price: str = Field(..., min_length=1)

class MedicineResponse(BaseModel):
    id: int
    name: str
    company: str
    price: str

    class Config:
        from_attributes = True

@router.get("/medicines", response_model=list[MedicineResponse])
def get_medicines(
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    db: Session = Depends(get_db)
):
    query = db.query(Medicine)

    if sort_by == "name":
        query = query.order_by(asc(Medicine.name) if order == "asc" else desc(Medicine.name))
    elif sort_by == "company":
        query = query.order_by(asc(Medicine.company) if order == "asc" else desc(Medicine.company))
    elif sort_by == "price":
        query = query.order_by(asc(Medicine.price) if order == "asc" else desc(Medicine.price))
    else:
        query = query.order_by(asc(Medicine.id) if order == "asc" else desc(Medicine.id))

    medicines = query.offset(skip).limit(limit).all()
    return medicines




@router.post("/medicines", response_model=MedicineResponse)
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
        raise HTTPException(
            status_code=404,
            detail="Medicine not found")

    db.delete(medicine)
    db.commit()

    return {"message": "Medicine deleted successfully"}


@router.put("/medicines/{medicine_id}", response_model=MedicineResponse)
def update_medicine(
    medicine_id: int,
    medicine: MedicineCreate,
    db: Session = Depends(get_db)
):
    existing_medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if existing_medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")

    existing_medicine.name = medicine.name
    existing_medicine.company = medicine.company
    existing_medicine.price = medicine.price

    db.commit()
    db.refresh(existing_medicine)

    return existing_medicine

@router.get("/medicines/search")
def search_medicine(
    name: str,
    db: Session = Depends(get_db)
):
    medicine = db.query(Medicine).filter(Medicine.name.ilike(f"%{name}%")).all()

    if not medicine:
       raise HTTPException(
          status_code=404,
          detail="Medicine not found"
        )

    return medicine

@router.get("/medicines/company/{company_name}")
def get_medicines_by_company(
    company_name: str,
    db: Session = Depends(get_db)
):
    medicines = db.query(Medicine).filter(
        Medicine.company == company_name
    ).all()

    if not medicines:
        raise HTTPException(
            status_code=404,
            detail="No medicines found for this company"
        )

    return medicines

@router.get("/medicines/price")
def get_medicines_by_price(
    min_price: int,
    max_price: int,
    db: Session = Depends(get_db)
):
    medicines = db.query(Medicine).filter(
        cast(Medicine.price, Integer) >= min_price,
        cast(Medicine.price, Integer) <= max_price
    ).all()

    if not medicines:
        raise HTTPException(
            status_code=404,
            detail="No medicines found in this price range"
        )

    return medicines

@router.get("/medicines/count")
def get_medicine_count(
    db: Session = Depends(get_db)
):
    total = db.query(func.count(Medicine.id)).scalar()

    return {
        "total_medicines": total
    }


@router.get("/medicines/{medicine_id}", response_model=MedicineResponse)
def get_medicine_by_id(
    medicine_id: int,
    db: Session = Depends(get_db)
):
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    return medicine

