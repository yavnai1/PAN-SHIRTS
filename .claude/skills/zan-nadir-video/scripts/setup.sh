#!/usr/bin/env bash
# One-time setup of the toolchain. Safe to re-run; everything is cached under $ZN_CACHE.
set -euo pipefail
ZN_CACHE="${ZN_CACHE:-$HOME/.cache/zan-nadir-video}"
mkdir -p "$ZN_CACHE"
cd "$ZN_CACHE"

# ffmpeg (static build shipped inside a PyPI wheel, works when apt/ffmpeg is missing) + python deps
python3 -c "import imageio_ffmpeg, PIL, numpy" 2>/dev/null || pip install -q imageio-ffmpeg pillow numpy
FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
if command -v ffmpeg >/dev/null && ffmpeg -hide_banner -filters 2>/dev/null | grep -q arnndn; then FF=$(command -v ffmpeg); fi
ln -sf "$FF" "$ZN_CACHE/ffmpeg"

# Word-level speech timing: transformers.js + whisper-small ONNX weights.
# The weights come from the npm registry (package sts-whisper-small), because
# huggingface.co is often blocked in sandboxed environments.
if [ ! -d "$ZN_CACHE/node_modules/@huggingface/transformers" ]; then
  [ -f package.json ] || npm init -y >/dev/null
  npm i -s @huggingface/transformers@3 >/dev/null 2>&1
fi
if [ ! -f "$ZN_CACHE/whisper/models/Xenova/whisper-small/onnx/encoder_model_quantized.onnx" ]; then
  mkdir -p whisper && cd whisper
  curl -sL -o m.tgz https://registry.npmjs.org/sts-whisper-small/-/sts-whisper-small-1.0.0.tgz
  tar xzf m.tgz --strip-components=1 && rm m.tgz
  cd ..
fi

# Playwright (renders the Hebrew graphics). Prefer a global install.
node -e "require('playwright')" 2>/dev/null || [ -d /opt/node22/lib/node_modules/playwright ] || npm i -s playwright >/dev/null 2>&1

echo "ready: $ZN_CACHE"
