"""Generate the placeholder Kiko app icon (1024x1024 PNG) without third-party packages.

Replace apps/desktop/assets/icon-source.png with the final Pixart brand mark and run
`pnpm --filter @agent/desktop tauri icon assets/icon-source.png`.
"""

import struct
import sys
import zlib

SIZE = 1024
SS = 2  # supersampling factor per axis


def inside_rounded_rect(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def inside_polygon(x, y, pts):
    hit = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


# Letter K built from three polygons (stem, upper arm, lower leg).
STEM = [(340, 280), (450, 280), (450, 744), (340, 744)]
ARM = [(450, 520), (640, 280), (775, 280), (520, 590)]
LEG = [(450, 610), (450, 500), (560, 470), (790, 744), (650, 744)]


def pixel(px, py):
    acc = [0.0, 0.0, 0.0, 0.0]
    for sy in range(SS):
        for sx in range(SS):
            x = px + (sx + 0.5) / SS
            y = py + (sy + 0.5) / SS
            if not inside_rounded_rect(x, y, 100, 100, 924, 924, 185):
                continue
            t = (x + y) / (2 * SIZE)
            r, g, b = 28 + 40 * t, 46 + 70 * t, 120 + 110 * t  # deep indigo → blue
            if inside_polygon(x, y, STEM) or inside_polygon(x, y, ARM) or inside_polygon(x, y, LEG):
                r, g, b = 246, 248, 255
            acc[0] += r
            acc[1] += g
            acc[2] += b
            acc[3] += 255
    n = SS * SS
    alpha = acc[3] / n
    if alpha == 0:
        return (0, 0, 0, 0)
    cover = acc[3] / 255
    return tuple(int(c / cover) for c in acc[:3]) + (int(alpha),)


def write_png(path):
    rows = []
    for y in range(SIZE):
        row = bytearray([0])
        for x in range(SIZE):
            row.extend(pixel(x, y))
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


write_png(sys.argv[1])
