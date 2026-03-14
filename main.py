from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import datetime

from database import SessionLocal, PatientRecord

app = FastAPI()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class PredictionRequest(BaseModel):
    name: str
    age: int
    gender: str
    sys_bp: int
    dia_bp: int
    cholesterol: int
    bmi: float
    diabetes: str
    hypertension: str

class PredictionResponse(BaseModel):
    id: str
    name: str
    risk_score: float
    status: str
    risk_factors: List[str]
    recommendations: List[str]
    timestamp: str

class Patient(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    risk_score: float
    status: str
    timestamp: str

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, db: Session = Depends(get_db)):
    risk_factors = []
    recommendations = []
    score = 15

    # Logic from main.js but server-side
    if request.sys_bp > 140 or request.dia_bp > 90:
        risk_factors.append(f"Elevated Blood Pressure: {request.sys_bp}/{request.dia_bp} mmHg")
        recommendations.append("Monitor BP daily. Restrict sodium intake and avoid stress.")
        score += 35
    
    if request.cholesterol > 240:
        risk_factors.append(f"High Cholesterol Level: {request.cholesterol} mg/dL")
        recommendations.append("Adopt a low saturated-fat diet. Consult a physician for statin evaluation.")
        score += 25
    
    if request.bmi >= 30:
        risk_factors.append(f"BMI of {request.bmi} indicates clinical obesity")
        recommendations.append("Engage in regular cardiovascular exercise. Seek dietary planning.")
        score += 15
    
    if request.diabetes == "Yes":
        risk_factors.append("Existing Diabetes history")
        score += 10
    
    if request.hypertension == "Yes":
        risk_factors.append("Existing Hypertension history")
        score += 10

    score = min(score, 98)
    status = "High Risk" if score >= 60 else "Stable"
    
    # Save the record
    record_id = str(uuid.uuid4())
    db_record = PatientRecord(
        id=record_id,
        name=request.name,
        age=request.age,
        gender=request.gender,
        sys_bp=request.sys_bp,
        dia_bp=request.dia_bp,
        cholesterol=request.cholesterol,
        bmi=request.bmi,
        diabetes=request.diabetes,
        hypertension=request.hypertension,
        risk_score=score,
        status=status,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return PredictionResponse(
        id=record_id,
        name=request.name,
        risk_score=score,
        status=status,
        risk_factors=risk_factors,
        recommendations=recommendations,
        timestamp=db_record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    )

@app.get("/patients", response_model=List[Patient])
def get_patients(db: Session = Depends(get_db)):
    records = db.query(PatientRecord).order_by(PatientRecord.timestamp.desc()).all()
    return [
        Patient(
            id=r.id,
            name=r.name,
            age=r.age,
            gender=r.gender,
            risk_score=r.risk_score,
            status=r.status,
            timestamp=r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ) for r in records
    ]

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    record = db.query(PatientRecord).filter(PatientRecord.id == patient_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Patient not found")
    return record

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
