from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd

app = FastAPI(
    title="AQI Prediction API",
    description="API Backend Stateless untuk menghitung prediksi Kualitas Udara (AQI) Jakarta",
    version="2.0"
)

# --- KONFIGURASI CORS ---
# Sesuaikan origins dengan URL frontend Anda (misal Vercel)
origins = [
    "http://localhost:3000",                  # Untuk testing Next.js lokal
    "https://jakarta-aqi.vercel.app",       # Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOAD MODEL DAN SCALER ---
try:
    model = joblib.load('mlr_aqi_model.pkl')
    scaler = joblib.load('scaler_cuaca.pkl')
except Exception as e:
    raise RuntimeError(f"Gagal memuat model/scaler: {e}")

# --- SKEMA DATA MASUKAN DARI FRONTEND ---
class PrediksiInput(BaseModel):
    AQI: float
    temperature_2m_mean: float
    temperature_2m_min: float                  # Dipertahankan untuk keselarasan parameter
    precipitation_sum: float
    wind_speed_10m_mean: float
    relative_humidity_2m_mean: float
    surface_pressure_mean: float
    cloud_cover_mean: float
    shortwave_radiation_sum: float

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {
        "status": "success", 
        "message": "AQI Predictor calculation API is running!"
    }

@app.post("/api/predict")
def prediksi_aqi(input_data: PrediksiInput):
    """
    Menerima parameter cuaca hasil fetch dari frontend, 
    lalu menghitung dan mengembalikan hasil prediksi AQI.
    """
    data_dict = input_data.dict()
    kolom_wajib = scaler.feature_names_in_
    df_input = pd.DataFrame(columns=kolom_wajib)
    
    # Ekstrak kolom yang dibutuhkan model
    row_data = {}
    for col in kolom_wajib:
        row_data[col] = data_dict.get(col)
        
    df_input.loc[0] = row_data
    
    # Lakukan standarisasi menggunakan scaler
    data_scaled = scaler.transform(df_input)
    df_scaled = pd.DataFrame(data_scaled, columns=kolom_wajib)
    
    # Lakukan prediksi menggunakan model ML
    prediksi = model.predict(df_scaled)[0]
    
    return {
        "status": "success",
        "prediksi_aqi": float(prediksi)
    }