from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, cast, Integer, func
from pydantic import BaseModel, Field
from .security import hash_password, verify_password 
from .auth import create_access_token, verify_token, verify_admin

from .database import SessionLocal
from .models import Medicine, User

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
    quantity: int

class StockUpdate(BaseModel):
    quantity: int = Field(..., gt=0)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=255)
    role: str = "user"

class UserLogin(BaseModel):
    email: str
    password: str    

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True        

class MedicineResponse(BaseModel):
    id: int
    name: str
    company: str
    price: str
    quantity: int

    class Config:
        from_attributes = True

class MedicinesListResponse(BaseModel):
    success: bool
    message: str
    data: list[MedicineResponse]        

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: dict | list | None = None        

@router.get("/medicines", response_model=MedicinesListResponse)
def get_medicines(
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "id",
    order: str = "asc",
    current_user: str = Depends(verify_token),
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
    return {
        "success": True,
        "message": "Medicines fetched successfully",
        "data": medicines
}




@router.post("/medicines", response_model=ApiResponse)
def create_medicine(medicine: MedicineCreate, admin=Depends(verify_admin), db: Session = Depends(get_db)):

    existing_medicine = db.query(Medicine).filter(
    Medicine.name.ilike(medicine.name)
).first()

    if existing_medicine:
       raise HTTPException(
        status_code=400,
        detail="Medicine already exists"
    )
    new_medicine = Medicine(
        name=medicine.name,
        company=medicine.company,
        price=medicine.price,
        quantity=medicine.quantity
    )

    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)

    return {
    "success": True,
    "message": "Medicine created successfully",
    "data": {
        "id": new_medicine.id,
        "name": new_medicine.name,
        "company": new_medicine.company,
        "price": new_medicine.price,
        "quantity": new_medicine.quantity
    }
}

@router.delete("/medicines/{medicine_id}", response_model=ApiResponse)
def delete_medicine(medicine_id: int, current_user=Depends(verify_admin), db: Session = Depends(get_db)):
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found")

    db.delete(medicine)
    db.commit()

    return {
        "success": True,
        "message": "Medicine deleted successfully",
        "data": None
}


@router.put("/medicines/{medicine_id}", response_model=ApiResponse)
def update_medicine(
    medicine_id: int,
    medicine: MedicineCreate, current_user=Depends(verify_admin),
    db: Session = Depends(get_db)
):
    existing_medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()

    if existing_medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")

    existing_medicine.name = medicine.name
    existing_medicine.company = medicine.company
    existing_medicine.price = medicine.price
    existing_medicine.quantity=medicine.quantity

    db.commit()
    db.refresh(existing_medicine)

    return {
        "success": True,
        "message": "Medicine updated successfully",
        "data": {
           "id": existing_medicine.id,
           "name": existing_medicine.name,
           "company": existing_medicine.company,
           "price": existing_medicine.price,
           "quantity": existing_medicine.quantity
    }
}

@router.patch("/medicines/{medicine_id}/add-stock", response_model=ApiResponse)
def add_stock(
    medicine_id: int,
    stock: StockUpdate, current_user=Depends(verify_admin),
    db: Session = Depends(get_db)
):
    medicine = db.query(Medicine).filter(
    Medicine.id == medicine_id
).first()
    if medicine is None:
       raise HTTPException(
        status_code=404,
        detail="Medicine not found"
    )
    medicine.quantity += stock.quantity
    
    db.commit()
    db.refresh(medicine)

    return {
    "success": True,
    "message": "Stock added successfully",
    "data": {
        "id": medicine.id,
        "name": medicine.name,
        "company": medicine.company,
        "price": medicine.price,
        "quantity": medicine.quantity
    }
}

@router.get("/medicines/search", response_model=MedicinesListResponse)
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

    return {
        "success": True,
        "message": "Medicines found successfully",
        "data": medicine
}

@router.get("/medicines/company/{company_name}", response_model=MedicinesListResponse)
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

    return {
        "success": True,
        "message": "Medicines fetched successfully",
        "data": medicines
}

@router.get("/medicines/price", response_model=MedicinesListResponse)
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

    return {
        "success": True,
        "message": "Medicines fetched successfully",
        "data": medicines
}

@router.get("/medicines/count", response_model=MedicinesListResponse)
def get_medicine_count(
    db: Session = Depends(get_db)
):
    total = db.query(func.count(Medicine.id)).scalar()

    return {
        "success": True,
        "message": "Medicine count fetched successfully",
        "data":{
            "total_medicines": total
        }    
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

@router.post("/register", response_model=ApiResponse)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        (User.username == user.username) |
        (User.email == user.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    new_user = User(
    username=user.username,
    email=user.email,
    password=hash_password(user.password),
    role=user.role
)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "message": "User registered successfully",
        "data": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    }

@router.post("/login", response_model=ApiResponse)
def login_user(
    user: UserLogin,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, existing_user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )


    token = create_access_token(
    data={
        "sub": existing_user.email,
        "role": existing_user.role
    }
)
    

    return {
        "success": True,
        "message": "Login successful",
        "data": {
           "access_token": token,
           "token_type": "bearer",
           "user": {
               "id": existing_user.id,
               "username": existing_user.username,
               "email": existing_user.email
            }
        }
    }

@router.get("/dashboard/stats", response_model=ApiResponse)
def dashboard_stats(
    current_user=Depends(verify_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()

    total_admins = db.query(func.count(User.id)).filter(
        User.role == "admin"
    ).scalar()

    total_normal_users = db.query(func.count(User.id)).filter(
        User.role == "user"
    ).scalar()

    total_medicines = db.query(func.count(Medicine.id)).scalar()

    return {
        "success": True,
        "message": "Dashboard statistics fetched successfully",
        "data": {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_normal_users": total_normal_users,
            "total_medicines": total_medicines
        }
    }