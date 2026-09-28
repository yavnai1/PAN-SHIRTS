#!/usr/bin/env python3
"""Zan Nadir branded video: intro slide (logo + place + map) -> captioned video with
info cards -> end slide.

    python3 build.py project.json [--draft]

See ../SKILL.md for the project.json schema. Intermediate files go to <out>.work/
and are reused on re-runs (delete a file to force that step again).
"""
import json, os, subprocess, sys, shutil, re, math

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL, 'assets')
CACHE = os.environ.get('ZN_CACHE', os.path.expanduser('~/.cache/zan-nadir-video'))
FF = os.path.join(CACHE, 'ffmpeg')

def run(cmd, **kw):
    print('+', ' '.join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    return subprocess.run(cmd, check=True, **kw)

def probe(path):
    out = subprocess.run([FF, '-i', path], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out)
    wh = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', out)
    rot = re.search(r'rotat\w*\s*:\s*(-?\d+)', out)
    d = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])
    w, h = int(wh[1]), int(wh[2])
    if rot and abs(int(rot[1])) in (90, 270): w, h = h, w
    return d, w, h

cfg = json.load(open(sys.argv[1]))
base = os.path.dirname(os.path.abspath(sys.argv[1]))
P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
video, out = P(cfg['video']), P(cfg['out'])
work = out + '.work'; os.makedirs(work, exist_ok=True)
if not os.path.exists(FF):
    sys.exit('run scripts/setup.sh first')

dur, sw, sh = probe(video)
t0, t1 = cfg.get('trim', [0, dur])
D = round(t1 - t0, 3)
layout = cfg.get('layout', 'original')
vertical_canvas = layout == 'vertical' or (layout == 'original' and sh > sw)
W, H = (1080, 1920) if vertical_canvas else (1920, 1080)
print(f'source {sw}x{sh} {dur:.1f}s -> {W}x{H}, clip {t0}-{t1}')

# 1) audio: speech enhancement ------------------------------------------------
clean = os.path.join(work, 'clean.wav')
if not os.path.exists(clean):
    rn = os.path.join(ASSETS, 'sh.rnnn')
    af = ('pan=mono|c0=0.5*c0+0.5*c1,highpass=f=90:poles=2,'
          f"arnndn=m='{rn}':mix={cfg.get('denoise', 1.0)},afftdn=nr=8:nf=-45:tn=1,"
          'equalizer=f=220:t=q:w=1:g=-3,equalizer=f=3000:t=q:w=1:g=4,equalizer=f=6500:t=q:w=1.2:g=2,'
          'acompressor=threshold=-26dB:ratio=3.5:attack=8:release=140:makeup=3,alimiter=limit=0.9,'
          'loudnorm=I=-14:TP=-1.5:LRA=8,aresample=48000,pan=stereo|c0=c0|c1=c0')
    run([FF, '-v', 'error', '-y', '-ss', str(t0), '-t', str(D), '-i', video, '-vn', '-af', af, '-c:a', 'pcm_s16le', clean])

# 2) word timing (whisper) + 3) align the user's transcript -------------------
words = os.path.join(work, 'words.json')
if not os.path.exists(words):
    f32 = os.path.join(work, 'a.f32')
    run([FF, '-v', 'error', '-y', '-i', clean, '-ac', '1', '-ar', '16000', '-f', 'f32le', f32])
    run(['node', os.path.join(HERE, 'transcribe.mjs'), f32, words], env={**os.environ, 'ZN_CACHE': CACHE})
if '--draft' in sys.argv:  # transcription draft for Ido to correct, no video yet
    print('\nDRAFT (Whisper, needs correction):\n' + json.load(open(words))['text'])
    sys.exit(0)
subs_file = os.path.join(work, 'subs.json')
tr = os.path.join(work, 'transcript.txt')
open(tr, 'w', encoding='utf-8').write(open(P(cfg['transcript_file']), encoding='utf-8').read())
run([sys.executable, os.path.join(HERE, 'align.py'), tr, words, subs_file])
subs = json.load(open(subs_file))['subs']
for s in cfg.get('subtitle_overrides', []):  # manual fixes: {"i":3,"s":..,"e":..,"t":..}
    subs[s['i']].update({k: v for k, v in s.items() if k != 'i'})

# 4) map ------------------------------------------------------------------------
pl = cfg['place']
mapimg = os.path.join(work, 'map.png')
margs = [sys.executable, os.path.join(HERE, 'make_map.py'), '--country', pl['country'],
         '--lat', str(pl['lat']), '--lon', str(pl['lon']), '--out', mapimg]
for r in pl.get('refs', []): margs += ['--ref', r]
if pl.get('map_span'): margs += ['--span', str(pl['map_span'])]
run(margs)
mapmeta = json.load(open(os.path.join(work, 'map.json')))

# 5) overlay timeline -------------------------------------------------------------
def find_time(anchor):
    for s in subs:
        if anchor in s['t']: return s['s']
    # anchor split across two subtitles
    for a, b in zip(subs, subs[1:]):
        if anchor in a['t'] + ' ' + b['t']: return a['s']
    raise SystemExit(f'anchor not found in transcript: {anchor!r}')

ev = [('logo', 0, D, True)]
sp = cfg.get('speaker')
if sp:
    for a, b in sp.get('show', [[0.4, 5.5]]): ev.append(('name', a, b, True))
mc = cfg.get('map_card', [6.0, 11.5])
if mc: ev.append(('map', mc[0], mc[1], True))
for f in cfg.get('facts', []):
    a = f['start'] if 'start' in f else find_time(f['anchor'])
    ev.append(('fact', a, min(a + f.get('dur', 4.5), D), f))
for s in subs: ev.append(('sub', s['s'], s['e'], s['t']))
# the map card and fact cards share a slot: facts win, map card is cut short
cuts = sorted({0, D} | {max(0, min(e[1], D)) for e in ev} | {max(0, min(e[2], D)) for e in ev})
states = []
for a, b in zip(cuts, cuts[1:]):
    if b - a < 0.02: continue
    m = (a + b) / 2; s = {}
    for e in ev:
        if e[1] <= m < e[2]: s[e[0]] = e[3]
    if 'fact' in s: s.pop('map', None)
    states.append({'a': a, 'b': b, 's': s})
json.dump(states, open(os.path.join(work, 'states.json'), 'w'), ensure_ascii=False)

# 6) render graphics ------------------------------------------------------------
page_cfg = {'place': pl, 'speaker': sp, 'map': mapmeta, 'mapimg': mapimg,
            'end': cfg.get('end', {'q': 'רוצים לטייל איתנו?', 'button': 'שלחו לנו הודעה ✦ זן נדיר'})}
html = open(os.path.join(SKILL, 'templates', 'page.html'), encoding='utf-8').read()
html = (html.replace('{{ASSETS}}', 'file://' + ASSETS).replace('{{W}}', str(W)).replace('{{H}}', str(H))
        .replace('{{LAYOUT}}', 'v' if vertical_canvas else '').replace('{{CFG}}', json.dumps(page_cfg, ensure_ascii=False)))
page = os.path.join(work, 'page.html'); open(page, 'w', encoding='utf-8').write(html)
gfx = os.path.join(work, 'gfx'); shutil.rmtree(gfx, ignore_errors=True)
run(['node', os.path.join(HERE, 'render.js'), page, os.path.join(work, 'states.json'), gfx, str(W), str(H)])

# 7) compose ---------------------------------------------------------------------
IN, END, XF = cfg.get('intro_sec', 4.0), cfg.get('end_sec', 3.5), 0.6
if vertical_canvas and sw > sh:   # landscape source on a 9:16 canvas: blurred fill + centered band
    vid = (f'[0:v]fps=30,split[a][b];[a]scale=-2:{H},crop={W}:{H},scale={W//4}:{H//4},boxblur=12:2,'
           f'scale={W}:{H},eq=brightness=-0.15:saturation=0.85[bg];'
           f'[b]scale={W}:-2:flags=lanczos,eq=contrast=1.04:saturation=1.1,unsharp=5:5:0.5[fg];'
           f'[bg][fg]overlay=0:(H-h)/2,setsar=1[v0];')
else:
    vid = (f'[0:v]fps=30,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
           f'eq=contrast=1.04:saturation=1.1,unsharp=5:5:0.5,setsar=1[v0];')
fc = (vid +
      f'[1:v]fps=30,format=rgba[ov];[v0][ov]overlay=0:0:eof_action=pass,format=yuv420p,trim=duration={D},setpts=PTS-STARTPTS,fps=30,settb=AVTB[main];'
      f'[2:v]scale={W}:{H},format=yuv420p,setsar=1,fps=30,settb=AVTB[intro];'
      f'[3:v]scale={W}:{H},format=yuv420p,setsar=1,fps=30,settb=AVTB[end];'
      f'[intro][main]xfade=transition=fade:duration={XF}:offset={IN - XF}[x1];'
      f'[x1][end]xfade=transition=fade:duration=0.5:offset={IN - XF + D - 0.5},format=yuv420p[vout];'
      f'[4:a]atrim=duration={D},afade=in:st=0:d=0.15,afade=out:st={D - 0.8}:d=0.8,adelay={int((IN - XF) * 1000)}:all=1,'
      f'apad=whole_dur={IN - XF + D - 0.5 + END}[aout]')
total = IN - XF + D - 0.5 + END
kbps = int(min(6000, (cfg.get('max_mb', 28) * 8192 / total) - 200))
run([FF, '-v', 'error', '-y', '-ss', str(t0), '-t', str(D), '-i', video,
     '-f', 'concat', '-safe', '0', '-i', os.path.join(gfx, 'overlay.txt'),
     '-loop', '1', '-framerate', '30', '-t', str(IN), '-i', os.path.join(gfx, 'intro.png'),
     '-loop', '1', '-framerate', '30', '-t', str(END), '-i', os.path.join(gfx, 'end.png'),
     '-i', clean, '-filter_complex', fc, '-map', '[vout]', '-map', '[aout]',
     '-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.3)}k', '-bufsize', f'{kbps * 2}k',
     '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out])

# 8) contact sheet for QA ---------------------------------------------------------
sheet = out.rsplit('.', 1)[0] + '_preview.jpg'
times = [1.5, IN + 2] + [IN - XF + (s['a'] + s['b']) / 2 for s in states if 'fact' in s['s'] or 'map' in s['s']][::3][:6]
sel = '+'.join(f'eq(n\\,{int(t * 30)})' for t in sorted(set(round(t, 1) for t in times))[:8])
cols = 4 if not vertical_canvas else 4
run([FF, '-v', 'error', '-y', '-i', out, '-vf', f"select='{sel}',scale={480 if not vertical_canvas else 270}:-1,tile={cols}x2",
     '-vsync', '0', '-frames:v', '1', sheet])
print(f'\nDONE {out}  ({os.path.getsize(out) / 1e6:.1f} MB, {total:.1f}s)\npreview: {sheet}')
