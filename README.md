# ☁️ AQI Predictor API (Backend)

Repository ini berisi backend API untuk memprediksi Kualitas Udara (AQI - Air Quality Index) Jakarta menggunakan model Machine Learning (**Multiple Linear Regression**). Backend ini dibuat menggunakan **FastAPI** dan dirancang untuk dapat di-deploy dengan mudah di **Render.com**.

API ini mengintegrasikan data cuaca dinamis dari satelit **Open-Meteo API** (untuk histori dan ramalan cuaca) dan memprosesnya menggunakan model prediksi yang sudah dilatih.

---

## 🚀 Panduan Memulai Secara Lokal

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

## 📖 Dokumentasi API untuk Frontend Developer

* **Base URL (Local)**: `http://127.0.0.1:8000`
* **Base URL (Production)**: `https://<nama-aplikasi-anda>.onrender.com` (Ubah setelah dideploy di Render)

> [!NOTE]  
> API ini secara otomatis mengaktifkan Swagger UI untuk mempermudah testing langsung di browser. Anda bisa membukanya melalui path `/docs` (contoh: `http://127.0.0.1:8000/docs`).

### 1. Health Check
Endpoint sederhana untuk memverifikasi apakah server backend berjalan normal.

* **Method**: `GET`
* **Path**: `/`
* **Response Contoh (JSON)**:
  ```json
  {
    "status": "success",
    "message": "AQI Predictor API is running!"
  }
  ```

---

### 2. Prediksi Besok Otomatis (Auto Forecast)
Endpoint ini secara otomatis menarik data cuaca hari ini dari satelit dan memperkirakan indeks kualitas udara (AQI) untuk esok hari.

* **Method**: `GET`
* **Path**: `/api/predict/auto`
* **Response Contoh - Sukses (JSON)**:
  ```json
  {
    "status": "success",
    "tanggal_acuan": "2026-06-11",
    "tanggal_prediksi": "2026-06-12",
    "data_cuaca_acuan": {
      "AQI": 148.54,
      "temperature_2m_mean": 29.0,
      "precipitation_sum": 0.0,
      "wind_speed_10m_mean": 5.9,
      "relative_humidity_2m_mean": 67.0,
      "surface_pressure_mean": 1011.5,
      "cloud_cover_mean": 13.0,
      "shortwave_radiation_sum": 19.38
    },
    "prediksi_aqi": 140.38
  }
  ```
* **Response Contoh - Gagal/Error (JSON)**:
  ```json
  {
    "detail": "Data satelit belum lengkap untuk parameter: AQI"
  }
  ```

---

### 3. Prediksi Berdasarkan Tanggal Acuan
Endpoint ini memprediksi AQI untuk H+1 berdasarkan tanggal acuan tertentu yang Anda kirimkan.

* **Method**: `GET`
* **Path**: `/api/predict/date/{tanggal}`
  * Ganti `{tanggal}` dengan tanggal berformat `YYYY-MM-DD` (contoh: `/api/predict/date/2026-06-10`)
* **Response Contoh - Sukses (JSON)**:
  ```json
  {
    "status": "success",
    "tanggal_acuan": "2026-06-10",
    "tanggal_prediksi": "2026-06-11",
    "data_cuaca_acuan": {
      "AQI": 134.29,
      "temperature_2m_mean": 29.5,
      "precipitation_sum": 0.5,
      "wind_speed_10m_mean": 6.4,
      "relative_humidity_2m_mean": 63.0,
      "surface_pressure_mean": 1010.7,
      "cloud_cover_mean": 65.0,
      "shortwave_radiation_sum": 18.81
    },
    "prediksi_aqi": 125.38
  }
  ```

---

### 4. Prediksi Kustom (Manual Input)
Endpoint ini digunakan ketika user di frontend memasukkan angka parameter cuaca secara manual untuk melakukan simulasi skenario.

* **Method**: `POST`
* **Path**: `/api/predict/manual`
* **Headers**: `Content-Type: application/json`
* **Request Body (JSON)**:
  ```json
  {
    "AQI": 75.0,
    "temperature_2m_mean": 28.5,
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
    "prediksi_aqi": 125.38
  }
  ```

---

## 💻 Contoh Integrasi di Frontend (JavaScript/React/Next.js)

Berikut adalah contoh fungsi sederhana untuk memanggil API prediksi manual di frontend Anda menggunakan `fetch`:

```javascript
async function fetchAqiPrediction(dataManual) {
  const BACKEND_URL = "https://<nama-aplikasi-anda>.onrender.com/api/predict/manual";
  
  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(dataManual),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log("Hasil Prediksi:", data.prediksi_aqi);
    return data.prediksi_aqi;
  } catch (error) {
    console.error("Gagal melakukan prediksi:", error);
  }
}

// Cara Penggunaan:
const inputSkenario = {
  AQI: 85.0,
  temperature_2m_mean: 30.2,
  precipitation_sum: 1.2,
  wind_speed_10m_mean: 8.5,
  relative_humidity_2m_mean: 70.0,
  surface_pressure_mean: 1012.0,
  cloud_cover_mean: 40.0,
  shortwave_radiation_sum: 22.0
};

fetchAqiPrediction(inputSkenario);
```

---

## 🛠️ Konfigurasi CORS (Cross-Origin Resource Sharing)

Agar frontend Anda di Vercel atau localhost dapat mengakses backend ini tanpa masalah keamanan browser (CORS Error), pastikan Anda telah mendaftarkan URL frontend Anda pada variabel `origins` di file **[app.py](file:///mnt/data/UserFiles/Documents/KULIAH/TUGAS%20SEM%204/AI/AQIBE/app.py)** sebelum mem-push ke Render:

```python
origins = [
    "http://localhost:3000",                  # Next.js lokal
    "https://nama-proyekmu.vercel.app",       # Ganti dengan link Vercel Anda
]
```

---

## ☁️ Deployment di Render.com

Saat membuat Web Service baru di Render, gunakan konfigurasi berikut:
* **Environment/Runtime**: `Python`
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
