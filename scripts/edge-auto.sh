#!/bin/bash

# ========= SETTINGAN PROFILE =========
startProfile=1
endProfile=6
searchEngine="https://www.google.com/search?q="
edgePath="/usr/bin/microsoft-edge"  # Sesuaikan lokasi Microsoft Edge di Linux
waitSeconds=1400
# =====================================

# ====== DAFTAR QUERY DI SINI =======
queries=(
  "cara membuat pancake"
  "destinasi wisata terbaik 2024"
  "rutinitas olahraga di rumah yang mudah"
  "ulasan smartphone terbaru"
  "cara menabung dengan cepat"
  "film terbaik untuk ditonton tahun ini"
  "tips berkebun sederhana"
  "cara belajar gitar online"
  "ide sarapan sehat"
  "buku terbaik untuk pengembangan diri"
  "cara meditasi yang efektif"
)
# ====================================

totalQueries=7
skipCurrent=false

# Trap untuk menangani Ctrl+C (SIGINT)
trap 'echo; echo ">> Skip current profile requested!"; skipCurrent=true' SIGINT

echo "Mulai looping..."

for ((i=0; i<totalQueries; i++)); do
    currentQuery="${queries[$i]}"
    currentQueryEncoded="${currentQuery// /+}"  # ganti spasi dengan +

    profileNum=$((startProfile + i))
    echo "-------------------------"
    echo "Loop index: $i"
    echo "Profile number: $profileNum"
    echo "Query: ${queries[$i]}"

    check=$((profileNum - endProfile))
    echo "Check: $check"

    if [[ $check -le 0 ]]; then
        echo "Membuka Edge dengan Profile $profileNum dan query: ${queries[$i]}"
        "$edgePath" --profile-directory="Profile $profileNum" "${searchEngine}${currentQueryEncoded}" &

        echo "Menunggu $waitSeconds detik... (Tekan Ctrl+C untuk skip)"
        
        # Tunggu dengan countdown & cek skip
        for ((t=waitSeconds; t>0; t--)); do
            if $skipCurrent; then
                echo "Skipping profile $profileNum..."
                skipCurrent=false
                break
            fi
            sleep 1
        done

        echo "Menutup Edge..."
        pkill -f "microsoft-edge"

    else
        echo "Profil sudah melewati batas, selesai!"
        break
    fi
done

echo "Semua selesai!"
read
