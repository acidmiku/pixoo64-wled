#!/usr/bin/env python3
"""DDP streaming soak for the Pixoo 64 WLED build.
Sends a moving diagonal rainbow (mapping sanity: diagonal stripes expose any
row-major/serpentine error) as DDP frames to port 4048, PUSH only on the last
packet so WLED shows once per frame.

Usage: .venv/Scripts/python wled/soak_ddp.py [host] [fps] [secs]
"""
import socket
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.88.17"
FPS = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
SECS = float(sys.argv[3]) if len(sys.argv) > 3 else 240.0
PORT = 4048
W = H = 64
CHUNK = 1440  # DDP payload bytes per packet

# 256-entry rainbow palette (HSV-ish wheel, cheap)
pal = []
for i in range(256):
    p = i * 6
    seg, off = divmod(p, 256)
    seg %= 6
    q = 255 - off
    r, g, b = [(255, off, 0), (q, 255, 0), (0, 255, off),
               (0, q, 255), (off, 0, 255), (255, 0, q)][seg]
    pal.append((r, g, b))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

frame = bytearray(W * H * 3)
n_packets = (len(frame) + CHUNK - 1) // CHUNK
period = 1.0 / FPS
t = 0
sent = 0
t_start = time.time()
next_stat = t_start + 5.0
deadline = t_start + SECS

while time.time() < deadline:
    f0 = time.time()
    # diagonal moving rainbow: idx = x*2 + y*3 + t
    i = 0
    for y in range(H):
        base = y * 3 + t
        for x in range(W):
            r, g, b = pal[(base + x * 2) & 255]
            frame[i] = r
            frame[i + 1] = g
            frame[i + 2] = b
            i += 3
    for p in range(n_packets):
        off = p * CHUNK
        payload = frame[off:off + CHUNK]
        last = p == n_packets - 1
        hdr = bytes([0x40 | (0x01 if last else 0), 0, 0x01, 0x01,
                     (off >> 24) & 0xFF, (off >> 16) & 0xFF,
                     (off >> 8) & 0xFF, off & 0xFF,
                     (len(payload) >> 8) & 0xFF, len(payload) & 0xFF])
        sock.sendto(hdr + payload, (HOST, PORT))
    sent += 1
    t = (t + 1) & 255
    if time.time() >= next_stat:
        el = time.time() - t_start
        print(f"{el:6.0f}s: {sent} frames, {sent / el:.1f} fps actual", flush=True)
        next_stat += 5.0
    dt = period - (time.time() - f0)
    if dt > 0:
        time.sleep(dt)

el = time.time() - t_start
print(f"done: {sent} frames in {el:.0f}s ({sent / el:.1f} fps)")
