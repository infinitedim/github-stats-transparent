# Visualisasi Statistik GitHub : Transparan

> Memvisualisasikan statistik pengguna dan repositori GitHub menggunakan GitHub Actions.

<a href="https://github.com/infinitedim/github-stats-transparent">

![ ](https://raw.githubusercontent.com/infinitedim/github-stats-transparent/refs/heads/output/generated/overview.svg)
![ ](https://raw.githubusercontent.com/infinitedim/github-stats-transparent/refs/heads/output/generated/languages.svg)

</a>

> Catatan: Repositori ini adalah perluasan dari proyek [jstrieb/github-stats](https://github.com/jstrieb/github-stats).  
> Dalam bentuk fork yang dipisahkan dari proyek aslinya. Jika Anda menyukai repositori ini, mohon berikan bintang juga pada proyek aslinya.

## ⚠️ Peringatan

Proyek ini menggunakan personal access token dengan izin baca. Jika terjadi kesalahan saat membaca beberapa repositori privat, pengecualian tersebut akan dicetak ke log workflow.  
Log pengecualian ini dapat dilihat oleh siapa saja di tab Actions pada repositori yang di-fork, sehingga beberapa nama repositori privat mungkin terekspos.

## ⚙️ Cara Instalasi

<!-- TODO: Add details and screenshots -->

1. Ikuti panduan [di sini](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) untuk membuat personal access token dengan izin `read:user` dan `repo`, lalu salin token yang dibuat.

2. Klik [Fork repositori ini](https://github.com/infinitedim/github-stats-transparent/fork) untuk melakukan fork repositori.

3. Buka halaman "Settings" → "Secrets" pada repositori yang sudah di-fork (di bagian bawah kiri layar), buat secret baru dengan nama `ACCESS_TOKEN`, dan tempelkan token yang telah disalin.

   ![ ](https://raw.githubusercontent.com/infinitedim/github-stats-transparent/main/readme_images/Actions.png)

4. Jika ingin mengecualikan repositori tertentu, buat secret bernama `EXCLUDED` dan masukkan nama-nama repositori yang ingin dikecualikan, dipisahkan dengan koma.

   <img src='https://raw.githubusercontent.com/infinitedim/github-stats-transparent/main/readme_images/Exclude.png' height='250px'/>

5. Jika ingin mengecualikan bahasa tertentu, buat secret bernama `EXCLUDED_LANGS` dan masukkan nama-nama bahasa yang ingin dikecualikan, dipisahkan dengan koma.

6. Jika ingin menyertakan statistik dari repositori yang di-fork, buat secret bernama `COUNT_STATS_FROM_FORKS` dan isi dengan nilai apa pun.

   <img src='https://raw.githubusercontent.com/infinitedim/github-stats-transparent/main/readme_images/Forks.png' height='250px'/>

7. Tekan tombol "Run Workflow" di [halaman Actions](../../actions?query=workflow%3A"Generate+Stats+Images") untuk pertama kali membuat gambar. Setelah itu akan dibuat otomatis setiap jam, dan dapat dijalankan ulang secara manual.

8. Gambar yang dihasilkan dapat ditemukan di folder [`generated`](../output/generated) dalam cabang `output`.

9. Tinggalkan tautan ke repositori ini agar orang lain dapat membuat gambar statistik mereka sendiri.

10. Jika bermanfaat, jangan lupa beri bintang!

## 🤔 Mengapa Transparan??

Dengan diperkenalkannya mode gelap di GitHub, menjadi sulit untuk menemukan warna latar belakang yang cocok untuk tema terang maupun gelap.  
Solusi paling sederhana untuk masalah ini adalah dengan membuat latar belakang transparan, dan warna teks dipilih setelah mencoba berbagai nilai agar tetap terbaca baik di latar belakang terang maupun gelap.

![ ](https://raw.githubusercontent.com/infinitedim/github-stats-transparent/refs/heads/main/readme_images/light.png)

![ ](https://raw.githubusercontent.com/infinitedim/github-stats-transparent/refs/heads/main/readme_images/dark.png)

## Proyek Terkait

- Perluasan dari fork [jstrieb/github-stats](https://github.com/jstrieb/github-stats)
- Terinspirasi oleh keinginan untuk meningkatkan [anuraghazra/github-readme-stats](https://github.com/anuraghazra/github-readme-stats)
- Memanfaatkan [GitHub Octicons](https://primer.style/octicons/) untuk menggunakan ikon yang sama dengan user interface GitHub
