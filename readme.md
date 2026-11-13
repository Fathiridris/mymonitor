# mymonitor

Tool monitoring sistem untuk Debian buatan sendiri, ditulis dengan Python. Dibuat sebagai alternatif sederhana untuk
`htop`, sekaligus latihan membaca `/proc`, membuat service systemd, dan
membuat tool CLI serta dashboard web

![Dashboard web mymonitor](docs/dashboard-web.png)

## Fitur
- Memantau CPU, RAM, swap, disk, load, uptime, suhu, dan trafik jaringan
- Menyimpan data ke `metrics.csv` dan mencatat alert ke `alerts.log`
- Berjalan sebagai service systemd dengan hak akses terbatas
- `web_dashboard.py`: dashboard web dengan grafik riwayat dan tabel proses
- `dashboard.py`: dashboard terminal live berwarna
- `top_mem.py`: proses dengan RAM terbesar
- `net_check.py`: cek gateway, DNS, internet, dan port yang listen
- `plot_svg.py`: grafik SVG dari data CSV

## Struktur
```
mymonitor/
├── monitor.py          # pengumpul data (inti, dipakai file lain)
├── top_mem.py          # proses RAM terbesar
├── net_check.py        # cek jaringan
├── plot_svg.py         # grafik dari CSV
├── dashboard.py        # dashboard terminal
├── web_dashboard.py    # dashboard web
├── mymonitor.service   # unit file systemd
└── docs/               # gambar untuk README
```

## Kebutuhan
- Debian (diuji di Debian 13 pada VMware)
- Python 3.x, tanpa pip

## Cara pakai
```bash
git clone https://github.com/Fathiridris/mymonitor.git
cd mymonitor
python3 monitor.py --interval 5 --log-dir ./log   # pengumpul data
python3 dashboard.py                              # dashboard terminal
python3 web_dashboard.py                          # dashboard web
python3 top_mem.py -n 10                          # proses RAM terbesar
python3 net_check.py                              # cek jaringan
python3 plot_svg.py log/metrics.csv               # buat grafik
```

## Dashboard web
```bash
python3 web_dashboard.py                  # http://127.0.0.1:8000
python3 web_dashboard.py --port 9000 --interval 1
```
Dashboard ini **tidak punya login**, jadi secara bawaan hanya mendengarkan
`127.0.0.1` (lokal). Untuk membukanya dari komputer lain, teruskan portnya
lewat SSH (`ssh -L 8000:127.0.0.1:8000 user@host`) atau lewat fitur
Ports di VS Code Remote-SSH. Jangan membukanya langsung ke internet.

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
- Membuat dan mengamankan service systemd (`DynamicUser`, `ProtectSystem`)
- Memecah program jadi fungsi dan modul yang bisa dipakai ulang
- Membuat server HTTP kecil, API JSON, dan halaman yang diperbarui JavaScript
- Thread dan `Lock` untuk berbagi data antar proses latar belakang
- Bekerja lewat SSH dan Git

## Lisensi
ITB