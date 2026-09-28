// Usage: node transcribe.mjs <audio.f32 (16kHz mono float32)> <out.json>
// Emits Whisper word timestamps: [{text, start, end}, ...]. Used for timing, the
// user's own transcript is always the text that goes on screen.
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const cache = process.env.ZN_CACHE || path.join(process.env.HOME, '.cache/zan-nadir-video');
const require = createRequire(path.join(cache, 'package.json'));
const mod = await import(require.resolve('@huggingface/transformers'));
const { pipeline, env } = mod.pipeline ? mod : mod.default;
env.localModelPath = path.join(cache, 'whisper/models/');
env.allowRemoteModels = false;
const [, , inFile, outFile] = process.argv;
const asr = await pipeline('automatic-speech-recognition', 'Xenova/whisper-small', { dtype: 'q8' });
const buf = fs.readFileSync(inFile);
const audio = new Float32Array(buf.buffer, buf.byteOffset, buf.length / 4);
const r = await asr(audio, {
  language: process.env.ZN_LANG || 'hebrew', task: 'transcribe',
  return_timestamps: 'word', chunk_length_s: 30, stride_length_s: 5,
});
const words = r.chunks.map(c => ({ text: c.text.trim(), start: c.timestamp[0], end: c.timestamp[1] ?? c.timestamp[0] + 0.3 }));
fs.writeFileSync(outFile, JSON.stringify({ text: r.text, words }, null, 1));
console.log(r.text);
