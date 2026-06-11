# AQI Predictor API (Stateless Backend)

Repository ini berisi backend API untuk memprediksi Kualitas Udara (AQI - Air Quality Index) Jakarta menggunakan model Machine Learning (**Multiple Linear Regression**). 

Backend ini bersifat **stateless (tanpa menyimpan state / tidak melakukan koneksi luar)**. Semua tugas pemanggilan API satelit Open-Meteo dialihkan langsung ke **Frontend (Client-side)**. Backend hanya menerima parameter cuaca matang dari frontend, melakukan standarisasi data, menghitung prediksi menggunakan file model (`mlr_aqi_model.pkl` & `scaler_cuaca.pkl`), dan mengembalikan hasil estimasi AQI.

### Keuntungan Arsitektur Ini:
1. **Bebas Error SSL/Koneksi**: Server backend Anda di Render tidak akan pernah mengalami error koneksi satelit atau masalah verifikasi sertifikat SSL HTTPS.
2. **Terhindar dari Rate Limit**: Pemanggilan API Open-Meteo dilakukan dari browser masing-masing pengguna (IP client berbeda-beda), sehingga IP server backend Anda aman dari pemblokiran/rate-limiting.
3. **Sangat Cepat**: Proses kalkulasi lokal hanya memakan waktu milidetik.

---

## Panduan Memulai Secara Lokal

### Prasyarat
* Python 3.10 ke atas sudah terinstal di komputer Anda.

### Langkah Instalasi
1. Clone repository ini ke lokal Anda.
2. Buat Virtual Environment:
   ```bash
   python -m venv venv
   ```
3. Aktifkan Virtual Environment:
   * **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```
   * **Windows (Command Prompt)**:
     ```cmd
     venv\Scripts\activate
     ```
4. Instal dependensi:
   ```bash
   pip install -r requirements.txt
   ```
5. Jalankan server lokal:
   ```bash
   uvicorn app:app --reload --port 8000
   ```
   API sekarang dapat diakses secara lokal di `http://127.0.0.1:8000`.

---

## Dokumentasi API (Untuk Frontend)

* **Base URL (Local)**: `http://127.0.0.1:8000`
* **Base URL (Production)**: `https://aqibe.onrender.com`

### 1. Health Check
* **Method**: `GET`
* **Path**: `/`
* **Response Contoh**:
  ```json
  {
    "status": "success",
    "message": "AQI Predictor calculation API is running!"
  }
  ```

### 2. Hitung Prediksi (Calculate)
Menerima parameter cuaca lengkap dan mengembalikan perkiraan nilai AQI.

* **Method**: `POST`
* **Path**: `/api/predict`
* **Headers**: `Content-Type: application/json`
* **Request Body (JSON)**:
  ```json
  {
    "AQI": 75.0,
    "temperature_2m_mean": 28.5,
    "temperature_2m_min": 24.0,
    "precipitation_sum": 0.0,
    "wind_speed_10m_mean": 10.0,
    "relative_humidity_2m_mean": 75.0,
    "surface_pressure_mean": 1010.0,
    "cloud_cover_mean": 50.0,
    "shortwave_radiation_sum": 15.0
  }
  ```
* **Response Contoh (JSON)**:
  ```json
  {
    "status": "success",
    "prediksi_aqi": 75.70123085978858
  }
  ```

---

## Panduan Integrasi Lengkap untuk Frontend Developer

Sebagai Frontend Developer, Anda perlu melakukan dua langkah berikut di aplikasi web Anda (Next.js, React, Vue, atau Vanilla JS):

### Langkah 1: Ambil Data Cuaca & AQI dari Open-Meteo
Lakukan HTTP GET request langsung dari browser ke API Open-Meteo menggunakan koordinat Jakarta (`latitude=-6.1818`, `longitude=106.8223`).

Berikut adalah fungsi JavaScript siap pakai yang mengimplementasikan:
* Logika 30 Hari: Memakai **Forecast API** untuk tanggal baru (≤ 30 hari lalu) dan **Archive API** untuk tanggal lama.
* Menghitung rata-rata AQI harian dari data per-jam.
* Melakukan **imputasi (pengisian otomatis) nilai median** jika ada parameter yang bernilai kosong (`null`).

```javascript
// Nilai median/rata-rata default Jakarta untuk imputasi data kosong
const NILAI_IMPUTASI_DEFAULT = {
  AQI: 75.0,
  temperature_2m_mean: 28.5,
  temperature_2m_min: 24.0,
  precipitation_sum: 0.0,
  wind_speed_10m_mean: 10.0,
  relative_humidity_2m_mean: 75.0,
  surface_pressure_mean: 1010.0,
  cloud_cover_mean: 50.0,
  shortwave_radiation_sum: 15.0
};

async function dapatkanDataSatelit(tanggalStr) {
  const tglTarget = new Date(tanggalStr);
  const tglHariIni = new Date();
  
  // Set waktu ke jam 00:00 untuk perbandingan tanggal saja
  tglTarget.setHours(0,0,0,0);
  tglHariIni.setHours(0,0,0,0);
  
  // Selisih hari
  const selisihMilidetik = tglHariIni - tglTarget;
  const selisihHari = selisihMilidetik / (1000 * 60 * 60 * 24);
  
  // Pilih endpoint cuaca berdasarkan selisih hari (Forecast untuk <= 30 hari terakhir, selebihnya Archive)
  let baseUrlCuaca = "https://archive-api.open-meteo.com/v1/archive";
  if (selisihHari <= 30) {
    baseUrlCuaca = "https://api.open-meteo.com/v1/forecast";
  }
  
  const urlCuaca = `${baseUrlCuaca}?latitude=-6.1818&longitude=106.8223&daily=temperature_2m_mean,temperature_2m_min,precipitation_sum,wind_speed_10m_mean,shortwave_radiation_sum,relative_humidity_2m_mean,surface_pressure_mean,cloud_cover_mean&timezone=auto&start_date=${tanggalStr}&end_date=${tanggalStr}`;
  const urlAqi = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=-6.1818&longitude=106.8223&hourly=us_aqi&timezone=auto&start_date=${tanggalStr}&end_date=${tanggalStr}`;
  
  try {
    const [resCuaca, resAqi] = await Promise.all([
      fetch(urlCuaca).then(r => r.json()),
      fetch(urlAqi).then(r => r.json())
    ]);
    
    // 1. Olah data AQI (hitung rata-rata harian dari 24 jam)
    const aqiHourly = resAqi.hourly?.us_aqi || [];
    const aqiValid = aqiHourly.filter(val => val !== null && val !== undefined);
    const aqiMean = aqiValid.length > 0 
      ? aqiValid.reduce((sum, val) => sum + val, 0) / aqiValid.length 
      : NILAI_IMPUTASI_DEFAULT.AQI;
      
    // Helper untuk mengambil nilai harian atau memakai median jika null
    const daily = resCuaca.daily || {};
    const dapatkanNilaiHarian = (key) => {
      const listVal = daily[key];
      if (!listVal || listVal[0] === null || listVal[0] === undefined) {
        return NILAI_IMPUTASI_DEFAULT[key];
      }
      return parseFloat(listVal[0]);
    };
    
    // Susun objek parameter cuaca matang
    return {
      AQI: aqiMean,
      temperature_2m_mean: dapatkanNilaiHarian('temperature_2m_mean'),
      temperature_2m_min: dapatkanNilaiHarian('temperature_2m_min'),
      precipitation_sum: dapatkanNilaiHarian('precipitation_sum'),
      wind_speed_10m_mean: dapatkanNilaiHarian('wind_speed_10m_mean'),
      relative_humidity_2m_mean: dapatkanNilaiHarian('relative_humidity_2m_mean'),
      surface_pressure_mean: dapatkanNilaiHarian('surface_pressure_mean'),
      cloud_cover_mean: dapatkanNilaiHarian('cloud_cover_mean'),
      shortwave_radiation_sum: dapatkanNilaiHarian('shortwave_radiation_sum')
    };
  } catch (error) {
    console.warn("Gagal mengambil data satelit. Menggunakan nilai fallback default:", error);
    return { ...NILAI_IMPUTASI_DEFAULT };
  }
}
```

### Langkah 2: Kirim ke Backend untuk Prediksi
Kirim data cuaca matang hasil langkah 1 ke backend API Anda:

```javascript
async function prediksiAqiBesok(tanggalAcuan) {
  const BACKEND_URL = "https://aqibe.onrender.com/api/predict";
  
  // 1. Ambil data dari satelit Open-Meteo
  const dataCuaca = await dapatkanDataSatelit(tanggalAcuan);
  
  // 2. Kirim data ke backend FastAPI Anda
  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(dataCuaca),
    });
    
    const hasil = await response.json();
    console.log(`Prediksi AQI H+1 dari tanggal ${tanggalAcuan}:`, hasil.prediksi_aqi);
    return hasil.prediksi_aqi;
  } catch (error) {
    console.error("Gagal menghubungi server backend untuk kalkulasi prediksi:", error);
  }
}

// Contoh Pemanggilan: Prediksi esok hari dengan data hari ini (2026-06-11)
prediksiAqiBesok("2026-06-11");
```

---

## Konfigurasi CORS (Cross-Origin Resource Sharing)

Agar frontend dapat memanggil backend, daftarkan domain frontend Anda pada variabel `origins` di file **app.py sebelum mem-push ke Render:

```python
origins = [
    "http://localhost:3000",                  # Next.js lokal
    "https://jakarta-aqi.vercel.app",       # Ganti dengan domain Vercel Anda
]
```

---

## Deployment di Render.com

Gunakan pengaturan berikut di dashboard Render Anda:
* **Environment/Runtime**: `Python`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
