#!/usr/bin/env python3
"""plot_svg.py - Grafik dari metrics.csv

Pemakaian:
    python3 plot_svg.py                      # baca /var/log/mymonitor/metrics.csv
    python3 plot_svg.py data.csv hasil.svg   # file CSV dan output sendiri
Hasil: file .svg + ringkasan sparkline di terminal.
"""
import csv
import sys
from datetime import datetime

csv_path = sys.argv[1] if len(sys.argv) > 1 else "/var/log/mymonitor/metrics.csv"
out_path = sys.argv[2] if len(sys.argv) > 2 else "grafik.svg"

# --- 1. Baca data ---------------------------------------------------------
cols = ["cpu", "ram", "disk", "rx_kbs", "tx_kbs"]
times = []
data = {c: [] for c in cols}
with open(csv_path) as f:
    for row in csv.DictReader(f):
        times.append(datetime.fromisoformat(row["time"]))
        for c in cols:
            data[c].append(float(row[c]))

if len(times) < 2:
    sys.exit("Data belum cukup, tunggu service mengumpulkan data dulu.")

# --- 2. Fungsi menggambar satu panel grafik -------------------------------
W, H = 800, 260                    # ukuran satu panel
ML, MR, MT, MB = 55, 20, 30, 30    # margin kiri, kanan, atas, bawah
COLORS = ["#e41a1c", "#377eb8", "#4daf4a"]


def panel(y0, title, series, ymax):
    """Kembalikan potongan SVG untuk satu panel. series = [(nama, nilai)]"""
    pw, ph = W - ML - MR, H - MT - MB
    t0, t1 = times[0].timestamp(), times[-1].timestamp()
    span = (t1 - t0) or 1
    out = [f'<text x="{ML}" y="{y0 + 18}" font-size="14" font-weight="bold">{title}</text>']
    # garis bantu horizontal + label sumbu Y
    for i in range(5):
        y = y0 + MT + ph - ph * i / 4
        out.append(f'<line x1="{ML}" y1="{y}" x2="{W - MR}" y2="{y}" stroke="#ddd"/>')
        out.append(f'<text x="{ML - 6}" y="{y + 4}" font-size="11" text-anchor="end">{ymax * i / 4:.0f}</text>')
    # label waktu awal dan akhir (sumbu X)
    base = y0 + MT + ph + 16
    out.append(f'<text x="{ML}" y="{base}" font-size="11">{times[0]:%H:%M:%S}</text>')
    out.append(f'<text x="{W - MR}" y="{base}" font-size="11" text-anchor="end">{times[-1]:%H:%M:%S}</text>')
    # garis data + legenda
    for n, (name, vals) in enumerate(series):
        pts = " ".join(
            f"{ML + (t.timestamp() - t0) / span * pw:.1f},"
            f"{y0 + MT + ph - min(v, ymax) / ymax * ph:.1f}"
            for t, v in zip(times, vals)
        )
        color = COLORS[n % len(COLORS)]
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        lx = W - MR - 150
        ly = y0 + 18 + n * 14
        out.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{color}"/>')
        out.append(f'<text x="{lx + 14}" y="{ly}" font-size="11">{name}</text>')
    return "\n".join(out)


# --- 3. Susun SVG ---------------------------------------------------------
net_max = max(max(data["rx_kbs"]), max(data["tx_kbs"]), 1) * 1.1
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H * 2}" '
    f'viewBox="0 0 {W} {H * 2}" font-family="sans-serif">',
    f'<rect width="{W}" height="{H * 2}" fill="white"/>',
    panel(0, "Pemakaian Sistem (%)",
          [("CPU %", data["cpu"]), ("RAM %", data["ram"]), ("Disk %", data["disk"])], 100),
    panel(H, "Trafik Jaringan (KB/s)",
          [("Download", data["rx_kbs"]), ("Upload", data["tx_kbs"])], net_max),
    "</svg>",
]
with open(out_path, "w") as f:
    f.write("\n".join(svg))
print(f"Grafik tersimpan: {out_path} ({len(times)} titik data)")

# --- 4. Sparkline di terminal --------------------------------------------
BLOCKS = "▁▂▃▄▅▆▇█"


def spark(vals, top):
    step = max(1, len(vals) // 60)          # maksimal ~60 karakter
    return "".join(BLOCKS[min(7, int(v / top * 7.999))] for v in vals[::step])


print(f"CPU  {spark(data['cpu'], 100)}")
print(f"RAM  {spark(data['ram'], 100)}")
