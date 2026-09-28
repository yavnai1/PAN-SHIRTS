#!/usr/bin/env python3
"""Time the user's transcript against Whisper word timestamps.

align.py transcript.txt words.json subs.json
The on-screen text is ALWAYS the user's transcript; Whisper only supplies timing.
Character-level alignment (difflib) maps each transcript character to a time, then the
transcript is cut into subtitle chunks of ~24-40 characters, preferring breaks at punctuation.
"""
import json, re, sys, difflib

tr_file, words_file, out_file = sys.argv[1:4]
MAXC, MINC = 40, 14

def norm(ch):
    # compare letters only; unify final letters and drop niqqud/punctuation
    ch = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}.get(ch, ch)
    return ch if re.match(r'[\w]', ch) else ''

words = json.load(open(words_file))['words']
# whisper side: every letter gets an interpolated time
w_chars, w_times = [], []
for w in words:
    letters = [norm(c) for c in w['text']]
    letters = [c for c in letters if c]
    n = max(len(letters), 1)
    for i, c in enumerate(letters):
        w_chars.append(c); w_times.append(w['start'] + (w['end'] - w['start']) * (i + 0.5) / n)

text = open(tr_file, encoding='utf-8').read().strip()
sentences = [re.sub(r'\s*\|\s*', ' | ', s.strip()) for s in re.split(r'\n+', text) if s.strip()]

# transcript side: letters with back-pointer to position
t_chars, t_pos = [], []
full = '\n'.join(s.replace(' | ', ' ') for s in sentences)
for i, c in enumerate(full):
    n = norm(c)
    if n: t_chars.append(n); t_pos.append(i)

sm = difflib.SequenceMatcher(None, t_chars, w_chars, autojunk=False)
t_time = [None] * len(t_chars)
for a, b, size in sm.get_matching_blocks():
    for k in range(size):
        t_time[a + k] = w_times[b + k]
# interpolate gaps
known = [i for i, t in enumerate(t_time) if t is not None]
if not known:
    raise SystemExit('alignment failed: transcript does not match the audio at all')
for i in range(len(t_time)):
    if t_time[i] is None:
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        if prev is None: t_time[i] = t_time[nxt]
        elif nxt is None: t_time[i] = t_time[prev]
        else: t_time[i] = t_time[prev] + (t_time[nxt] - t_time[prev]) * (i - prev) / (nxt - prev)
pos2time = {p: t for p, t in zip(t_pos, t_time)}
coverage = len(known) / len(t_chars)

def time_at(pos, forward=True):
    rng = range(pos, len(full)) if forward else range(pos, -1, -1)
    for p in rng:
        if p in pos2time: return pos2time[p]
    return None

# chunking
chunks = []
offset = 0
for s in sentences:
    words_ = s.split(' '); cur = []
    for wd in words_:
        if wd == '|':  # forced break
            if cur: chunks.append(' '.join(cur)); cur = []
            continue
        cur.append(wd); L = len(' '.join(cur))
        if L >= MAXC - 6 or (wd[-1] in ',;:–-' and L >= MINC + 8):
            chunks.append(' '.join(cur)); cur = []
    if cur:
        tail = ' '.join(cur)
        if len(tail) < MINC and chunks and len(chunks[-1]) + len(tail) <= MAXC + 8 and chunks[-1] in s.replace(' | ', ' ') and '|' not in s:
            chunks[-1] = chunks[-1] + ' ' + tail
        else:
            chunks.append(tail)
    # locate chunk spans
subs = []; offset = 0
for c in chunks:
    p = full.index(c, offset); offset = p + len(c)
    t0 = time_at(p, True); t1 = time_at(p + len(c) - 1, False)
    subs.append({'s': round(t0 - 0.12, 2), 'e': round(t1 + 0.25, 2), 't': c})
# no overlaps, no flicker: close small gaps
for i in range(len(subs) - 1):
    if subs[i]['e'] > subs[i + 1]['s']: subs[i]['e'] = subs[i + 1]['s'] - 0.02
    elif subs[i + 1]['s'] - subs[i]['e'] < 0.5: subs[i]['e'] = subs[i + 1]['s'] - 0.02
subs[0]['s'] = max(0, subs[0]['s'])
json.dump({'coverage': round(coverage, 3), 'subs': subs}, open(out_file, 'w'), ensure_ascii=False, indent=1)
for s in subs: print(f"{s['s']:6.2f}-{s['e']:6.2f}  {s['t']}")
print(f'alignment coverage: {coverage:.0%}' + ('  (LOW: check that the transcript matches this video)' if coverage < 0.45 else ''))
