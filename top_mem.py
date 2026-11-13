#!/usr/bin/env python3
"""top_mem.py - Tampilkan proses dengan pemakaian RAM terbesar

Pemakaian:
    python3 top_mem.py          # 5 proses teratas
    python3 top_mem.py -n 10    # 10 proses teratas
"""
import argparse
import os


def total_ram_kb():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal"):
                return int(line.split()[1])
    return 1


def read_process(pid):
    """Kembalikan (nama, rss_kb) dari /proc/<pid>/status, atau None."""
    name, rss = None, None
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("Name:"):
                    name = line.split()[1]
                elif line.startswith("VmRSS:"):
                    rss = int(line.split()[1])  # kB
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return None  # proses sudah selesai atau tidak boleh dibaca
    if name is None or rss is None:
        return None  # thread kernel tidak punya VmRSS
    return name, rss


def top_processes(limit):
    procs = []
    for entry in os.listdir("/proc"):
        if entry.isdigit():  # folder angka = PID
            result = read_process(entry)
            if result:
                procs.append((int(entry), result[0], result[1]))
    procs.sort(key=lambda p: p[2], reverse=True)
    return procs[:limit]


def main():
    parser = argparse.ArgumentParser(description="Proses dengan RAM terbesar")
    parser.add_argument("-n", type=int, default=5, help="jumlah proses (default 5)")
    args = parser.parse_args()

    total = total_ram_kb()
    print(f"{'PID':>7}  {'NAMA':<20} {'RAM (MB)':>9} {'% RAM':>7}")
    print("-" * 47)
    for pid, name, rss in top_processes(args.n):
        print(f"{pid:>7}  {name:<20} {rss / 1024:>9.1f} {100 * rss / total:>6.1f}%")


if __name__ == "__main__":
    main()
