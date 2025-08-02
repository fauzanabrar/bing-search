@echo off
setlocal enabledelayedexpansion

:: ========= SETTINGAN PROFILE =========
set "startProfile=20"
set "endProfile=22"
set "searchEngine=https://www.google.com/search?q="
set "edgePath=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
set "waitSeconds=1150"
:: =====================================

:: ====== DAFTAR QUERY DI SINI =======
set queries[0]=cara membuat pancake
set queries[1]=destinasi wisata terbaik 2024
set queries[2]=rutinitas olahraga di rumah yang mudah
set queries[3]=ulasan smartphone terbaru
set queries[4]=cara menabung dengan cepat
set queries[5]=film terbaik untuk ditonton tahun ini
set queries[6]=tips berkebun sederhana
set queries[7]=cara belajar gitar online
set queries[8]=ide sarapan sehat
set queries[9]=buku terbaik untuk pengembangan diri
set queries[10]=cara meditasi yang efektif
set queries[11]=resep makan malam cepat
set queries[12]=cara memulai podcast
set queries[13]=tips tidur lebih nyenyak
set queries[14]=cara meningkatkan daya ingat
set queries[15]=jalur hiking terbaik di dekat saya
set queries[16]=cara latihan untuk marathon
set queries[17]=tips traveling hemat
set queries[18]=cara merapikan rumah
set queries[19]=kursus coding online terbaik
set queries[20]=cara belajar bahasa baru
set queries[21]=aplikasi fitness dengan rating tertinggi
set queries[22]=cara mengurangi stres secara alami
set queries[23]=cara tetap termotivasi
set queries[24]=cara membuat kopi di rumah
set queries[25]=tips belajar jarak jauh
set queries[26]=cara mulai investasi
set queries[27]=alat edit foto gratis terbaik
set queries[28]=cara meningkatkan sistem imun
set queries[29]=10 hack produktivitas terbaik
set queries[30]=cara menulis resume
set queries[31]=tempat wisata terbaik di Eropa
set queries[32]=cara mengatur ruang kerja
set queries[33]=resep dessert mudah
set queries[34]=cara meningkatkan kemampuan komunikasi
set queries[35]=situs belanja online terbaik
set queries[36]=cara mengelola waktu dengan baik
set queries[37]=tips menjaga kesehatan mental
set queries[38]=cara membuat anggaran bulanan
set queries[39]=cara belajar public speaking
set queries[40]=rekomendasi film dokumenter
set queries[41]=cara mengurangi penggunaan plastik
set queries[42]=tips menjaga kebugaran saat bekerja dari rumah
set queries[43]=cara membuat smoothie sehat
set queries[44]=resep masakan vegetarian
set queries[45]=cara mengatur keuangan pribadi

:: ====================================

:: ====== HITUNG TOTAL QUERY =====
set "totalQueries=3"

:: Simpan endProfile ke var delayed
echo Mulai looping...

for /L %%i in (0,1,%totalQueries%-1) do (
    set "currentQuery=!queries[%%i]!"
    set "currentQuery=!currentQuery: =+!"

    set /a profileNum=%startProfile% + %%i

    echo -------------------------
    echo Loop index: %%i
    echo Profile number: !profileNum!
    echo Query: !queries[%%i]!

    set /a check=!profileNum! - !endProfile!

    echo Check: !check!

    if !check! LEQ 0 (
        echo Membuka Edge dengan Profile !profileNum! dan query: !queries[%%i]!
        start "" "!edgePath!" --profile-directory="Profile !profileNum!" "!searchEngine!!currentQuery!"

        echo Menunggu !waitSeconds! detik...
        timeout /t !waitSeconds! /nobreak

        echo Menutup Edge...
        taskkill /im msedge.exe /f
    ) else (
        echo Profil sudah melewati batas, selesai!
        goto end
    )
)

:end
echo Semua selesai!
pause
