# Source Code Pengolahan

Source code penelitian skripsi **"Implementasi Small Language Model (SLM) dengan Fine-Tuning QLoRA dan Retrieval-Augmented Generation (RAG) untuk Question Answering Publikasi Statistik BPS"**.

Penelitian terdiri atas tiga tujuan:

| Tujuan | Isi                                                           | Folder kode | Folder hasil     | Bab |
| ------ | ------------------------------------------------------------- | ----------- | ---------------- | --- |
| 1      | Seleksi SLM berbahasa Indonesia                               | `tujuan1/`  | `Hasil/tujuan1/` | 4.1 |
| 2      | Pembangunan dataset QA, fine-tuning QLoRA, dan evaluasi model | `tujuan2/`  | `Hasil/tujuan2/` | 4.2 |
| 3      | Implementasi dan evaluasi sistem QA berbasis RAG              | `tujuan3/`  | `Hasil/tujuan3/` | 4.3 |

Aplikasi web QA (FastAPI + Ollama + FAISS/BM25 + reranker) berada di repositori terpisah, `Sistem QA RAG/`. Lihat README di sana.

---

## Struktur folder

SkripsiNabil/
├── tujuan1/ # Seleksi SLM (IndoMMLU + IndoCareer)
├── tujuan2/
│ ├── [1] data preparation/ # Ekstraksi PDF → chunking → dataset QA → embedding
│ ├── [2] modelling/ # Persiapan, fine-tuning QLoRA, prediksi
│ └── [3] evaluation/ # Evaluasi otomatis, evaluasi manusia, ekspor GGUF
├── tujuan3/ # Evaluasi RAG (K1–K5), skenario, performa sistem
├── Visualisasi/ # Notebook grafik Bab 4 + diagram arsitektur
├── Hasil/
│ ├── tujuan1/ # Ranking dan data benchmark
│ ├── tujuan2/ # Artefak dataset, training, dan evaluasi + Gambar/
│ ├── tujuan3/ # Artefak RAGAS, skenario, versi-final/, adopsi-bps/ + Gambar/
│ └── Wawancara/
└── Percobaan/ # Notebook uji coba versi lama (tidak dipakai di skripsi)

---

## Tujuan 1 — Seleksi SLM

Kandidat dievaluasi secara _zero-shot_ dengan _greedy decoding_ dan kuantisasi 4-bit pada IndoMMLU (`indolem/IndoMMLU`) dan IndoCareer (`indolem/IndoCareer`, config `all`). Skor akhir = 50% akurasi IndoMMLU + 50% akurasi IndoCareer.

| Notebook                                                                                                                                                                             | Fungsi                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `smollm2-135m`, `smollm2-360m`, `qwen2-5-0-5b`, `qwen2-5-1-5b`, `qwen2-5-3b`, `qwen2-5-7b`, `llama3-2-1b`, `llama3-2-3b`, `llama-3-1-8b`, `gemma-2-2b`, `phi-3-5-mini`, `mistral-7b` | Evaluasi satu model per notebook (template sama)                                                                  |
| `result-tujuan1.ipynb`                                                                                                                                                               | Menggabungkan hasil seluruh model menjadi ranking final per subjek dan kelompok profesi                           |
| `uji-statistik-tujuan-1-seleksi-slm.ipynb`                                                                                                                                           | Uji konkordansi Spearman (IndoMMLU vs IndoCareer) dan One-Way ANOVA pada lima model teratas, didahului uji asumsi |

**Keluaran:** `ranking_summary.csv`, `ranking_final_komprehensif.csv`, `dataset_IndoMMLU.csv`, `dataset_IndoCareer.csv`, dan `Ranking IndoMMLU dan IndoCareer.xlsx`.

---

## Tujuan 2 — Dataset QA, Fine-Tuning, dan Evaluasi Model

Seluruh notebook dijalankan di Kaggle (GPU). Artefak disimpan ke Hugging Face Hub:

- `Makaareeem/publikasi-rag-knowledge-base` — chunk, metadata, embedding, indeks FAISS
- `Makaareeem/publikasi-rag-finetuning-dataset` — dataset QA, data terformat, prediksi, skor
- `Makaareeem/{gemma2,llama3.2}-qlora-adapter` — adaptor LoRA
- `Makaareeem/{gemma2,llama3.2}-{base,finetuned}-gguf` — model GGUF untuk Ollama

### [1] Data preparation

| No    | Notebook                            | Fungsi                                                                                                                                    |
| ----- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 01    | `01-extract-pdf-pymupdfllm-ocr`     | Ekstraksi teks PDF publikasi BPS dengan PyMuPDF4LLM dan penilaian mutu ekstraksi                                                          |
| 02    | `02-cleaning-extract`               | Pembersihan artefak ekstraksi dengan tetap mempertahankan penanda struktur (Markdown, layout)                                             |
| 03    | `03-structured-cleaned-extract`     | Penyusunan struktur dokumen (bab/subbab) dari hasil pembersihan                                                                           |
| 04    | `04-chunking-and-splitting`         | Chunking per section (`chunk_size=2000`, `overlap=200`, `chunking_v3_rag`); hanya teks naratif, tanpa tabel dan gambar                    |
| 05    | `05-generating-context-aware-qa`    | Pembangkitan pasangan QA ter-_grounding_ per section dengan LLM `deepseek-v4-flash` (konteks 1.500 token, overlap 150, temperatur QA 0,7) |
| 05b-1 | `05b-tahap-1-eksplorasi-dataset-qa` | Eksplorasi awal dataset QA                                                                                                                |
| 05b-2 | `05b-tahap-2-cleaning-dataset-qa`   | Pembersihan berbasis aturan: validasi `chunk_id`, deteksi duplikat dengan embedding + FAISS                                               |
| 05b-3 | `05b-tahap-3-dataset-qa-eval`       | Uji keragaman pertanyaan, distribusi pembuka, dan kemiripan semantik IndoBERT                                                             |
| 06    | `06-dataset-qa-final`               | Dataset final dan pembagian `train` (6.516) / `val` (1.043) / `test` (1.791), diunggah ke HF                                              |
| 07    | `07-embedding`                      | Embedding chunk dengan `nomic-ai/nomic-embed-text-v1.5` (768 dimensi) dan indeks FAISS                                                    |

### [2] Modelling

| No  | Notebook                                                           | Fungsi                                                                                          |
| --- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| 08  | `08-modelling-preparation`                                         | Format chat template per model, analisis panjang token, _dry-run_ VRAM untuk memilih batch size |
| 09  | `09-instruction-tuning-gemma2`, `09-instruction-tuning-llama3-2`   | Fine-tuning QLoRA (Unsloth + TRL), dengan konfigurasi pada tabel di bawah                       |
| 10  | `10-generate-prediction-gemma2`, `10-generate-prediction-llama3-2` | Prediksi model base dan fine-tuned pada data uji                                                |

Konfigurasi fine-tuning QLoRA (notebook 09):

| Parameter               | Gemma-2-2B                       | Llama-3.2-3B                             |
| ----------------------- | -------------------------------- | ---------------------------------------- |
| Model dasar             | `unsloth/gemma-2-2b-it-bnb-4bit` | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| LoRA r / alpha          | 16 / 32                          | 16 / 32                                  |
| Learning rate           | 2e-5                             | 2e-5                                     |
| Epoch                   | 3                                | 3                                        |
| Batch efektif           | 16 (4 × 4)                       | 16 (2 × 8)                               |
| Panjang urutan maksimum | 1.024                            | 1.536                                    |

### [3] Evaluation

| No  | Notebook                                                                     | Fungsi                                                                 |
| --- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 11  | `11-compute-automatic-eval`                                                  | EM, F1, ROUGE-L, dan IndoBERTScore (`firqaaa/indo-sentence-bert-base`) |
| 12  | `12-prepare-human-evaluation`                                                | Penyusunan lembar evaluasi manusia secara buta (_blind_)               |
| 13  | `13-compute-human-evaluation`                                                | Rekap skor Likert dan reliabilitas antarpenilai (Krippendorff's alpha) |
| 15  | `15-export-gguf-model`                                                       | Merge adaptor dan ekspor ke GGUF Q4_K_M beserta `Modelfile` Ollama     |
| 16  | `16-generate-prediction-gemma2-gguf`, `16-generate-prediction-llama3-2-gguf` | Prediksi ulang memakai model GGUF melalui Ollama                       |
| 17  | `17-compute-automatic-eval-gguf`                                             | Metrik otomatis untuk prediksi GGUF                                    |

**Keluaran utama** (`Hasil/tujuan2/`):

- `train/val/test.csv` dan `*_predictions*.csv`
- `*_scored*.csv` dan `summary_metrics*.csv`
- `human_eval_*.csv`
- `*_training_summary.json` dan `training_config.json`
- `faiss_index.bin`
- JSON hasil ekstraksi per publikasi
- Gambar `fig01`–`fig47`

---

## Tujuan 3 — Sistem QA Berbasis RAG

Pipeline retrieval:

1. Perluasan kueri.
2. Pencarian _dense_ (nomic-embed + FAISS, top-20) dan BM25 (top-20).
3. Penggabungan peringkat dengan Reciprocal Rank Fusion (RRF).
4. _Reranking_ dengan `madebyaris/rerank-indonesia`.
5. Generasi jawaban dengan k = 5 sumber.

Kondisi ablasi:

| Kondisi | Model                                                           | RAG   |
| ------- | --------------------------------------------------------------- | ----- |
| K1      | Base                                                            | Tidak |
| K2      | Base                                                            | Ya    |
| K3      | Fine-tuned                                                      | Tidak |
| K4      | Fine-tuned                                                      | Ya    |
| K5      | DeepSeek (`deepseek-v4-flash`) sebagai pembanding LLM komersial | Ya    |

| No  | Notebook                            | Lingkungan | Fungsi                                                                                                                                                                           |
| --- | ----------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 18  | `18-persiapan-evaluasi-rag`         | Kaggle     | Registrasi model/prompt, penguncian revisi artefak HF, penentuan _gold chunk_ untuk Hit@K, Recall@K, MRR                                                                         |
| 19  | `19-generate-prediction-RAG`        | Kaggle     | Instalasi Ollama, registrasi 4 GGUF, generasi jawaban K1–K5                                                                                                                      |
| 20  | `20-rag-evaluation`                 | Kaggle     | Metrik retrieval dan RAGAS 0.4.3 (Faithfulness, Answer Relevancy, Context Relevance) dengan _judge_ `gpt-4o-mini` dan `text-embedding-3-small`; selisih berpasangan antarkondisi |
| 21  | `21-generate-scenario-evaluation`   | Kaggle     | Evaluasi skenario pertanyaan, variasi gaya bahasa, dan kesalahan ketik (_robustness_)                                                                                            |
| 23  | `23-test-system-performance`        | Lokal      | Uji performa versi awal (endpoint produksi, evaluasi, streaming, generator Ollama)                                                                                               |
| 23b | `23b-test-system-performance-final` | Lokal      | Uji performa versi akhir (waktu respons, CPU, RAM, VRAM), profil permintaan bersamaan (1/2/4 klien), dan perencanaan adopsi BPS                                                  |

**Keluaran utama** (`Hasil/tujuan3/`):

- `ragas_summary.csv`, `ragas_paired_differences.csv`
- `scenario_*.csv`
- `functional_results.json`, `stream_stage_test.json`
- `versi-final/<run_id>/` — `system_performance_all.csv`, `capacity_profile.csv`, `coverage.json`, `system_performance_environment.json`
- `adopsi-bps/<run_id>/` — `kebutuhan-operasional.csv`, `kebutuhan-pengembangan-model.csv`, `beban-pembuatan-dataset.csv`, `cakupan-bukti-pengukuran.csv`, `inventaris-artefak-sistem.csv`, `asumsi-dan-sumber.json`

Notebook 23b membuat folder run baru setiap kali dijalankan. Notebook visualisasi membaca run terbaru yang lengkap.

---

## Visualisasi

| Notebook                     | Membaca          | Menghasilkan            |
| ---------------------------- | ---------------- | ----------------------- |
| `Visualisasi tujuan 1.ipynb` | `Hasil/tujuan1/` | Grafik Bab 4.1          |
| `Visualisasi tujuan 2.ipynb` | `Hasil/tujuan2/` | `fig01`–`fig47` Bab 4.2 |
| `Visualisasi tujuan 3.ipynb` | `Hasil/tujuan3/` | `fig01`–`fig18` Bab 4.3 |

Ketiga notebook berjalan di Google Colab (Drive) dan hanya membaca artefak aktual, tanpa angka _fallback_. Pada tujuan 3, Gemma-2 dikeluarkan: RAGAS ditampilkan untuk Llama-3.2 dan DeepSeek, sedangkan performa dan adopsi hanya untuk Llama-3.2.

Diagram pendukung: `Arsitektur QA.png`, `Crips MLQ.png`, `Diagram-QLoRA.drawio.png`, `Faiss UMUM.drawio.png`.

---

## Urutan menjalankan

Tujuan 1 : model-\*.ipynb → result-tujuan1 → uji-statistik-tujuan-1
Tujuan 2 : 01 → 02 → 03 → 04 → 05 → 05b(1-3) → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 15 → 16 → 17
Tujuan 3 : 18 → 19 → 20 → 21 → (jalankan Sistem QA RAG lokal) → 23b
Grafik : Visualisasi tujuan 1/2/3

---

## Lingkungan dan kredensial

- **Kaggle** (tujuan 1, 2, dan 18–21): GPU Kaggle; _secrets_ `HF_TOKEN`, `API_Deepseek`, dan kunci OpenAI untuk _judge_ RAGAS.
- **Lokal** (23, 23b): Windows, conda env `rag-sistem`, Python 3.11, Ollama, backend `Sistem QA RAG` di `http://127.0.0.1:8000`.
  - Perangkat uji: Intel 4 core/8 thread, RAM 16 GB, RTX 3050 Laptop 4 GB.
  - Dependensi notebook: `requests`, `pandas`, `numpy`, `psutil`, `nvidia-ml-py`.
- **Colab**: notebook visualisasi; folder `Hasil/` berada di Google Drive.

## Catatan

- Cakupan data hanya teks naratif publikasi; tabel dan gambar tidak masuk basis pengetahuan maupun dataset.
- Dataset QA dibangkitkan dengan LLM (DeepSeek), sehingga tetap memerlukan pembersihan dan pemeriksaan.
- Status `ok` pada uji performa menandakan kontrak API berhasil, bukan kebenaran jawaban.
- Notebook di `Percobaan/` adalah versi uji coba dan tidak menjadi dasar hasil skripsi.
