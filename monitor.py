#!/usr/bin/env python3
"""mymonitor - System monitor sederhana untuk Debian
"""
import argparse
import csv
import logging
import os
import shutil
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
# Ambang batas alert (persen, suhu dalam derajat Celsius)
THRESHOLDS = {"cpu": 90.0, "ram": 85.0, "disk": 85.0, "temp": 80.0}

# Jeda minimal (detik) antar catatan alert untuk metrik yang sama
COOLDOWN = 600

log = logging.getLogger("mymonitor")


# ---------------------------------------------------------------------------
# Pembaca data dari /proc dan /sys
# ---------------------------------------------------------------------------
def read_cpu():
    """Kembalikan (idle, total) dari baris 'cpu' di /proc/stat."""
    with open("/proc/stat") as f:
        vals = list(map(int, f.readline().split()[1:]))
    idle = vals[3] + vals[4]  # idle + iowait
    return idle, sum(vals)


def read_meminfo():
    """Kembalikan dictionary isi /proc/meminfo (satuan kB)."""
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, val = line.split(":")
            info[key] = int(val.split()[0])
    return info


def read_net():
    """Total byte masuk/keluar semua interface kecuali loopback."""
    rx = tx = 0
    with open("/proc/net/dev") as f:
        for line in list(f)[2:]:
            name, data = line.split(":")
            if name.strip() == "lo":
                continue
            cols = data.split()
            rx += int(cols[0])
            tx += int(cols[8])
    return rx, tx


def read_temp():
    """Suhu tertinggi (Celsius) dari sensor yang ada, atau None.

    Di mesin virtual biasanya tidak ada sensor, jadi hasilnya None.
    """
    temps = []
    sources = [
        "/sys/class/thermal/thermal_zone{}/temp",
        "/sys/class/hwmon/hwmon{}/temp1_input",
    ]
    for pattern in sources:
        for i in range(20):
            try:
                with open(pattern.format(i)) as f:
                    temps.append(int(f.read()) / 1000)
            except (OSError, ValueError):
                continue
    return max(temps) if temps else None


# ---------------------------------------------------------------------------
# Pengumpulan data
# ---------------------------------------------------------------------------
def collect(prev_cpu, prev_net, interval):
    """Ukur semua metrik. Kembalikan (baris_data, cpu_baru, net_baru)."""
    # CPU: persentase dihitung dari SELISIH dua pembacaan
    idle, total = read_cpu()
    d_total = total - prev_cpu[1]
    cpu = 100 * (1 - (idle - prev_cpu[0]) / d_total) if d_total else 0.0

    # RAM dan swap
    mem = read_meminfo()
    ram = 100 * (mem["MemTotal"] - mem["MemAvailable"]) / mem["MemTotal"]
    swap_total = mem.get("SwapTotal", 0)
    swap = 100 * (swap_total - mem["SwapFree"]) / swap_total if swap_total else 0.0

    # Disk (partisi root)
    du = shutil.disk_usage("/")
    disk = 100 * du.used / du.total

    # Jaringan: KB/s dari selisih byte
    rx, tx = read_net()
    rx_kbs = (rx - prev_net[0]) / 1024 / interval
    tx_kbs = (tx - prev_net[1]) / 1024 / interval

    # Beban sistem dan uptime
    with open("/proc/loadavg") as f:
        load1 = float(f.read().split()[0])
    with open("/proc/uptime") as f:
        uptime_h = float(f.read().split()[0]) / 3600

    temp = read_temp()  # dipanggil sekali saja

    row = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "cpu": round(cpu, 1),
        "ram": round(ram, 1),
        "swap": round(swap, 1),
        "disk": round(disk, 1),
        "load1": load1,
        "temp": round(temp, 1) if temp is not None else "",
        "rx_kbs": round(rx_kbs, 1),
        "tx_kbs": round(tx_kbs, 1),
        "uptime_h": round(uptime_h, 2),
    }
    return row, (idle, total), (rx, tx)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
def check_alerts(row, alert_file, last_alert):
    """Catat peringatan kalau metrik melewati batas.

    Selalu ke log (journal). Ke alerts.log hanya kalau cooldown sudah lewat,
    supaya file tidak penuh saat kondisi buruk berlangsung lama.
    """
    now = time.time()
    for key, limit in THRESHOLDS.items():
        value = row.get(key)
        if value in ("", None) or value <= limit:
            continue
        log.warning("ALERT: %s = %s (batas %s)", key, value, limit)
        if now - last_alert.get(key, 0) > COOLDOWN:
            last_alert[key] = now
            with open(alert_file, "a") as f:
                f.write(f"{row['time']} {key}={value} (batas {limit})\n")


# ---------------------------------------------------------------------------
# Program utama
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="System monitor sederhana")
    parser.add_argument("--interval", type=float, default=5,
                        help="detik antar pengukuran (default 5)")
    parser.add_argument("--log-dir", default=".",
                        help="folder untuk metrics.csv dan alerts.log")
    parser.add_argument("--once", action="store_true",
                        help="ukur sekali lalu keluar")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(args.log_dir, exist_ok=True)
    csv_path = os.path.join(args.log_dir, "metrics.csv")
    alert_file = os.path.join(args.log_dir, "alerts.log")
    new_file = not os.path.exists(csv_path)

    prev_cpu, prev_net = read_cpu(), read_net()
    last_alert = {}
    log.info("Monitoring dimulai, interval %ss, log di %s", args.interval, args.log_dir)

    with open(csv_path, "a", newline="") as f:
        writer = None
        try:
            while True:
                time.sleep(args.interval)
                row, prev_cpu, prev_net = collect(prev_cpu, prev_net, args.interval)

                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    if new_file:
                        writer.writeheader()
                writer.writerow(row)
                f.flush()

                check_alerts(row, alert_file, last_alert)
                print(
                    f"[{row['time']}] CPU {row['cpu']}% | RAM {row['ram']}% | "
                    f"Disk {row['disk']}% | Load {row['load1']} | "
                    f"Net ↓{row['rx_kbs']} ↑{row['tx_kbs']} KB/s",
                    flush=True,
                )
                if args.once:
                    break
        except KeyboardInterrupt:
            log.info("Dihentikan.")


if __name__ == "__main__":
    main()