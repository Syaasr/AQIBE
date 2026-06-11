from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
import requests
from datetime import datetime, timedelta

app = FastAPI(
    title="AQI Prediction API",
    description="API Backend untuk memprediksi Kualitas Udara (AQI) Jakarta",
    version="1.0"
)

# --- KONFIGURASI CORS ---
# Sesuaikan origins dengan URL frontend Anda (misal Vercel)
origins = [
    "http://localhost:3000",                  # Untuk testing Next.js lokal
    "https://nama-proyekmu.vercel.app",       # Ganti dengan URL Vercel asli Anda
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

# --- SKEMA DATA UNTUK INPUT MANUAL ---
class PrediksiManualInput(BaseModel):
    AQI: float
    temperature_2m_mean: float
    precipitation_sum: float
    wind_speed_10m_mean: float
    relative_humidity_2m_mean: float
    surface_pressure_mean: float
    cloud_cover_mean: float
    shortwave_radiation_sum: float

# --- FUNGSI AMBIL DATA DARI OPEN-METEO ---
def tarik_data_cuaca_dan_aqi(tanggal_str: str):
    try:
        tgl_target = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
        tgl_hari_ini = datetime.today().date()
        
        if tgl_target < tgl_hari_ini:
            base_url_cuaca = "https://archive-api.open-meteo.com/v1/archive"
        else:
            base_url_cuaca = "https://api.open-meteo.com/v1/forecast"
            
        url_cuaca = f"{base_url_cuaca}?latitude=-6.1818&longitude=106.8223&daily=temperature_2m_mean,precipitation_sum,wind_speed_10m_mean,shortwave_radiation_sum,relative_humidity_2m_mean,surface_pressure_mean,cloud_cover_mean&timezone=auto&start_date={tanggal_str}&end_date={tanggal_str}"
        url_aqi = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude=-6.1818&longitude=106.8223&hourly=us_aqi&timezone=auto&start_date={tanggal_str}&end_date={tanggal_str}"
        
        res_cuaca = requests.get(url_cuaca).json()
        res_aqi = requests.get(url_aqi).json()
        
        daily = res_cuaca.get('daily', {})
        
        aqi_hourly = res_aqi.get('hourly', {}).get('us_aqi', [])
        aqi_valid = [x for x in aqi_hourly if x is not None]
        aqi_mean = sum(aqi_valid)/len(aqi_valid) if aqi_valid else None
        
        def get_val(key):
            val_list = daily.get(key)
            if not val_list or val_list[0] is None:
                return None
            return float(val_list[0])

        data_gabungan = {
            'AQI': aqi_mean,
            'temperature_2m_mean': get_val('temperature_2m_mean'),
            'precipitation_sum': get_val('precipitation_sum'),
            'wind_speed_10m_mean': get_val('wind_speed_10m_mean'),
            'relative_humidity_2m_mean': get_val('relative_humidity_2m_mean'),
            'surface_pressure_mean': get_val('surface_pressure_mean'),
            'cloud_cover_mean': get_val('cloud_cover_mean'),
            'shortwave_radiation_sum': get_val('shortwave_radiation_sum')
        }
        return data_gabungan
    except Exception as e:
        return None

def lakukan_prediksi(data_dict: dict):
    kolom_wajib = scaler.feature_names_in_
    df_input = pd.DataFrame(columns=kolom_wajib)
    
    row_data = {}
    for col in kolom_wajib:
        row_data[col] = data_dict.get(col)
        
    df_input.loc[0] = row_data
    data_scaled = scaler.transform(df_input)
    df_scaled = pd.DataFrame(data_scaled, columns=kolom_wajib)
    
    prediksi = model.predict(df_scaled)[0]
    return float(prediksi)

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "success", "message": "AQI Predictor API is running!"}

@app.get("/api/predict/auto")
def prediksi_auto():
    """Mengambil data hari ini secara otomatis dari satelit lalu memprediksi untuk besok."""
    hari_ini = datetime.today().strftime('%Y-%m-%d')
    data_hari_ini = tarik_data_cuaca_dan_aqi(hari_ini)
    
    if not data_hari_ini:
        raise HTTPException(status_code=500, detail="Gagal menghubungi API cuaca satelit.")
        
    # Cek kelengkapan
    for key, value in data_hari_ini.items():
        if value is None:
            raise HTTPException(status_code=400, detail=f"Data satelit belum lengkap untuk parameter: {key}")
            
    hasil_prediksi = lakukan_prediksi(data_hari_ini)
    return {
        "status": "success",
        "tanggal_acuan": hari_ini,
        "tanggal_prediksi": (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        "data_cuaca_acuan": data_hari_ini,
        "prediksi_aqi": hasil_prediksi
    }

@app.get("/api/predict/date/{tanggal}")
def prediksi_tanggal(tanggal: str):
    """Memprediksi AQI H+1 berdasarkan tanggal acuan tertentu (format: YYYY-MM-DD)."""
    try:
        datetime.strptime(tanggal, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid. Gunakan YYYY-MM-DD.")
        
    data_tgl = tarik_data_cuaca_dan_aqi(tanggal)
    if not data_tgl:
        raise HTTPException(status_code=500, detail="Gagal mengambil data dari satelit untuk tanggal tersebut.")
        
    for key, value in data_tgl.items():
        if value is None:
            raise HTTPException(status_code=400, detail=f"Data satelit tidak lengkap untuk parameter: {key}")
            
    hasil_prediksi = lakukan_prediksi(data_tgl)
    tgl_besok = (datetime.strptime(tanggal, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    return {
        "status": "success",
        "tanggal_acuan": tanggal,
        "tanggal_prediksi": tgl_besok,
        "data_cuaca_acuan": data_tgl,
        "prediksi_aqi": hasil_prediksi
    }

@app.post("/api/predict/manual")
def prediksi_manual(input_data: PrediksiManualInput):
    """Menerima parameter cuaca input manual dari frontend untuk diprediksi."""
    data_dict = input_data.dict()
    hasil_prediksi = lakukan_prediksi(data_dict)
    return {
        "status": "success",
        "prediksi_aqi": hasil_prediksi
    }