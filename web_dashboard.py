#!/usr/bin/env python3
"""web_dashboard.py - Dashboard monitoring berbasis web (stdlib saja).

Memakai ulang monitor.py dan top_mem.py (taruh satu folder).
Server kecil ini melayani dua alamat:
    /              halaman HTML (tampilan)
    /api/metrics   data JSON (diambil JavaScript tiap 2 detik)

Pemakaian:
    python3 web_dashboard.py                   # http://127.0.0.1:8000
    python3 web_dashboard.py --port 9000 --interval 1
Keluar: Ctrl+C
"""
import argparse
import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import monitor   # collect(), THRESHOLDS
import top_mem   # top_processes(), total_ram_kb()

HISTORY = deque(maxlen=120)  # 120 pengukuran terakhir
STATE = {"procs": []}
LOCK = threading.Lock()      # supaya thread pengukur dan thread server tidak bentrok


def sampler(interval, nproc):
    """Thread latar belakang: ukur terus-menerus dan simpan hasilnya."""
    total_kb = top_mem.total_ram_kb()
    prev_cpu, prev_net = monitor.read_cpu(), monitor.read_net()
    while True:
        time.sleep(interval)
        row, prev_cpu, prev_net = monitor.collect(prev_cpu, prev_net, interval)
        procs = [
            {"pid": pid, "name": name, "mb": round(rss / 1024, 1),
             "pct": round(100 * rss / total_kb, 1)}
            for pid, name, rss in top_mem.top_processes(nproc)
        ]
        with LOCK:
            HISTORY.append(row)
            STATE["procs"] = procs


PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mymonitor</title>
<style>
  :root {
    --bg: #f5f6f8; --card: #ffffff; --text: #1d2330; --muted: #6b7384;
    --line: #e1e4ea; --ok: #2e9e5b; --warn: #d9a21b; --bad: #d64545;
    --cpu: #2f6fdd; --ram: #e07a1f;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #11141b; --card: #1a1f2a; --text: #e6e9f0; --muted: #8b93a7;
      --line: #2a3140; --ok: #4cc27f; --warn: #e8b84a; --bad: #ef6b6b;
      --cpu: #6c9bff; --ram: #f2a05a;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 20px; background: var(--bg); color: var(--text);
         font-family: system-ui, sans-serif; }
  header { display: flex; justify-content: space-between; align-items: baseline;
           flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  h1 { font-size: 20px; margin: 0; }
  #status { font-size: 13px; color: var(--muted); }
  .grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px; }
  .card h2 { font-size: 13px; margin: 0 0 8px; color: var(--muted); font-weight: 600; }
  .value { font-size: 26px; font-weight: 600; }
  .bar { height: 8px; background: var(--line); border-radius: 4px; margin-top: 8px; overflow: hidden; }
  .fill { height: 100%; width: 0; background: var(--ok); transition: width .4s; }
  .fill.warn { background: var(--warn); } .fill.bad { background: var(--bad); }
  .wide { margin-top: 12px; }
  svg { width: 100%; height: 160px; display: block; }
  .legend { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .legend b { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
              margin: 0 4px 0 12px; vertical-align: middle; }
  .legend b:first-child { margin-left: 0; }
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 600; font-size: 12px; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<header>
  <h1>mymonitor - <span id="host">...</span></h1>
  <div id="status">Mengukur...</div>
</header>

<div class="grid" id="meters"></div>

<div class="card wide">
  <h2>Riwayat CPU dan RAM</h2>
  <svg id="chart" viewBox="0 0 600 160" preserveAspectRatio="none"></svg>
  <div class="legend"><b style="background:var(--cpu)"></b>CPU
    <b style="background:var(--ram)"></b>RAM</div>
</div>

<div class="grid wide">
  <div class="card"><h2>Jaringan</h2><div id="net" class="value" style="font-size:18px">-</div></div>
  <div class="card"><h2>Load rata-rata (1 menit)</h2><div id="load" class="value">-</div></div>
  <div class="card"><h2>Uptime</h2><div id="uptime" class="value">-</div></div>
</div>

<div class="card wide">
  <h2>Proses dengan RAM terbesar</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th class="num">PID</th><th>Proses</th>
        <th class="num">RAM (MB)</th><th class="num">% RAM</th></tr></thead>
      <tbody id="procs"></tbody>
    </table>
  </div>
</div>

<script>
const METERS = [["cpu", "CPU"], ["ram", "RAM"], ["swap", "Swap"], ["disk", "Disk"]];
const meters = document.getElementById("meters");

// Buat kartu meter sekali saja
for (const [key, label] of METERS) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = '<h2></h2><div class="value">-</div><div class="bar"><div class="fill"></div></div>';
  card.querySelector("h2").textContent = label;
  card.id = "m-" + key;
  meters.appendChild(card);
}

function level(key, value, limits) {
  const limit = limits[key] !== undefined ? limits[key] : 90;
  if (value > limit) return "bad";
  if (value > limit * 0.7) return "warn";
  return "";
}

function line(values, color) {
  const n = values.length;
  const pts = values.map((v, i) => {
    const x = n > 1 ? (i / (n - 1)) * 600 : 0;
    const y = 160 - Math.min(v, 100) / 100 * 160;
    return x.toFixed(1) + "," + y.toFixed(1);
  }).join(" ");
  return '<polyline fill="none" stroke="' + color + '" stroke-width="2" points="' + pts + '"/>';
}

function render(d) {
  document.getElementById("host").textContent = d.host;
  if (d.history.length === 0) return;
  const last = d.history[d.history.length - 1];

  for (const [key] of METERS) {
    const card = document.getElementById("m-" + key);
    const lv = level(key, last[key], d.limits);
    card.querySelector(".value").textContent = last[key].toFixed(1) + "%";
    const fill = card.querySelector(".fill");
    fill.style.width = Math.min(last[key], 100) + "%";
    fill.className = "fill " + lv;
  }

  const chart = document.getElementById("chart");
  let grid = "";
  for (let i = 1; i < 4; i++) {
    const y = i * 40;
    grid += '<line x1="0" x2="600" y1="' + y + '" y2="' + y +
            '" stroke="var(--line)" stroke-width="1"/>';
  }
  chart.innerHTML = grid + line(d.history.map(r => r.cpu), "var(--cpu)")
                         + line(d.history.map(r => r.ram), "var(--ram)");

  document.getElementById("net").textContent =
    "Download " + last.rx_kbs + " KB/s  |  Upload " + last.tx_kbs + " KB/s";
  document.getElementById("load").textContent = last.load1;
  document.getElementById("uptime").textContent = last.uptime_h.toFixed(1) + " jam";

  const tbody = document.getElementById("procs");
  tbody.innerHTML = "";
  for (const p of d.procs) {
    const tr = document.createElement("tr");
    for (const [val, cls] of [[p.pid, "num"], [p.name, ""], [p.mb, "num"], [p.pct, "num"]]) {
      const td = document.createElement("td");
      td.textContent = val;      // textContent: aman dari HTML nyasar
      if (cls) td.className = cls;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function refresh() {
  const status = document.getElementById("status");
  try {
    const res = await fetch("/api/metrics", { cache: "no-store" });
    const data = await res.json();
    render(data);
    status.textContent = "Diperbarui " + new Date().toLocaleTimeString("id-ID");
  } catch (e) {
    status.textContent = "Terputus dari server, mencoba lagi...";
  }
}
refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.reply(200, "text/html; charset=utf-8", PAGE.encode())
        elif self.path == "/api/metrics":
            with LOCK:
                payload = {
                    "host": os.uname().nodename,
                    "limits": monitor.THRESHOLDS,
                    "history": list(HISTORY),
                    "procs": STATE["procs"],
                }
            self.reply(200, "application/json", json.dumps(payload).encode())
        else:
            self.reply(404, "text/plain; charset=utf-8", b"Tidak ditemukan")

    def reply(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # diamkan log tiap permintaan supaya terminal tidak penuh


def main():
    parser = argparse.ArgumentParser(description="Dashboard monitoring web")
    parser.add_argument("--host", default="127.0.0.1",
                        help="alamat yang didengarkan (default 127.0.0.1, hanya lokal)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--interval", type=float, default=2, help="detik antar pengukuran")
    parser.add_argument("-n", type=int, default=5, help="jumlah proses teratas")
    args = parser.parse_args()

    threading.Thread(target=sampler, args=(args.interval, args.n), daemon=True).start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Dashboard berjalan di http://{args.host}:{args.port}  (Ctrl+C untuk berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDihentikan.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()