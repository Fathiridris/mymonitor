#!/usr/bin/env python3
"""net_check.py - Cek kondisi jaringan

Pemakaian:
    python3 net_check.py              # cek sekali
    python3 net_check.py --watch 10   # ulangi tiap 10 detik (Ctrl+C untuk berhenti)
Kode keluar: 0 = internet OK, 1 = internet bermasalah.
"""
import argparse
import os
import shutil
import socket
import struct
import subprocess
import time
from datetime import datetime

TCP_TARGETS = [("1.1.1.1", 443), ("8.8.8.8", 53)]
DNS_TEST_HOST = "google.com"


def interfaces():
    """Daftar (nama, status) dari /sys/class/net, tanpa loopback."""
    base = "/sys/class/net"
    result = []
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if name == "lo":
            continue
        try:
            with open(f"{base}/{name}/operstate") as f:
                result.append((name, f.read().strip()))
        except OSError:
            continue
    return result


def default_gateway():
    """Cari gateway bawaan dari /proc/net/route, atau None."""
    try:
        with open("/proc/net/route") as f:
            for line in list(f)[1:]:
                cols = line.split()
                if cols[1] == "00000000":  # tujuan 0.0.0.0 = rute bawaan
                    return socket.inet_ntoa(struct.pack("<L", int(cols[2], 16)))
    except (OSError, IndexError, ValueError):
        pass
    return None


def ping_ms(host):
    """Ping 1x lewat perintah 'ping'. Kembalikan ms, atau None kalau gagal."""
    if not shutil.which("ping"):
        return None
    try:
        out = subprocess.run(["ping", "-c", "1", "-W", "2", host],
                             capture_output=True, text=True, timeout=5).stdout
    except (subprocess.TimeoutExpired, OSError):
        return None
    if "time=" in out:
        return float(out.split("time=")[1].split()[0])
    return None


def tcp_ms(host, port, timeout=3):
    """Ukur waktu koneksi TCP dalam ms, atau None kalau gagal."""
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.perf_counter() - start) * 1000
    except OSError:
        return None


def dns_ms(host):
    """Ukur waktu resolusi DNS. Kembalikan (ms, ip) atau (None, None)."""
    start = time.perf_counter()
    try:
        ip = socket.gethostbyname(host)
        return (time.perf_counter() - start) * 1000, ip
    except OSError:
        return None, None


def listening_ports():
    """Port TCP yang sedang LISTEN, dibaca dari /proc/net/tcp dan tcp6."""
    ports = set()
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path) as f:
                for line in list(f)[1:]:
                    cols = line.split()
                    if cols[3] == "0A":  # 0A = LISTEN
                        ports.add(int(cols[1].split(":")[1], 16))
        except OSError:
            continue
    return sorted(ports)


def fmt(ms):
    return f"{ms:.1f} ms" if ms is not None else "GAGAL"


def run_check():
    """Jalankan semua cek, cetak hasilnya, kembalikan True kalau internet OK."""
    print(f"== Cek jaringan {datetime.now():%H:%M:%S} ==")
    for name, state in interfaces():
        print(f"Interface : {name} ({state})")

    gw = default_gateway()
    if gw:
        print(f"Gateway   : {gw}  ping {fmt(ping_ms(gw))}")
    else:
        print("Gateway   : tidak ditemukan (tidak ada rute bawaan)")

    ms, ip = dns_ms(DNS_TEST_HOST)
    print(f"DNS       : {DNS_TEST_HOST} -> {ip or '-'}  {fmt(ms)}")

    internet_ok = False
    for host, port in TCP_TARGETS:
        ms = tcp_ms(host, port)
        internet_ok = internet_ok or ms is not None
        print(f"TCP       : {host}:{port}  {fmt(ms)}")

    names = []
    for p in listening_ports():
        try:
            names.append(f"{p}/{socket.getservbyport(p)}")
        except OSError:
            names.append(str(p))
    print("Port LISTEN:", ", ".join(names) or "-")
    print("Status    :", "INTERNET OK" if internet_ok else "INTERNET BERMASALAH")
    return internet_ok


def main():
    parser = argparse.ArgumentParser(description="Cek kondisi jaringan")
    parser.add_argument("--watch", type=float, metavar="DETIK",
                        help="ulangi cek tiap N detik")
    args = parser.parse_args()

    if not args.watch:
        raise SystemExit(0 if run_check() else 1)
    try:
        while True:
            run_check()
            print()
            time.sleep(args.watch)
    except KeyboardInterrupt:
        print("Dihentikan.")


if __name__ == "__main__":
    main()
