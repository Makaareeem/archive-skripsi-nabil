# Question Answering Publikasi Statistik BPS

Aplikasi web untuk menjawab pertanyaan berdasarkan publikasi statistik Badan Pusat Statistik (BPS). Sistem menerapkan Retrieval-Augmented Generation (RAG) dengan Small Language Model, pencarian hybrid, dan penyajian sumber agar jawaban dapat ditelusuri kembali ke publikasi asal.

Demo: [qapublikasi.skripsi.uk](https://qapublikasi.skripsi.uk)

## Fitur

- Pencarian hybrid menggunakan FAISS dan BM25.
- Penggabungan hasil dengan Reciprocal Rank Fusion (RRF).
- Reranking terhadap maksimal 20 kandidat dokumen.
- Perluasan pertanyaan dengan tetap mempertahankan pertanyaan asli.
- Jawaban berbasis maksimal lima sumber yang paling relevan.
- Sitasi, halaman publikasi, skor relevansi, tautan, dan cuplikan asli sumber.
- Streaming jawaban dan tampilan tahapan pemrosesan.
- Validasi pertanyaan, antrean terbatas, pembatalan, dan pesan kesalahan yang aman.
- Pilihan model Llama 3.2 3B dan Gemma 2 2B dalam versi dasar dan fine-tuned.
- API evaluasi terpisah untuk kebutuhan penelitian.

## Alur sistem

```text
Pertanyaan
   │
   ├─ Validasi dan antrean
   ├─ Perluasan pertanyaan
   ├─ Dense retrieval + BM25
   ├─ Reciprocal Rank Fusion
   ├─ Reranking 20 kandidat
   ├─ Pemilihan maksimal 5 sumber
   ├─ Generasi jawaban bersitasi
   └─ Pemeriksaan jawaban dan sumber
```

Pada lingkungan lokal, frontend, FastAPI, retrieval, dan Ollama berjalan pada satu komputer. Deployment menggunakan Cloudflare Worker sebagai gateway dan Runpod Serverless untuk menjalankan backend serta inferensi model.

```text
Browser → Cloudflare Worker → Runpod → FastAPI → RAG Pipeline → Ollama
```

## Struktur repository

| Lokasi | Kegunaan |
| --- | --- |
| `app/` | API FastAPI dan seluruh pipeline RAG. |
| `web/` | Antarmuka pengguna berbasis HTML, CSS, dan JavaScript. |
| `deploy/` | Konfigurasi Ollama, Docker Runpod, runtime, dan gateway Cloudflare. |
| `tests/` | Pengujian backend, frontend, antrean, dan kontrak API. |
| `tools/` | Utilitas benchmark API. |

Model GGUF, indeks FAISS, cache, dan hasil build tidak disimpan di Git karena ukurannya besar. Aset tersebut diunduh atau dibuat ulang saat persiapan sistem.

## Prasyarat

- Python 3.11
- Ollama
- Git
- Node.js 22 atau lebih baru untuk gateway Cloudflare
- GPU yang didukung Ollama disarankan untuk inferensi yang lebih cepat

## Instalasi lokal

1. Clone repository dan masuk ke folder proyek.

   ```bash
   git clone https://github.com/Makaareeem/SistemQAPublikasi.git
   cd SistemQAPublikasi
   ```

2. Buat dan aktifkan environment Python.

   ```bash
   python -m venv .venv
   ```

   Windows:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Linux atau macOS:

   ```bash
   source .venv/bin/activate
   ```

3. Instal dependensi.

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Salin konfigurasi contoh.

   Windows:

   ```powershell
   Copy-Item .env.example .env
   ```

   Linux atau macOS:

   ```bash
   cp .env.example .env
   ```

5. Jalankan Ollama pada terminal terpisah.

   ```bash
   ollama serve
   ```

6. Unduh dan daftarkan model ke Ollama.

   ```bash
   python -m deploy.setup_ollama
   ```

7. Jalankan aplikasi.

   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

Buka [http://127.0.0.1:8000](http://127.0.0.1:8000). Indeks FAISS, metadata publikasi, embedding model, dan reranker akan diunduh pada persiapan pertama.

## Konfigurasi

Konfigurasi runtime berada di `.env`. Nilai yang paling sering disesuaikan:

| Variabel | Kegunaan |
| --- | --- |
| `DEFAULT_MODEL_KEY` | Model yang dipilih secara default. |
| `INFERENCE_URL` | Alamat layanan Ollama. |
| `QUEUE_CONCURRENCY` | Jumlah pipeline yang dapat aktif bersamaan. |
| `MAX_QUEUE` | Jumlah permintaan yang dapat menunggu. |
| `QUEUE_WAIT_TIMEOUT` | Batas waktu tunggu antrean. |
| `OLLAMA_TIMEOUT` | Batas waktu komunikasi dengan Ollama. |
| `OLLAMA_KEEP_ALIVE` | Lama model dipertahankan dalam memori. |
| `EMBEDDING_DEVICE` | Perangkat untuk embedding, misalnya `cpu` atau `cuda`. |
| `RERANKER_DEVICE` | Perangkat untuk reranker. |
| `RERANK_SCORE_THRESHOLD` | Batas minimal skor reranker. |

Gunakan `.env.example` sebagai acuan lengkap. Jangan memasukkan `.env`, token Hugging Face, API key Runpod, atau password Cloudflare ke repository.

## API

| Metode dan endpoint | Kegunaan |
| --- | --- |
| `GET /ping` | Health check untuk deployment. |
| `GET /api/health` | Status backend, indeks, dan model. |
| `GET /api/ready` | Readiness check aplikasi. |
| `POST /api/ask` | Menghasilkan jawaban RAG dalam format JSON. |
| `POST /api/ask/stream` | Menghasilkan jawaban melalui Server-Sent Events. |
| `POST /api/eval/ask` | Endpoint penelitian privat; nonaktif secara default. |

Contoh permintaan:

```json
{
  "question": "Apa yang dimaksud dengan Tingkat Pengangguran Terbuka?",
  "model_key": "llama3.2-finetuned",
  "use_rag": true,
  "response_style": "ringkas"
}
```

Dokumentasi OpenAPI tersedia di [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) ketika backend lokal aktif.

## Pengujian

Instal dependensi pengembangan:

```bash
python -m pip install -r requirements-dev.txt
```

Jalankan pengujian backend:

```bash
python -B -m unittest discover -s tests -p "test_*.py" -v
```

Jalankan pengujian frontend tanpa browser:

```bash
node --test tests/frontend.test.cjs tests/frontend-audit.test.cjs tests/frontend-ui.test.cjs
```

Jalankan pengujian deployment:

```bash
python -B -m unittest discover -s deploy/runpod-demo -p "test_*.py" -v
cd deploy/runpod-demo/gateway
npm install
npm test
```

`tests/frontend-browser.test.cjs` menyediakan pemeriksaan visual opsional dan memerlukan Playwright serta `tests/ui_preview_server.py`. `smoke_test.py` menjalankan satu permintaan nyata sehingga backend dan Ollama harus aktif.

## Deployment

Konfigurasi production berada di [`deploy/runpod-demo`](deploy/runpod-demo/README.md). Docker image mengunduh aset berdasarkan versi dan checksum dalam `assets.json`. Cloudflare Worker menyajikan frontend tanpa login, menyimpan API key Runpod sebagai secret, membatasi frekuensi permintaan, dan meneruskan rute yang diizinkan ke backend.

Untuk menjaga biaya ketika tidak digunakan, Runpod dapat dikonfigurasi dengan active worker `0`. Permintaan pertama setelah worker berhenti memerlukan waktu tambahan untuk menyalakan container dan memuat model.

## Keamanan

- API key Runpod hanya disimpan sebagai secret pada Cloudflare Worker.
- Browser tidak menerima kredensial Runpod.
- API evaluasi tidak dibuka melalui gateway publik.
- Request body, origin, rute, dan ukuran input diperiksa sebelum diteruskan.
- Antrean aplikasi dan rate limiting Cloudflare membatasi permintaan. Penggunaan GPU serta biaya tetap perlu dipantau karena layanan dapat diakses umum.
