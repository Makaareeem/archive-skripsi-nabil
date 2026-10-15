# Deployment Runpod Serverless dan Cloudflare

Konfigurasi production untuk Question Answering Publikasi Statistik BPS. Backend RAG dan inferensi model berjalan pada Runpod Serverless, sedangkan Cloudflare Worker menyajikan frontend serta menjadi gateway menuju backend.

Alamat aplikasi: [qapublikasi.skripsi.uk](https://qapublikasi.skripsi.uk)

## Arsitektur

```text
Browser
   │
   ▼
Cloudflare DNS dan TLS
   │
   ▼
Cloudflare Worker
   ├─ pembatasan frekuensi permintaan
   ├─ penyajian frontend
   ├─ validasi origin dan rute
   └─ penyimpanan API key Runpod
   │
   ▼
Runpod Serverless
   ├─ FastAPI
   ├─ FAISS dan BM25
   ├─ embedding dan reranker
   └─ Ollama dan model GGUF
```

Laptop lokal tidak menjadi bagian dari jalur production. Runpod menggunakan penyimpanan persisten untuk model, indeks, dan cache agar aset tidak perlu diunduh pada setiap cold start.

## Struktur

| Lokasi | Kegunaan |
| --- | --- |
| `Dockerfile` | Image backend Runpod. |
| `assets.json` | Versi, ukuran, dan checksum aset model serta basis pengetahuan. |
| `runtime/` | Persiapan aset, Ollama, FastAPI, dan health server. |
| `runpod.env.example` | Konfigurasi runtime nonrahasia. |
| `gateway/` | Cloudflare Worker dan adaptor frontend. |
| `test_runtime.py` | Pengujian runtime dan konfigurasi kapasitas. |

Kode aplikasi tetap berasal dari folder `app/` dan `web/` pada root repository. Pipeline lokal dan production menggunakan implementasi RAG yang sama.

## Konfigurasi Runpod

| Pengaturan | Nilai deployment |
| --- | --- |
| Endpoint type | Load Balancer |
| Dockerfile | `deploy/runpod-demo/Dockerfile` |
| Build context | Root repository |
| HTTP ports | `8000`, `8081` |
| Health path | `/ping` |
| Active workers | `0` |
| Max workers | `1` |
| GPU per worker | `1` |
| Persistent storage | `/runpod-volume` |

Active worker `0` memungkinkan backend berhenti ketika tidak digunakan. Konfigurasi ini menekan biaya, tetapi permintaan pertama setelah worker berhenti mengalami cold start untuk menyalakan container dan memuat model.

## Aset model dan basis pengetahuan

`assets.json` mengunci repository, revisi, ukuran, dan SHA-256 setiap aset. Startup pertama mengunduh aset dari Hugging Face ke volume persisten. Startup berikutnya menggunakan file yang telah diverifikasi.

Aset yang dikelola meliputi:

- Llama 3.2 3B versi dasar dan fine-tuned;
- Gemma 2 2B versi dasar dan fine-tuned;
- indeks FAISS dan metadata chunk publikasi;
- model embedding Nomic Embed Text;
- model reranker bahasa Indonesia.

`HF_TOKEN` tersedia sebagai secret Runpod ketika repository aset memerlukan autentikasi. Token tidak disimpan dalam image atau repository.

## Kapasitas

Profil deployment menggunakan konfigurasi awal berikut:

```text
QUEUE_CONCURRENCY=3
MAX_QUEUE=4
OLLAMA_NUM_PARALLEL=1
QUEUE_WAIT_TIMEOUT=120
OLLAMA_TIMEOUT=180
```

Satu worker menerima maksimal tiga pipeline aktif dan empat permintaan menunggu. Inferensi Ollama tetap serial untuk menjaga penggunaan VRAM pada GPU 16 GB. Permintaan kedelapan ditolak ketika seluruh slot aktif dan antrean telah terisi.

Antrean berada dalam memori worker dan tidak dipertahankan ketika container berhenti. Kapasitas ini merupakan konfigurasi awal; perubahan GPU, model, jumlah worker, dan target waktu respons memerlukan pengujian beban ulang.

## Cloudflare Worker

Gateway Cloudflare berada di `gateway/` dan dibangun dari source frontend pada folder `web/`. Hasil build frontend tidak disimpan dalam Git.

Konfigurasi build Git:

| Pengaturan | Nilai |
| --- | --- |
| Root directory | `deploy/runpod-demo/gateway` |
| Build command | `npm run build` |
| Deploy command | `npx wrangler deploy` |
| Production branch | `main` |

Binding runtime:

| Nama | Jenis | Kegunaan |
| --- | --- | --- |
| `RUNPOD_ORIGIN` | Variable | Origin HTTPS endpoint Runpod. |
| `RUNPOD_API_KEY` | Secret | Autentikasi Cloudflare ke Runpod. |
| `ASK_RATE_LIMIT` | Rate limit binding | Maksimal lima permintaan jawaban per menit per alamat IP dalam satu lokasi Cloudflare. |
| `WAKE_RATE_LIMIT` | Rate limit binding | Maksimal 30 pemeriksaan kesiapan per menit per alamat IP dalam satu lokasi Cloudflare. |

Secret production disimpan pada Cloudflare dan tidak ditulis ke `wrangler.jsonc`, source frontend, atau riwayat Git.

## Health check

| Endpoint | Peran |
| --- | --- |
| `GET /ping` | Health check publik Runpod. |
| `GET /api/health` | Status backend, model, dan basis pengetahuan. |
| `GET /api/ready` | Readiness aplikasi FastAPI. |
| `GET /api/wake` | Aktivasi backend melalui gateway Cloudflare. |

Halaman awal tidak langsung membangunkan GPU. Backend mulai diaktifkan ketika pengguna mengirim pertanyaan.

## Keamanan

- API key Runpod hanya tersedia pada runtime Cloudflare Worker.
- Endpoint evaluasi tidak diteruskan melalui gateway publik.
- Gateway membatasi origin, metode HTTP, rute, ukuran request body, redirect, dan timeout.
- Respons error upstream diubah menjadi pesan publik tanpa rincian internal.
- Pembatalan dari browser diteruskan ke koneksi backend.
- Halaman dapat dibuka tanpa login; dua rate limit diterapkan sebelum permintaan diteruskan ke GPU.

Rate limit ini bersifat per lokasi Cloudflare dan tidak menjamin batas biaya global. Pantau penggunaan Runpod dan tambahkan perlindungan bot atau batas anggaran sesuai kebutuhan operasional.

## Pengujian

Runtime Runpod:

```bash
python -B -m unittest discover -s deploy/runpod-demo -p "test_*.py" -v
```

Gateway Cloudflare:

```bash
cd deploy/runpod-demo/gateway
npm install
npm test
```

Pengujian mencakup validasi aset, penyimpanan persisten, registrasi model, kapasitas antrean, akses publik dan rate limit gateway, pembatasan rute, streaming, pembatalan, dan penyaringan error upstream.
