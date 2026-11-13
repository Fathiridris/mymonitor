#!/usr/bin/env python3
"""dashboard.py - Dashboard terminal live untuk mymonitor
"""
import argparse
import os
import sys
import time
from datetime import datetime

import monitor   # collect(), THRESHOLDS
import top_mem   # top_processes(), total_ram_kb()

# Kode warna ANSI
RESET, BOLD = "\033[0m", "\033[1m"
GREEN, YELLOW, RED = "\033[32m", "\033[33m", "\033[31m"
CLEAR_EOL = "\033[K"  # hapus sisa baris


def color_for(key, value):
    limit = monitor.THRESHOLDS.get(key, 90.0)
    if value > limit:
        return RED
    if value > limit * 0.7:
        return YELLOW
    return GREEN


def bar(key, value, width=30):
    filled = int(min(value, 100) / 100 * width)
    return f"{color_for(key, value)}{'█' * filled}{'░' * (width - filled)}{RESET}"


def render(row, procs, total_kb):
    """Susun satu layar penuh dalam bentuk teks."""
    lines = [
        f"{BOLD}mymonitor dashboard{RESET} - {os.uname().nodename}   "
        f"{datetime.now():%H:%M:%S}   uptime {row['uptime_h']:.1f} jam",
        "",
    ]
    for key, label in [("cpu", "CPU "), ("ram", "RAM "), ("swap", "Swap"), ("disk", "Disk")]:
        v = row[key]
        lines.append(f" {label} {bar(key, v)} {color_for(key, v)}{v:5.1f}%{RESET}")
    lines.append("")
    lines.append(f" Load  {row['load1']}    Net  ↓ {row['rx_kbs']} KB/s   ↑ {row['tx_kbs']} KB/s")
    if row["temp"] != "":
        lines.append(f" Suhu  {row['temp']} °C")
    lines.append("")
    lines.append(f"{BOLD} {'PID':>7}  {'PROSES':<20} {'RAM(MB)':>8} {'%RAM':>6}{RESET}")
    for pid, name, rss in procs:
        lines.append(f" {pid:>7}  {name:<20} {rss / 1024:>8.1f} {100 * rss / total_kb:>5.1f}%")
    lines.append("")
    lines.append(" Tekan Ctrl+C untuk keluar")
    return "\n".join(line + CLEAR_EOL for line in lines)


def main():
    parser = argparse.ArgumentParser(description="Dashboard terminal live")
    parser.add_argument("--interval", type=float, default=2, help="detik antar refresh")
    parser.add_argument("-n", type=int, default=5, help="jumlah proses RAM teratas")
    args = parser.parse_args()

    total_kb = top_mem.total_ram_kb()
    prev_cpu, prev_net = monitor.read_cpu(), monitor.read_net()
    sys.stdout.write("\033[2J\033[?25l")  # bersihkan layar, sembunyikan kursor
    print("Mengukur...", flush=True)
    try:
        while True:
            time.sleep(args.interval)
            row, prev_cpu, prev_net = monitor.collect(prev_cpu, prev_net, args.interval)
            frame = render(row, top_mem.top_processes(args.n), total_kb)
            sys.stdout.write("\033[H" + frame + "\033[J")  # ke pojok kiri atas, timpa layar
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\n")  # tampilkan kursor lagi


if __name__ == "__main__":
    main()