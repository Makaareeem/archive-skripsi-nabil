# Arsip Skripsi — Question Answering Publikasi Statistik BPS

Repositori ini berisi arsip penelitian skripsi **"Implementasi Small Language Model (SLM) dengan Fine-Tuning QLoRA dan Retrieval-Augmented Generation (RAG) untuk Question Answering Publikasi Statistik BPS"** (Politeknik Statistika STIS).

Publikasi statistik BPS banyak digunakan masyarakat, tetapi formatnya panjang sehingga informasi tertentu sulit ditemukan. Penelitian ini membangun sistem tanya-jawab yang menjawab pertanyaan pengguna berdasarkan isi publikasi BPS. Sistem menggunakan SLM yang dapat dijalankan secara lokal pada sumber daya terbatas. Fine-tuning QLoRA menyelaraskan model dengan istilah dan konsep statistik resmi, sedangkan RAG menjaga agar jawaban bersumber dari publikasi dan dapat ditelusuri kembali ke halaman asalnya.

Penelitian disusun dalam tiga tujuan:

1. **Seleksi SLM** berbahasa Indonesia menggunakan benchmark IndoMMLU dan IndoCareer.
2. **Pembangunan dataset QA, fine-tuning QLoRA, dan evaluasi model** dengan Exact Match, F1, ROUGE-L, IndoBERTScore, serta evaluasi manusia.
3. **Implementasi dan evaluasi sistem QA berbasis RAG** dengan metrik retrieval, RAGAS, skenario pertanyaan, dan uji performa sistem.

Demo aplikasi: [qapublikasi.skripsi.uk](https://qapublikasi.skripsi.uk)

---

## Struktur repositori

```text
Archive-Skripsi-Nabil/
├── Artefact/       # Aplikasi web QA berbasis RAG (produk akhir penelitian)
├── SourceCode/     # Notebook pengolahan data, pemodelan, evaluasi, dan visualisasi
├── Dataset/        # Daftar publikasi sumber dan data statistik akses publikasi BPS
└── Dokumentasi/    # Panduan pengguna dan dokumentasi teknis sistem
```

| Folder | Isi singkat | Dokumentasi |
| --- | --- | --- |
| [`Artefact/`](Artefact/README.md) | Aplikasi web QA: backend FastAPI, pipeline RAG, antarmuka web, pengujian, dan konfigurasi deployment | [README Artefact](Artefact/README.md) |
| [`SourceCode/`](SourceCode/README.md) | Seluruh notebook penelitian untuk Tujuan 1–3, hasil olahan, dan visualisasi Bab 4 | [README SourceCode](SourceCode/README.md) |
| `Dataset/` | Data mentah yang menjadi dasar pemilihan dan pembentukan basis pengetahuan | Dijelaskan di bawah |
| `Dokumentasi/` | Panduan penggunaan sistem dalam format PDF | Dijelaskan di bawah |

---

### `Artefact/` — Aplikasi Sistem QA

Folder ini berisi prototipe sistem Question Answering yang menjadi produk akhir penelitian. Pengguna mengajukan pertanyaan, sistem mencari bagian publikasi yang relevan, lalu SLM menyusun jawaban beserta sitasi ke publikasi dan halaman sumbernya.

Alur utamanya: validasi pertanyaan → perluasan kueri → pencarian hybrid (FAISS + BM25) → Reciprocal Rank Fusion → reranking → pemilihan maksimal lima sumber → generasi jawaban bersitasi. Model yang tersedia adalah Llama 3.2 3B dan Gemma 2 2B, masing-masing dalam versi dasar dan hasil fine-tuning.

Panduan instalasi lokal, konfigurasi, daftar endpoint API, pengujian, dan deployment tersedia di **[Artefact/README.md](Artefact/README.md)**. Konfigurasi deployment produksi dijelaskan lebih lanjut di [Artefact/deploy/runpod-demo/README.md](Artefact/deploy/runpod-demo/README.md).

### `SourceCode/` — Source Code Penelitian

Folder ini berisi notebook yang digunakan untuk menghasilkan seluruh temuan penelitian, dikelompokkan per tujuan:

| Subfolder | Isi |
| --- | --- |
| `tujuan1/` | Evaluasi 12 kandidat SLM, ranking gabungan, dan uji statistik seleksi model |
| `tujuan2/` | Ekstraksi dan chunking PDF, pembangkitan dataset QA, embedding, fine-tuning QLoRA, evaluasi otomatis dan manusia, serta ekspor model GGUF |
| `tujuan3/` | Evaluasi RAG pada lima kondisi ablasi (K1–K5), evaluasi skenario, dan uji performa sistem |
| `Hasil/` | Keluaran tiap tujuan (CSV, JSON, gambar) serta hasil wawancara |
| `Visualisasi/` | Notebook grafik Bab 4 dan diagram arsitektur |
| `Percobaan/` | Notebook uji coba versi lama yang tidak dipakai sebagai dasar hasil skripsi |

Urutan menjalankan notebook, lingkungan (Kaggle, lokal, Colab), konfigurasi fine-tuning, dan daftar artefak di Hugging Face Hub dijelaskan di **[SourceCode/README.md](SourceCode/README.md)**.

### `Dataset/` — Data Sumber

Folder ini menyimpan data mentah yang digunakan sebelum tahap pengolahan.

- **`List Publikasi/`** — daftar publikasi BPS yang menjadi basis pengetahuan sistem.
  - `List_publikasi.xlsx` dan `list publikasi - statistik indonesia.txt` memuat judul publikasi beserta tautan resminya di situs BPS, dikelompokkan per tahun terbit.
  - `pdf.zip` berisi berkas PDF dari 47 publikasi tersebut (2023: 17, 2024: 14, 2025: 16). Arsip ini berukuran sekitar 630 MB dan **tidak disertakan di GitHub**. Berkas PDF dapat diunduh ulang dari tautan pada daftar publikasi.
- **`Data hit and view Publikasi/`** — statistik akses publikasi BPS Pusat berdasarkan Google Analytics, dalam format Excel.
  - `Tahunan/` berisi jumlah *view* dan *download* publikasi sepanjang 2025.
  - `Bulanan/` berisi jumlah *view* dan *download* publikasi untuk Januari dan Februari 2026.

  Data ini digunakan sebagai latar belakang penelitian untuk menunjukkan tingginya pemanfaatan publikasi BPS oleh masyarakat.

### `Dokumentasi/` — Panduan Sistem

Folder ini berisi dua dokumen PDF untuk pembaca yang berbeda:

- **`Dokumentasi Pengguna QA Publikasi Statistik BPS.pdf`** — panduan untuk pengguna umum aplikasi web: cara memulai, menulis pertanyaan yang baik, fitur dan menu, memeriksa angka dan tahun pada jawaban, pertanyaan yang sering diajukan (FAQ), serta cara mengatasi kendala.
- **`Dokumentasi Teknis & Developer.pdf`** — panduan untuk pengembang dan pengelola sistem: alur RAG, model dan basis pengetahuan, struktur komponen perangkat lunak, instalasi lokal, API dan format respons, deployment (Runpod dan Cloudflare), pengujian, serta batasan sistem.

---

## Catatan

- Basis pengetahuan hanya mencakup **teks naratif** publikasi. Tabel dan gambar tidak dimasukkan.
- Model GGUF, indeks FAISS, dan dataset QA tidak disimpan di repositori karena ukurannya besar. Seluruhnya tersedia di Hugging Face Hub dan diunduh otomatis saat persiapan sistem.
- Jawaban sistem dihasilkan oleh model bahasa dan dapat mengandung kekeliruan. Untuk keperluan resmi, selalu periksa kembali angka dan pernyataan pada publikasi sumber yang ditautkan.
