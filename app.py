import streamlit as st
import pandas as pd
import joblib
import requests
from datetime import datetime, timedelta

from fastapi import FastAPI, BaseModel
from fastapi.middleware.cors import CORSMiddleware # Tambahkan import ini
import joblib
import pandas as pd

app = FastAPI()

# --- KONFIGURASI CORS ---
# Masukkan URL Vercel milikmu dan URL localhost untuk testing
origins = [
    "http://localhost:3000",                  # Untuk testing Next.js lokal
    "https://nama-proyekmu.vercel.app",       # Ubah dengan URL Vercel asli nanti
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # Mengizinkan frontend di atas untuk mengakses API
    allow_credentials=True,
    allow_methods=["*"],             # Mengizinkan semua jenis HTTP Request (POST, GET, dll)
    allow_headers=["*"],             # Mengizinkan semua HTTP Headers
)

# ==========================================
# 1. LOAD MODEL DAN SCALER
# ==========================================
@st.cache_resource
def load_components():
    model = joblib.load('mlr_aqi_model.pkl')
    scaler = joblib.load('scaler_cuaca.pkl')
    return model, scaler

model, scaler = load_components()

# ==========================================
# 2. FUNGSI PENARIKAN DATA API OPEN-METEO
# ==========================================
def tarik_data_cuaca_dan_aqi(tanggal_str):
    """Menarik cuaca dan AQI Jakarta secara dinamis (Forecast atau Archive)."""
    try:
        # Cek apakah tanggal yang dipilih adalah masa lalu atau masa depan
        tgl_target = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
        tgl_hari_ini = datetime.today().date()
        
        # Pisahkan jalur API berdasarkan tanggal
        if tgl_target < tgl_hari_ini:
            base_url_cuaca = "https://archive-api.open-meteo.com/v1/archive"
        else:
            base_url_cuaca = "https://api.open-meteo.com/v1/forecast"
            
        url_cuaca = f"{base_url_cuaca}?latitude=-6.1818&longitude=106.8223&daily=temperature_2m_mean,temperature_2m_min,precipitation_sum,wind_speed_10m_mean,shortwave_radiation_sum,relative_humidity_2m_mean,surface_pressure_mean,cloud_cover_mean&timezone=auto&start_date={tanggal_str}&end_date={tanggal_str}"
        url_aqi = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude=-6.1818&longitude=106.8223&hourly=us_aqi&timezone=auto&start_date={tanggal_str}&end_date={tanggal_str}"
        
        res_cuaca = requests.get(url_cuaca).json()
        res_aqi = requests.get(url_aqi).json()
        
        daily = res_cuaca.get('daily', {})
        
        # Ekstrak dan hitung rata-rata AQI harian
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
            'temperature_2m_min': get_val('temperature_2m_min'),
            'precipitation_sum': get_val('precipitation_sum'),
            'wind_speed_10m_mean': get_val('wind_speed_10m_mean'),
            'relative_humidity_2m_mean': get_val('relative_humidity_2m_mean'),
            'surface_pressure_mean': get_val('surface_pressure_mean'),
            'cloud_cover_mean': get_val('cloud_cover_mean'),
            'shortwave_radiation_sum': get_val('shortwave_radiation_sum')
        }
        return data_gabungan
    except Exception as e:
        st.error(f"Gagal menghubungi server satelit: {e}")
        return None

# ==========================================
# 3. FUNGSI PREDIKSI & VALIDASI
# ==========================================
def cek_kelengkapan_data(data_dict):
    """Mengecek apakah ada data yang None/Kosong dari API."""
    for key, value in data_dict.items():
        if value is None:
            return False, key
    return True, None

def lakukan_prediksi(data_dict):
    kolom_wajib = scaler.feature_names_in_
    df_input = pd.DataFrame(columns=kolom_wajib)
    
    row_data = {}
    for col in kolom_wajib:
        row_data[col] = data_dict.get(col)
        
    df_input.loc[0] = row_data
 
    data_scaled = scaler.transform(df_input)

    df_scaled = pd.DataFrame(data_scaled, columns=kolom_wajib)
    
    prediksi = model.predict(df_scaled)[0]
    return prediksi

def tampilkan_hasil(prediksi_aqi, besok_str):
    st.success(f"### 🎯 Estimasi Nilai AQI pada {besok_str}: **{prediksi_aqi:.2f}**")
    
    if prediksi_aqi <= 50:
        st.info("🟢 Kategori: Baik (Udara bersih dan sangat sehat!)")
    elif prediksi_aqi <= 100:
        st.warning("🟡 Kategori: Sedang (Kualitas udara dapat diterima. Aman untuk luar ruangan.)")
    elif prediksi_aqi <= 150:
        st.error("🟠 Kategori: Tidak Sehat untuk Kelompok Sensitif (Gunakan masker jika rentan.)")
    else:
        st.error("🔴 Kategori: Tidak Sehat (Hindari aktivitas berat di luar ruangan!)")


# ==========================================
# 4. PENGATURAN HALAMAN & SIDEBAR
# ==========================================
st.set_page_config(page_title="AQI JKT Predictor", page_icon="🏙️", layout="centered")

with st.sidebar:
    st.markdown("### 🏙️ Tentang Aplikasi")
    st.write("Sistem prediksi Kualitas Udara (AQI) Jakarta berbasis Machine Learning (Multiple Linear Regression).")

st.title("☁️ Prediksi Kualitas Udara Jakarta")

tab1, tab2, tab3 = st.tabs(["🚀 Prediksi Besok (Auto)", "🎛️ Input Parameter", "📅 Pilih Tanggal"])

# ==========================================
# TAB 1: PREDIKSI BESOK (DASHBOARD AWAL)
# ==========================================
with tab1:
    st.subheader("Prakiraan AQI Hari Esok Secara Otomatis")
    st.write("Sistem akan menarik data cuaca dan kondisi polusi hari ini, lalu menebak kualitas udara untuk besok.")
    
    if st.button("🔄 Tarik Data Sekarang & Prediksi Besok", type="primary"):
        with st.spinner('Menghubungi satelit Open-Meteo...'):
            hari_ini = datetime.today().strftime('%Y-%m-%d')
            besok = (datetime.today() + timedelta(days=1)).strftime('%d %B %Y')
            
            data_hari_ini = tarik_data_cuaca_dan_aqi(hari_ini)
            
            if data_hari_ini:
                data_lengkap, parameter_hilang = cek_kelengkapan_data(data_hari_ini)
                
                if not data_lengkap:
                    st.warning(f"⚠️ Prediksi dibatalkan! Satelit belum merilis data untuk parameter: **{parameter_hilang}**. Kami menolak memprediksi dengan data yang cacat agar hasil tidak melenceng.")
                else:
                    st.write(f"Data Hari Ini ({hari_ini}) berhasil diamankan!")
                    col1, col2, col3 = st.columns(3)
                    
                    col1.metric("Suhu Rata-rata", f"{data_hari_ini['temperature_2m_mean']} °C")
                    col2.metric("Curah Hujan", f"{data_hari_ini['precipitation_sum']} mm")
                    col3.metric("AQI Aktual Hari Ini", f"{data_hari_ini['AQI']:.1f}")
                    
                    hasil_prediksi = lakukan_prediksi(data_hari_ini)
                    st.divider()
                    tampilkan_hasil(hasil_prediksi, besok)

# ==========================================
# TAB 2: INPUT MANUAL
# ==========================================
with tab2:
    st.subheader("Eksperimen Prediksi Cuaca")
    st.write("Ubah-ubah angka di bawah ini untuk melihat bagaimana cuaca mempengaruhi polusi.")
    
    col1, col2 = st.columns(2)
    with col1:
        aqi_in = st.number_input("AQI Hari Ini", value=75.0)
        temp_mean_in = st.number_input("Suhu Rata-rata (°C)", value=28.5)
        temp_min_in = st.number_input("Suhu Minimum (°C)", value=24.0)
        precip_in = st.number_input("Curah Hujan (mm)", value=0.0)
    with col2:
        wind_in = st.number_input("Kec. Angin Rata-rata (km/h)", value=10.0)
        rh_in = st.number_input("Kelembaban (%)", value=75.0)
        press_in = st.number_input("Tekanan Udara (hPa)", value=1010.0)
        cloud_in = st.number_input("Tutupan Awan (%)", value=50.0)
        rad_in = st.number_input("Radiasi Matahari (W/m²)", value=15.0)

    if st.button("🔮 Prediksi Skenario Ini"):
        data_manual = {
            'AQI': aqi_in,
            'temperature_2m_mean': temp_mean_in,
            'temperature_2m_min': temp_min_in,
            'precipitation_sum': precip_in,
            'wind_speed_10m_mean': wind_in,
            'relative_humidity_2m_mean': rh_in,
            'surface_pressure_mean': press_in,
            'cloud_cover_mean': cloud_in,
            'shortwave_radiation_sum': rad_in
        }
        hasil = lakukan_prediksi(data_manual)
        tampilkan_hasil(hasil, "Keesokan Harinya")

# ==========================================
# TAB 3: PILIH TANGGAL TERTENTU
# ==========================================
with tab3:
    st.subheader("Cek Histori / Prakiraan Jarak Jauh")
    st.write("Pilih tanggal mana pun, kami akan menarik datanya dan menebak kondisi keesokan harinya.")
    
    tanggal_dipilih = st.date_input("Pilih Tanggal Acuan")
    tanggal_besoknya = (tanggal_dipilih + timedelta(days=1)).strftime('%d %B %Y')
    
    if st.button("🕰️ Mulai Prediksi H+1", key="btn_tgl"):
        with st.spinner(f"Mengambil rekaman data tanggal {tanggal_dipilih}..."):
            tgl_str = tanggal_dipilih.strftime('%Y-%m-%d')
            data_tgl = tarik_data_cuaca_dan_aqi(tgl_str)
            
            if data_tgl:
                data_lengkap, parameter_hilang = cek_kelengkapan_data(data_tgl)
                
                if not data_lengkap:
                    st.warning(f"⚠️ Prediksi dibatalkan! Satelit tidak memiliki rekaman lengkap untuk tanggal ini (Data hilang: **{parameter_hilang}**). Silakan pilih tanggal lain.")
                else:
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Suhu Rata-rata", f"{data_tgl['temperature_2m_mean']} °C")
                    col_b.metric("Curah Hujan", f"{data_tgl['precipitation_sum']} mm")
                    col_c.metric("AQI Acuan", f"{data_tgl['AQI']:.1f}")
                    
                    hasil_tgl = lakukan_prediksi(data_tgl)
                    st.divider()
                    tampilkan_hasil(hasil_tgl, tanggal_besoknya)