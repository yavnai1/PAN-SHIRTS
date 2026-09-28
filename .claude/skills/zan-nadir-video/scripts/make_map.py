#!/usr/bin/env python3
"""Locator map in Zan Nadir colors.

make_map.py --country GRC --lat 39.72 --lon 21.63 --out map.png [--ref "אתונה,37.98,23.73" ...]
Writes map.png (transparent rounded card, 2x) and map.json with label positions in % of the image,
so the HTML template can place Hebrew labels (PIL can't shape RTL text).
"""
import argparse, json, math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
COUNTRIES = os.path.join(HERE, '..', 'assets', 'countries_50m.json')

ap = argparse.ArgumentParser()
ap.add_argument('--country', required=True, help='ISO3 of the highlighted country, e.g. GRC, ITA, RWA')
ap.add_argument('--lat', type=float, required=True)
ap.add_argument('--lon', type=float, required=True)
ap.add_argument('--ref', action='append', default=[], help='"name,lat,lon" reference city (1-2 is enough)')
ap.add_argument('--w', type=int, default=740)
ap.add_argument('--h', type=int, default=660)
ap.add_argument('--span', type=float, default=0, help='force map height in degrees (zoom); 0 = fit country')
ap.add_argument('--out', required=True)
a = ap.parse_args()

feats = json.load(open(COUNTRIES))
home = [f for f in feats if f['id'] == a.country]
if not home:
    raise SystemExit(f'unknown ISO3 {a.country}')

# bbox of the highlighted country, ignoring far-away territories (e.g. overseas islands)
xs, ys = [], []
for poly in home[0]['coords']:
    ring = poly[0]
    cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
    if abs(cx - a.lon) < 12 and abs(cy - a.lat) < 10:
        xs += [p[0] for p in ring]; ys += [p[1] for p in ring]
lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
if a.span:
    lat0, lat1 = a.lat - a.span / 2, a.lat + a.span / 2
    lon0, lon1 = a.lon - a.span, a.lon + a.span
padx, pady = (lon1 - lon0) * 0.08 + 0.3, (lat1 - lat0) * 0.08 + 0.3
lon0, lon1, lat0, lat1 = lon0 - padx, lon1 + padx, lat0 - pady, lat1 + pady
k = math.cos(math.radians((lat0 + lat1) / 2))
# expand the shorter side so the box matches the image aspect
want = a.w / a.h; have = (lon1 - lon0) * k / (lat1 - lat0)
if have < want:
    extra = ((lat1 - lat0) * want / k - (lon1 - lon0)) / 2; lon0 -= extra; lon1 += extra
else:
    extra = ((lon1 - lon0) * k / want - (lat1 - lat0)) / 2; lat0 -= extra; lat1 += extra

SC = 3
W, H = a.w * SC, a.h * SC
def P(lon, lat):
    return ((lon - lon0) / (lon1 - lon0) * W, (lat1 - lat) / (lat1 - lat0) * H)

im = Image.new('RGBA', (W, H), (207, 226, 232, 255))  # sea
dr = ImageDraw.Draw(im)
def draw(f, fill, outline, width):
    for poly in f['coords']:
        ring = poly[0]
        if max(p[0] for p in ring) < lon0 - 5 or min(p[0] for p in ring) > lon1 + 5: continue
        if max(p[1] for p in ring) < lat0 - 5 or min(p[1] for p in ring) > lat1 + 5: continue
        dr.polygon([P(*p) for p in ring], fill=fill, outline=outline, width=width)
for f in feats:
    if f['id'] != a.country:
        draw(f, (242, 236, 222, 255), (190, 175, 150, 255), SC)
draw(home[0], (233, 211, 174, 255), (166, 90, 42, 255), 2 * SC)

labels = []
for r in a.ref:
    name, la, lo = r.rsplit(',', 2)
    x, y = P(float(lo), float(la))
    dr.ellipse([x - 5 * SC, y - 5 * SC, x + 5 * SC, y + 5 * SC], fill=(42, 24, 16, 255))
    labels.append({'name': name.strip(), 'x': x / W * 100, 'y': y / H * 100})
x, y = P(a.lon, a.lat)
dr.ellipse([x - 20 * SC, y - 20 * SC, x + 20 * SC, y + 20 * SC], fill=(166, 90, 42, 70))
dr.ellipse([x - 9 * SC, y - 9 * SC, x + 9 * SC, y + 9 * SC], fill=(166, 90, 42, 255), outline=(255, 255, 255, 255), width=3 * SC)

mask = Image.new('L', im.size, 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=16 * SC, fill=255)
out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.paste(im, (0, 0), mask)
out.resize((a.w * 2, a.h * 2), Image.LANCZOS).save(a.out)
json.dump({'pin': {'x': x / W * 100, 'y': y / H * 100}, 'refs': labels, 'w': a.w, 'h': a.h},
          open(os.path.splitext(a.out)[0] + '.json', 'w'), ensure_ascii=False)
print('map ->', a.out)
