# -*- coding: utf-8 -*-
"""Generate a simple 512x512 icon.png for the addon (pure stdlib)."""
import math
import os
import struct
import zlib

SIZE = 512
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'weather.metno', 'resources', 'icon.png')


def in_circle(x, y, cx, cy, r):
    return math.hypot(x - cx, y - cy) <= r


def make_rows():
    rows = []
    for y in range(SIZE):
        t = y / SIZE
        sky = (int(25 + 70 * t), int(70 + 95 * t), int(135 + 85 * t))
        row = bytearray([0])  # filter type 0
        for x in range(SIZE):
            r, g, b = sky
            # sun with a soft rim
            d = math.hypot(x - 165, y - 155)
            if d < 95:
                r, g, b = 255, 205, 60
            elif d < 110:
                f = (110 - d) / 15
                r = int(r + (255 - r) * f)
                g = int(g + (205 - g) * f)
                b = int(b + (60 - b) * f)
            # cloud: three lobes + a flat base
            if (in_circle(x, y, 245, 345, 78)
                    or in_circle(x, y, 340, 305, 96)
                    or in_circle(x, y, 428, 350, 72)
                    or (245 <= x <= 428 and 350 <= y <= 420)):
                r, g, b = 245, 248, 252
            row += bytes((r, g, b))
        rows.append(bytes(row))
    return b''.join(rows)


def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))


def main():
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(make_rows(), 9))
    png += chunk(b'IEND', b'')
    with open(OUT, 'wb') as f:
        f.write(png)
    print('wrote %s (%i bytes)' % (OUT, len(png)))


if __name__ == '__main__':
    main()
