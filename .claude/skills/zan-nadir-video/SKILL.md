---
name: zan-nadir-video
description: Turn a raw Zan Nadir (זן נדיר) travel video (a guide talking on location, a trip clip, a TV segment) into a branded, captioned social video. Output is an opening slide with the Zan Nadir logo, the place name and a locator map, then the video with the speaker's voice cleaned up, full Hebrew subtitles timed to the speech, a name tag, a map card, short info cards about the place, and a branded end slide with a call to action. Use whenever Ido sends a video for Zan Nadir, or says "תפיק סרטון", "סרטון ממותג", "תוסיף כתוביות", "ריל לזן נדיר", "תערוך את הסרטון של יורם", "Zan Nadir video", even without the word "skill". Not for documents or brochures (use zan-nadir-docs).
---

# Zan Nadir branded video

Brand: copper `#A65A2A`, cream `#F8F1DE`, ink `#2A1810`, sand `#D9B27C`; Frank Ruhl Libre 900 for titles, Heebo for everything else. The logo (`assets/logo.png`) goes only on light surfaces: a cream card on the video, full size on the intro and end slides.

## Step 1: gather what's missing and ask BEFORE producing

The full transcript matters most. Never burn in subtitles from machine transcription alone. Hebrew Whisper makes a lot of mistakes, and on-screen spelling mistakes hurt the brand. Get these from Ido, in one AskUserQuestion round (or a short message if they need free text):

| What | Required? | Notes |
|---|---|---|
| Full transcript | **Yes** | One line per sentence, spelled exactly as it should appear on screen. If it's missing, you can run step 2 first and give Ido the Whisper draft to correct, but don't produce the video until an approved text comes back. `\|` inside a line forces a subtitle break. |
| Place name + region/country | Yes | For example "מטאורה" / "תסליה, צפון יוון". Also look up coordinates (lat/lon) and the country's ISO3 code yourself, and state them in your reply so Ido can catch a mistake. |
| Speaker name + role | Yes, if someone speaks | Default: "יורם פורת · מדריך טיולים בזן נדיר" for Yoram. Don't guess a name from the face. |
| Format | Default: keep the source format | `"layout": "vertical"` produces 9:16 for Reels/TikTok. Offer both. |
| Trim | Optional | `"trim": [start, end]` in seconds, if there are dead seconds at the start or end. |
| Call to action | Default in the example | Trip dates or season, if Ido wants them mentioned. |

Info cards: suggest 3-5 short facts about the place, tied to things the speaker says (the `anchor` = a word from the transcript, so the card appears when it's said). **Only facts you're sure of.** No heights, years or numbers you can't verify. When in doubt, drop the number or ask. Show Ido the list of facts before production. Numbers the speaker himself says are fine as-is.

## Step 2: setup (once per environment)

```bash
bash <skill>/scripts/setup.sh        # ffmpeg, Pillow, transformers.js, whisper-small from npm, Playwright
```
Everything is cached in `~/.cache/zan-nadir-video` (override with `ZN_CACHE`). Whisper comes from npm because huggingface.co is often blocked in cloud environments. If npm is also blocked, word-level timing isn't available. Say so and ask Ido for approximate timings, or produce subtitles by sentence only.

To show Ido a transcription draft before he sends a transcript: run build.py with an empty transcript; it creates `words.json`, and `words.json → text` is the draft.

## Step 3: project.json and build

Copy `templates/project.example.json` next to the video, fill it in, and save the transcript as `transcript.txt`. Then:

```bash
python3 <skill>/scripts/build.py project.json
```

What it does, in order (results are cached under `<out>.work/`; to redo a step, delete its file):
1. **Audio**: mono, 90Hz high-pass (wind), RNNoise (`assets/sh.rnnn`), light FFT denoise, EQ for voice clarity (-3dB at 220Hz, +4dB at 3kHz, +2dB at 6.5kHz), compressor, loudness -14 LUFS (the social media standard). If the voice sounds "metallic", set `"denoise": 0.7`.
2. **Word timing**: Whisper small, word timestamps (`words.json`).
3. **Alignment**: `align.py` aligns Ido's transcript to the timing letter by letter. The on-screen text is always the transcript. It prints the subtitles and a coverage %. Below 45% means the transcript probably doesn't match the video: stop and check. Manual timing fixes: `"subtitle_overrides": [{"i": 3, "s": 10.2}]`.
4. **Map**: `make_map.py` draws the country highlighted, its neighbors, the sea, a pin, and 1-2 reference cities (`refs`). Labels are HTML (PIL doesn't handle RTL). For a small island or a zoom-in, use `"map_span": 3` (degrees).
5. **Graphics**: `templates/page.html` renders with Playwright to one transparent PNG per state (subtitle / card / tag), plus the intro and end slides.
6. **Compose**: intro (4s) → fade → video with the overlays → fade → end slide (3.5s). The bitrate is set automatically to stay under `max_mb` (default 28MB, because the file-send limit is 30MB).
7. **Preview**: `<out>_preview.jpg`, a contact sheet.

## Step 4: QA before sending

Look at the preview (Read on the jpg) and check:
- Subtitles aren't cut off, don't cover the face or the logo, and punctuation sits on the correct (left) side.
- Numbers inside Hebrew text: bidi can flip them (for example "ה־14" or "ב־1988"). Prefer words ("הארבע עשרה") or "בשנת 1988".
- Cards don't cover each other; the map card gives way to fact cards automatically.
- The pin sits in the right place on the map.
Anything wrong: fix project.json and run again (it takes seconds, apart from the final render).

## Delivery

- Send the file with SendUserFile (`display: render`). If it's over 30MB, lower `max_mb`.
- Say what you did in a few lines, and list separately: which facts came from your own knowledge (so Ido verifies them), and any wording in the transcript you changed.
- Recommend a 9:16 version if only one format was produced.
- Sound: you can't listen. Say the audio was processed and should be checked by ear.

## Files

- `scripts/setup.sh`: installs the toolchain
- `scripts/build.py`: the whole pipeline, from project.json
- `scripts/transcribe.mjs`: Whisper word timestamps
- `scripts/align.py`: transcript ↔ timing
- `scripts/make_map.py`: locator map (Natural Earth 1:50m, `assets/countries_50m.json`)
- `scripts/render.js`: graphics PNGs with Playwright
- `templates/page.html`: design of all graphic elements (landscape and `.v` for vertical)
- `templates/project.example.json`: full example (Meteora with Yoram)
- `templates/transcript.example.txt`: the matching transcript example
