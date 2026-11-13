# mymonitor

Tool monitoring sistem untuk Debian buatan sendiri, ditulis dengan Python
(hanya library bawaan). Alternatif sederhana untuk `htop`, sekaligus
latihan membaca `/proc`, membuat service systemd, dan membuat tool CLI.

## Fitur
- Memantau CPU, RAM, swap, disk, load, uptime, dan trafik jaringan
- Menyimpan data ke `metrics.csv` dan mencatat alert ke `alerts.log`
- Berjalan sebagai service systemd dengan hak akses terbatas
- `dashboard.py`: dashboard terminal live berwarna
- `top_mem.py`: proses dengan RAM terbesar
- `net_check.py`: cek gateway, DNS, internet, dan port yang listen
- `plot_svg.py`: grafik SVG dari data CSV

## Kebutuhan
- Debian (diuji di Debian 13 pada VMware)
- Python 3.x, tanpa pip

## Cara pakai
```bash
git clone https://github.com/USERNAME/mymonitor.git
cd mymonitor
python3 monitor.py --interval 5 --log-dir ./log   # pengumpul data
python3 dashboard.py                              # dashboard live
python3 top_mem.py -n 10                          # proses RAM terbesar
python3 net_check.py                              # cek jaringan
python3 plot_svg.py log/metrics.csv               # buat grafik
```

## Memasang sebagai service
```bash
sudo mkdir -p /opt/mymonitor
sudo cp monitor.py /opt/mymonitor/
sudo cp mymonitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mymonitor
```

## Yang saya pelajari
- Membaca data sistem langsung dari `/proc` dan `/sys`
- Menghitung persentase CPU dari selisih dua pembacaan
- Membuat dan mengamankan service systemd
- Memecah program jadi fungsi dan modul yang bisa dipakai ulang
- Bekerja lewat SSH dan Git

## Lisensi
ITB