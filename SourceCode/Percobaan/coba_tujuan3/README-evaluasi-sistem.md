# Pengujian tujuan 3 setelah GGUF

Acuan proposal yang digunakan: **Bab 3 - Metode Penelitian - Naskah Baru.docx**, folder *Naskah Baru Bab 3 - 21 September 2026*, terutama §3.2.4 dan §3.2.5. Notebook 15–17 tetap dipertahankan; ketiganya mengekspor dan mengevaluasi generator GGUF dengan konteks acuan. Notebook baru menguji sistem dengan hasil retrieval sesungguhnya.

## Cakupan evaluasi yang disepakati

Notebook 18–19 **hanya menghitung answer relevance, faithfulness, dan context relevance**. EM, F1, ROUGE-L, dan IndoBERTScore tetap menjadi hasil tahap sebelumnya; tidak dihitung ulang di sini. Dependensi bert-score/rouge-score dan unduhan encoder penilai telah dihapus.

Tanpa RAG: answer relevance. Dengan RAG: ketiganya. Faithfulness menilai dukungan klaim jawaban oleh konteks; context relevance menilai retrieval terhadap pertanyaan. Tidak menggabungkan ketiganya menjadi satu skor before/after.

Gunakan RUN_NAME evaluasi baru untuk hasil bersih. Notebook 19 dapat membaca prediksi lama tanpa generasi ulang dan hanya menyalin artefak generasi/cache, bukan tabel metrik lama. Artefak lama tidak dihapus. evaluation_scope.json menyatakan metrik yang aktif. Notebook 20 tidak lagi menghitung F1; rekap robustness otomatis hanya jumlah permintaan berhasil/gagal, sedangkan kualitas tetap dinilai melalui lembar manusia.

LLM komersial sebagai generator pembanding belum ditambahkan karena modelnya belum dipilih; API yang ada tetap untuk judge.

## Urutan penggunaan

**Notebook 18 sudah menggabungkan generasi dan evaluasi. Notebook 19 tidak wajib dijalankan.**

1. Import **18-evaluate-rag.ipynb** ke Kaggle; aktifkan GPU dan Internet. Tidak perlu folder aplikasi, FastAPI, atau UI Sistem QA RAG. Logika pipeline aplikasi disertakan langsung sebagai snapshot di notebook.
2. Di Add-ons → Secrets, aktifkan `HF_Faiss` bila akses HF membutuhkan token dan `OPENAI_API_KEY` untuk RAGAS. Jangan tempel nilai key ke sel, chat, atau output. Jalankan sel setup pada sesi baru. Jika diminta restart setelah pemasangan, restart lalu ubah `INSTALL_DEPENDENCIES=False` sebelum menjalankan kembali.
3. Default pilot: `RUN_NAME="pilot_v2"`, `DATA_SPLIT="val"`, `MAX_ITEMS=5`, `RUN_EXPERIMENT=True`. Ada 60 prediksi utama: delapan end-to-end dan empat controlled per pertanyaan. CSV, metadata, indeks FAISS, dan empat GGUF diambil dari Hugging Face seperti notebook 16. Model OpenAI bukan generator penelitian.
4. Ubah `RUN_RAGAS=True` untuk menjalankan tiga metrik dengan OpenAI. Default `False` mencegah panggilan API berbayar tanpa pengaturan eksplisit. Judge default `gpt-4o-mini-2024-07-18`; embedding `text-embedding-3-small`. Sesuaikan dengan akses akun dan bekukan sebelum final. Pertanyaan, jawaban, dan potongan konteks dikirim ke OpenAI; biaya mencakup chat dan embedding.
5. Jalankan sel berurutan hingga rekap dan ZIP. Periksa prompt, konteks, kegagalan, serta kualitas judge pada bahasa Indonesia. Untuk final gunakan RUN_NAME baru, `DATA_SPLIT="test"`, `MAX_ITEMS=None`, setelah konfigurasi dibekukan pada validasi. Jangan memilih konfigurasi berdasarkan skor test.
6. Unduh folder hasil/ZIP melalui panel Output Kaggle. Tidak ada upload HF otomatis. Pengujian penuh dapat memerlukan beberapa sesi; simpan output sebelum sesi berakhir.
7. **19-compute-evaluate-rag.ipynb** hanya untuk evaluasi ulang atau melanjutkan RAGAS: attach output 18 sebagai Kaggle input, isi `INPUT_RUN_DIR` ke folder berisi `manifest.json`, gunakan RUN_NAME evaluasi baru, dan aktifkan RUN_RAGAS bila perlu. Tidak ada unduhan GGUF atau generasi ulang. Sel evaluasinya identik dengan 18 dan diperiksa unit test.
8. **20-test-function-robustness-latency.ipynb** dijalankan lokal bersama aplikasi aktif; petunjuk terperinci ada di bawah.

### Sumber Hugging Face dan resume

Dataset: `Makaareeem/publikasi-rag-finetuning-dataset`; KB: `Makaareeem/publikasi-rag-knowledge-base`. GGUF memakai repo `Makaareeem/gemma2-base-gguf`, `Makaareeem/gemma2-finetuned-gguf`, `Makaareeem/llama3.2-base-gguf`, dan `Makaareeem/llama3.2-finetuned-gguf`.

Untuk resume sesi baru, attach folder hasil lama sebagai Kaggle input, isi `RESTORE_DIR` ke folder yang langsung berisi manifest, lalu gunakan konfigurasi yang sama. ZIP perlu diekstrak dahulu. Restore menolak benturan isi berkas. Hasil sukses dilewati, error dicoba ulang, konteks controlled dipertahankan.

Manifest membekukan revisi HF, hash data/model/KB, prompt, konfigurasi, versi paket dan Ollama. Revisi HF lama otomatis dipakai saat resume. Jika runtime/paket berubah, pulihkan versinya atau gunakan run baru; jangan menonaktifkan pemeriksaan manifest. Installer Ollama mengikuti pola notebook 16 dan mengambil versi tersedia saat instalasi. CPU dipakai untuk embedding/reranker agar GPU tersedia bagi Ollama. Seed, timeout, dan `num_ctx=8192` dibuat eksplisit. Ini kesetaraan algoritma, bukan bukti waktu Kaggle identik dengan aplikasi lokal. Snapshot tidak otomatis mengikuti perubahan aplikasi berikutnya.

## Ketiga metrik RAGAS

| Metrik | Input | Kelas pada RAGAS 0.2.15 |
|---|---|---|
| Faithfulness | Pertanyaan, jawaban, konteks aktual | `Faithfulness` |
| Answer relevance | Pertanyaan, jawaban | `ResponseRelevancy`, strictness=3, embedding OpenAI |
| Context relevance | Pertanyaan, konteks aktual | `ContextRelevance` |

Dataset tidak perlu mempunyai kolom recall atau skor RAGAS. Pertanyaan berasal dari dataset; jawaban dan konteks dihasilkan eksperimen, kemudian dinilai. Kolom `cot`, `response`, dan `ans_ref` bukan syarat evaluasi RAGAS. Jika tersedia, acuan hanya dipertahankan sebagai bahan pemeriksaan manusia di notebook 20; tidak dinilai oleh evaluator 18–19.

**Catatan Bab III:** `ContextRelevance` versi ini berasal dari keluarga metrik NVIDIA: dua prompt judge memberikan 0/1/2, lalu dinormalisasi menjadi 0–1. Jika keduanya valid, diambil rata-rata; bila hanya satu valid, implementasi memakai yang valid. Ini **bukan context recall/precision dan berbeda dari rumus fraksi kalimat relevan pada paper RAGAS awal**. Jika Bab III mewajibkan rumus paper awal tersebut, perlu keputusan penyelarasan sebelum run final; jangan menyebut keduanya identik. Bab III tidak diubah.

Faithfulness/context relevance bernilai NA untuk K1/K3. Retrieval kosong pada kondisi RAG ditandai `empty_retrieval` dan NA; jumlahnya wajib dilaporkan, bukan disembunyikan di balik rata-rata kasus valid. Answer relevance tetap dihitung pada semua kondisi. Kegagalan evaluator/NaN tidak diganti nol. Cache terpisah per input/metrik/konfigurasi sehingga retry tidak mengulang metrik yang berhasil. Ada beberapa panggilan API untuk sebagian metrik; kalibrasikan kualitas dan biaya pada pilot.

Audit langsung wheel RAGAS 0.2.15 menemukan rincian berbeda dari uraian dokumentasi: ContextRelevance memotong konteks menjadi 7.000 karakter, memakai temperature 0.1, dan memanggil template pertama dua kali. Notebook mempertahankan implementasi paket serta mencatat `context_relevance_context_chars` dan `context_relevance_truncated`. Jangan mengklaim konteks panjang seluruhnya dinilai atau dua template berbeda digunakan. Audit dampak batas ini sebelum final. Konfigurasi evaluator mencatat perilaku internal tersebut; temperature 0 pada objek chat tidak berarti semua metrik menggunakannya tanpa override.

Referensi implementasi: [Faithfulness](https://docs.ragas.io/en/v0.2.15/concepts/metrics/available_metrics/faithfulness/), [Answer relevance](https://docs.ragas.io/en/v0.2.15/concepts/metrics/available_metrics/answer_relevance/), [Context relevance](https://docs.ragas.io/en/v0.2.15/concepts/metrics/available_metrics/nvidia_metrics/), [OpenAI API](https://developers.openai.com/api/docs/quickstart).

Hit@5, Recall@5, MRR@5 dan pembuatan qrels sudah dikeluarkan dari alur 18–19. Evaluasi tahap ini hanya tiga metrik RAGAS. Berkas qrels lama, bila ada, tidak dihapus atau dipakai untuk skor baru.

## Menjalankan notebook 20 bersama aplikasi

Ya, boleh menyalakan dev aplikasi terlebih dahulu. Notebook mengirim HTTP ke aplikasi; aplikasi tidak menjalankan ipynb.

1. Download folder hasil 18, letakkan di `Hasil/tujuan3/pilot_v2` proyek SkripsiNabil.
2. Di terminal folder Sistem QA RAG, aktifkan lingkungan aplikasi dan ikuti README aplikasi untuk dependensi serta `.env`. Jalankan `ollama serve` jika layanan belum aktif; setup model pertama kali memakai `python -m deploy.setup_ollama`.
3. Untuk pemeriksaan dev jalankan `uvicorn app.main:app --reload`.
4. Buka notebook 20 melalui Jupyter/VS Code **lokal**. Samakan RUN_NAME; tentukan LOCAL_RUN_NAME; periksa API_URL (default port 8000) dan OLLAMA_URL (port 11434). Kernel notebook memerlukan pandas, numpy, requests; krippendorff hanya untuk rekap manusia.
5. Aktifkan `RUN_API_TESTS=True`. Preflight memeriksa endpoint dan empat model, tetapi bukan bukti semua fungsi lulus.
6. Untuk waktu final, restart server tanpa reload: `uvicorn app.main:app --host 127.0.0.1 --port 8000`. Isi SERVER_HARDWARE, set `SERVER_RUN_MODE="no_reload"`, gunakan LOCAL_RUN_NAME baru, dan aktifkan RUN_TIMING. Jangan jalankan beban lain bersamaan.
7. Untuk robustness, isi dan sahkan pertanyaan asli serta variasinya sebelum mengaktifkan RUN_ROBUSTNESS. OOS diperiksa terhadap cakupan korpus dan dinilai manusia, bukan memakai token F1.

Hasil baru tersimpan terpisah pada `Hasil/tujuan3/<RUN_NAME>/local_tests/<LOCAL_RUN_NAME>/`. Paket manusia membaca prediksi 18. Tidak memerlukan OpenAI. `localhost` Kaggle menunjuk mesin Kaggle, bukan laptop; karena itu notebook 20 dijalankan lokal.

Default timing: tiga pertanyaan × empat model × dua mode RAG × (satu model-unloaded + tiga warm) = 96 permintaan. Model dikeluarkan dari memori untuk blok unloaded; embedding/reranker/cache OS mungkin sudah hangat. Ini bukan cold-start seluruh sistem, bukan TTFT/token per detik. Laporkan median/p95 dan ukuran sampel; p95 dari sedikit ulangan belum stabil.

Uji gangguan, sumber/halaman, isolasi pertanyaan, dan UI memiliki lembar manual berstatus awal `not_run`. Paket evaluasi manusia: 1% pertanyaan lengkap dibulatkan ke atas, delapan kondisi end-to-end, lima penilai, skala 1–5; rekap alpha ordinal dilakukan setelah semua lembar terisi.

## Apa itu test_evaluation_notebooks.py?

Ini **unit test kode notebook**, bukan dataset, bukan eksperimen model, dan bukan uji aplikasi sungguhan. Ia mengambil definisi fungsi tanpa menjalankan sel inferensi/unduhan, memakai contoh kecil dan komponen palsu, tanpa API berbayar. Jalankan dari akar proyek:

```text
python tujuan3/test_evaluation_notebooks.py
```

Dependensinya nbformat, numpy, dan pandas. Test memeriksa format/sintaks, masukan tanpa jawaban acuan, pembatasan tiga metrik, pasangan controlled, cache/resume, NA tanpa RAG, konflik restore, serta kesamaan evaluator 18–19. Tidak menjalankan model/API dan bukan bukti kualitas model.

## Cara membaca eksperimen

| Kondisi | Model | Konteks |
|---|---|---|
| K1 | Sebelum tuning | Tanpa retrieval |
| K2 | Sebelum tuning | Retrieval |
| K3 | Sesudah tuning | Tanpa retrieval |
| K4 | Sesudah tuning | Retrieval |

Kedua arsitektur menjalani keempat kondisi. Pada `end_to_end`, model uji juga membuat ekspansi kueri, sesuai implementasi aplikasi. Pada `controlled`, retrieval satu model referensi disimpan dan digunakan identik oleh kedua generator. Selisih K4–K2 pada protokol kedua lebih tepat untuk membahas perubahan generator dengan konteks tetap. K1/K3 tidak diulang di protokol controlled karena tidak menerima retrieval.

K1/K3 mempertahankan kebijakan prompt berbasis konteks yang sama; model dapat lebih sering menolak tanpa konteks. Ini ablasi sistem dengan prompt tetap, bukan pengukuran kemampuan closed-book maksimum. K3–K1 membahas tuning tanpa RAG; K2–K1 dan K4–K3 membahas tambahan RAG.

Semua fungsi baru memiliki komentar singkat tepat di atas definisinya. Kode metode disertakan langsung dalam notebook, bukan disembunyikan dalam modul tambahan.

Pemeriksaan data lokal menemukan 1.791 pertanyaan uji dan 22.603 entri KB. Sebanyak 45 ID chunk asal berulang dengan teks berbeda; notebook membedakannya melalui gabungan `chunk_id::faiss=<nomor>`. Seluruh kandidat provenance pertanyaan uji dapat dipetakan ke metadata. Dengan dua protokol default, pengujian penuh memerlukan 21.492 prediksi utama, di luar panggilan ekspansi kueri, ringkasan sumber, dan evaluator.

## Keluaran

Hasil Kaggle masuk ke `/kaggle/working/rag_results/<RUN_NAME>/`, lalu diunduh ke `Hasil/tujuan3/<RUN_NAME>/` untuk pengujian lokal:

- `manifest.json`: konfigurasi, hash data/kode/KB, metadata model, lingkungan eksekusi.
- `predictions/*.json`: jawaban, prompt, konteks, ID chunk, waktu komponen, status kegagalan; dapat dilanjutkan setelah terputus.
- `retrieval_cache/`: snapshot konteks untuk eksperimen controlled.
- `system_scored.*`, `system_metrics_summary.csv`, `system_metrics_by_task.csv`, `paired_differences.csv`: skor dan analisis berpasangan.
- `inference_coverage.csv`: jumlah inferensi berhasil/gagal. Notebook juga melaporkan jumlah prediksi tersimpan terhadap yang diharapkan.
- `ragas_cache/`, `ragas_evaluators/`, `*_coverage.csv`: cache, identitas judge tanpa key, dan cakupan ketiga metrik.
- `test_selected.csv`: nama kompatibilitas; kolom split dan manifest membedakan val dari test.
- `local_tests/<LOCAL_RUN_NAME>/`: `functional_results.csv`, `functional_manual.csv`, `timing/`, `robustness/`, `human_evaluation/` untuk pengujian sistem dan penilaian manusia.

## Dasar metode

| Bagian | Sumber penelitian | Penerapan dalam notebook |
|---|---|---|
| RAG | Lewis dkk. (2020), [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) | Pisahkan pengetahuan parametrik dan konteks dokumen; aplikasi memakai adaptasi retrieve-then-generate, bukan replikasi pelatihan end-to-end paper |
| Fusion | Cormack dkk. (2009), [Reciprocal Rank Fusion](https://doi.org/10.1145/1571941.1572114) | Gunakan fungsi RRF aplikasi yang sudah ada |
| Faithfulness dan relevancy | Es dkk. (2024), [RAGAS](https://aclanthology.org/2024.eacl-demo.16/) | Penilaian klaim terhadap konteks dan relevansi jawaban terhadap pertanyaan |
| Ketahanan | Ribeiro dkk. (2020), [CheckList](https://aclanthology.org/2020.acl-main.442/) | Uji kemampuan minimum dan invariansi parafrasa/typo yang disahkan |
| Evaluasi manusia | van der Lee dkk. (2021), [Human evaluation of automatically generated text](https://doi.org/10.1016/j.csl.2020.101151) | Rubrik eksplisit, identitas model dibutakan, pelaporan prosedur penilai |

Angka seed, ukuran pilot, ulangan waktu, model referensi, matriks K1–K4, dan sampel manusia 1% adalah keputusan desain penelitian/proposal. Jangan menulis bahwa semuanya diwajibkan oleh paper.

## Batas interpretasi

- Tanpa RAG, faithfulness dan context relevance adalah NA, bukan nol. Perbandingan tanpa/dengan RAG memakai answer relevance; ketiganya tidak membuktikan akurasi faktual secara umum.
- Konteks tersimpan sama dengan prompt yang dikirim; aplikasi belum mengungkap pemotongan internal Ollama. Periksa `num_ctx` dan panjang prompt sebelum pengujian final.
- Full test tidak boleh diklaim selesai hanya karena notebook berjalan: cocokkan kelengkapan prediksi dan jumlah skor valid. Pilot bukan hasil penelitian final.
- Waktu `model_unloaded` hanya mengontrol residensi model Ollama. Bukan cold-start semua komponen. Waktu controlled yang memakai cache tidak boleh dipakai sebagai waktu end-to-end aplikasi.
- Uji fungsi otomatis memeriksa perilaku API dan bentuk respons. Dukungan fakta, akses publikasi, UI, OOS, serta pemulihan layanan masih memerlukan bukti pengujian yang dicatat.
- Notebook diperiksa melalui validasi format/sintaks dan unit test offline. Inferensi empat GGUF, eksekusi Kaggle, panggilan judge OpenAI, dan pengujian endpoint belum dijalankan sebagai eksperimen penelitian dalam perubahan ini.
