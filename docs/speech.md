# GLOW Speech Platform PRD — v3.0.0

> **Scope for v3.0.0:** Speech Studio supports typed synthesis, uploaded document-to-speech conversion, and adaptive runtime estimation based on real server telemetry.

## Tiered Architecture

| Tier | Engine | Install | Models | GPU required | Quality |
|------|--------|---------|--------|--------------|---------|
| **1 — Default** | Kokoro ONNX | `pip install kokoro-onnx` | ~85 MB (auto-detectable via HF Hub) | No | Good |
| **2 — Supplemental** | Piper TTS | `pip install piper-tts` | ~50–100 MB per voice (manual download) | No | Fair–Good |
| **3 — Optional/Cloud** | Azure AI Speech Neural | Azure subscription + SDK | None | No | Excellent |

**Tier 1 and 2 are shipping in v3.0.0.** Tier 3 (Azure) is deferred to a later release.

Both Tier 1 and Tier 2 are CPU-only, self-hosted, free to run, and never send document text outside the server. All voices are English-only in v3.0.0.

---

## Tier 1: Kokoro ONNX

### Voices (English)

| Voice ID | Label | Accent | Gender |
|----------|-------|--------|--------|
| `af_bella` | Bella | American | Female |
| `af_sarah` | Sarah | American | Female |
| `af_nicole` | Nicole | American | Female |
| `af_sky` | Sky | American | Female |
| `am_adam` | Adam | American | Male |
| `am_michael` | Michael | American | Male |
| `bf_emma` | Emma | British | Female |
| `bf_isabella` | Isabella | British | Female |
| `bm_george` | George | British | Male |
| `bm_lewis` | Lewis | British | Male |

### Installation

```bash
pip install kokoro-onnx
```

### Model files

Model files are NOT bundled with the pip package. They must be placed in `instance/speech_models/` before the engine can synthesize. GLOW's Speech settings page shows setup status and download instructions.

**Manual download:**

```bash
mkdir -p instance/speech_models
wget -O instance/speech_models/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget -O instance/speech_models/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

### Model directory

Configurable via `GLOW_SPEECH_MODEL_DIR` environment variable. Default: `{flask_instance_path}/speech_models/`.

---

## Tier 2: Piper TTS

### Voices (English, curated)

| Voice ID | Label | Accent | Gender | Sample Rate |
|----------|-------|--------|--------|-------------|
| `en_US-lessac-medium` | Lessac (US) | American | Male | 22050 Hz |
| `en_US-amy-medium` | Amy (US) | American | Female | 22050 Hz |
| `en_US-ryan-high` | Ryan (US, High Quality) | American | Male | 22050 Hz |
| `en_US-hfc_female-medium` | HFC Female (US) | American | Female | 22050 Hz |
| `en_GB-alan-medium` | Alan (GB) | British | Male | 22050 Hz |
| `en_GB-southern_english_female-low` | Southern English Female (GB) | British | Female | 16000 Hz |

### Installation

```bash
pip install piper-tts
```

### Model files

Each Piper voice requires two files: `{voice_id}.onnx` and `{voice_id}.onnx.json`. Place them in `instance/speech_models/piper/`. Download from Hugging Face:

```bash
# Example: Lessac medium
mkdir -p instance/speech_models/piper
wget -O instance/speech_models/piper/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget -O instance/speech_models/piper/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

GLOW also detects Hugging Face's nested `en/...` download layout if those files have already been placed under `instance/speech_models/piper/`.

---

## Audio Processing Pipeline

```
User text + voice + speed + pitch
        ↓
  Engine synthesize() → float32 numpy array + sample_rate
        ↓
  Pitch shift (stdlib wave resampling, ±20 semitones)
        ↓
  numpy → 16-bit PCM WAV (stdlib wave, no extra deps)
        ↓
  Preview: return audio/wav for inline <audio> player
  Download: encode to MP3 via pydub+ffmpeg if available, else WAV
```

### Speed
- Kokoro: native `speed` parameter (0.5–2.0×)
- Piper: `length_scale = 1 / speed` (inverse — longer scale = slower)

### Pitch
- Implemented via sample-rate manipulation (stdlib `wave`, no extra deps)
- Range: −20 to +20 semitones, step 1
- Note: this approach slightly affects tempo alongside pitch (acceptable for demo use)

### Audio output
- Preview: `audio/wav`, inline `<audio>` player
- Download: `audio/mpeg` (MP3 at 192 kbps via pydub) if ffmpeg is installed, otherwise `audio/wav`

---

## v3.0.0 Scope: Settings + Speech Studio

The `/speech/` route provides:

1. **Engine status** — which engines are installed and model files present
2. **Voice selector** — one combined voice list (single combo box) across ready engines
3. **Speed slider** — 0.5× to 2.0×, step 0.1, default 1.0
4. **Pitch slider** — −20 to +20 semitones, step 1, default 0
5. **Speech text area** — up to 500 characters, live character counter
6. **Preview button** — JS fetch → returns WAV → inline `<audio>` player
7. **Download button** — form POST → returns MP3 (or WAV fallback) as attachment
8. **Persistent preferences (opt-in)** — selected voice, text, speed, and pitch can be saved in GLOW local settings (`glow_user_settings`) and restored on return
9. **Preview progress messaging** — users get live status text while synthesis runs so long previews (15-20 seconds) remain clearly active
10. **Document prepare step** — extracts uploaded document text, stores session token, and shows estimated audio + processing durations
11. **Snippet preview** — previews the first two extracted sentences from the uploaded file
12. **Full document render** — queue-first synthesis for full extracted text with job progress and MP3/WAV download
13. **Smart timed announcements** — status announcements scale by expected runtime (short jobs: ~10-20 second updates, long jobs: ~45-150 second updates)
14. **Adaptive estimate telemetry** — real conversion samples (word count, source size bytes, speed/voice, and measured processing time) are stored server-side and blended into future estimates for this deployment
15. **Convert-tab handoff** — Convert now offers a "Speech audio" direction that opens Speech Studio with the uploaded file already loaded (no second upload)
16. **Queued document preparation option** — long-running preparation can return a job progress flow and continue back to Speech Studio when complete

Speech Studio now supports queue-first processing for heavy paths (document prepare + full-document downloads) through the shared `/job/<id>/` progress surface when async mode is enabled.

### Adaptive estimate telemetry

Speech Studio now records each completed document conversion into `instance/speech_metrics.db` with:

- Word count
- Character count
- Source document size in bytes
- Selected engine/voice/speed/pitch
- Real measured processing duration
- Generated audio duration

Future estimates blend baseline text-length heuristics with this historical telemetry so estimates improve over time on the actual server infrastructure in production.

### Deployment note: curated Piper voice seeding

Deploy and image build workflows now seed a curated English Piper set (US + GB) rather than only one default voice when network access is available:

- `en_US-lessac-medium`
- `en_US-amy-medium`
- `en_US-ryan-high`
- `en_US-hfc_female-medium`
- `en_GB-alan-medium`
- `en_GB-southern_english_female-low`

### Admin voice pack management

The admin dashboard includes a Speech Studio voice management page with one-click install/remove controls for curated Piper voices. This lets administrators add or remove voice packs without shell access.

---

## Deferred to future release

- Incremental/chunked streaming playback for long document synthesis
- Optional email notifications for background speech renders
- Azure AI Speech Tier 3 integration

---

## 1. Overview (original Kokoro PRD — retained for reference)

A self-hosted Text-to-Speech (TTS) platform built on Kokoro TTS, designed for Unix environments. The system enables:

- English-only voice synthesis
- User-controlled speech customization
- Real-time preview generation
- MP3 export and download
- Accurate generation time estimation
- CPU-first deployment (no GPU required)

---

## 2. Goals

### Primary Goals
- Reliable CPU-based TTS generation
- Predictable performance and timing
- Customizable speech output
- Scalable backend architecture

### Secondary Goals
- Preview-first UX
- Efficient caching and reuse
- Async processing for long jobs

---

## 3. Non-Goals

- Emotion-level synthesis (limited by model)
- Voice cloning or training
- Multilingual support
- Studio-grade prosody control

---

## 4. System Architecture

### High-Level Flow

```

User Input
↓
Text Analyzer (length + estimate)
↓
Preview Generator (short clip)
↓
TTS Engine (Kokoro)
↓
Audio Processor (WAV → MP3)
↓
Storage + Download API

```

---

## 5. Core Components

### API Layer
- FastAPI
- Handles:
  - text input
  - parameters
  - preview requests
  - job creation

### TTS Engine
- Kokoro ONNX model
- Loaded into memory at startup

### Audio Processing
- FFmpeg for conversion:
```

ffmpeg -i input.wav -codec:a libmp3lame -b:a 192k output.mp3

```

### Job Queue
- Redis-based queue
- Worker processes (2–4 per machine)

### Storage
```

/audio/{user_id}/{job_id}.mp3

```

---

## 6. CPU-Only Deployment Strategy

### Key Insight
Kokoro is CPU-friendly and does NOT require a GPU.

### Performance Characteristics

| Mode | Speed |
|------|------|
| CPU | ~0.8x – 1.5x realtime |
| GPU (optional) | ~3x – 10x realtime |

---

## 7. Performance Expectations (CPU)

| Input Size | Audio Length | Generation Time |
|-----------|-------------|----------------|
| 50 words | ~20 sec | 15–25 sec |
| 300 words | ~2 min | 1.5–3 min |
| 2000 words | ~12–15 min | 10–20 min |

---

## 8. System Constraints Without GPU

### Limitations
- Slower generation speed
- Limited concurrency (1–4 jobs)
- Long jobs must be asynchronous
- Not suitable for real-time full-length output

### Still Fully Supported
- Preview generation
- MP3 export
- Parameter customization
- Time estimation

---

## 9. Required Design Adjustments (CPU Optimization)

### 1. Async Job Processing (MANDATORY)

```

POST /generate → returns job_id
GET /status → progress
GET /download → file

```

---

### 2. Job Queue

- Redis queue
- Worker pool (2–4 workers)
- FIFO + priority support

---

### 3. Text Chunking (CRITICAL)

Split long inputs:

```

Max chunk size: ~500 words

```

Pipeline:
```

Split → Generate in parallel → Merge audio

```

---

### 4. Preview-First UX

- Generate first 3–8 seconds
- Response time: <1 second
- Prevents wasted compute

---

### 5. Caching

Hash key:
```

hash(text + voice + parameters)

```

Reuse identical outputs.

---

## 10. User Customization

### Voice Selection
- Predefined voices:
  - af_bella
  - am_adam
  - etc.

---

### Adjustable Parameters

| Parameter | Method |
|----------|--------|
| Speed | Native |
| Pitch | FFmpeg post-processing |
| Tone | Text formatting |
| Energy | Audio filters |

---

### Processing Pipeline

```

Kokoro WAV
↓
Pitch shift (ffmpeg)
↓
Tempo adjust
↓
MP3 encode

```

---

## 11. Preview Feature

### Behavior
- Uses truncated input (~200 chars)
- Returns short audio clip

### Target Latency
- < 1 second

---

## 12. Time Estimation Engine

### Formula

```

words = len(text.split())
speech_duration = words / 2.7
generation_time = speech_duration / speed_factor

````

---

### Example

| Words | Audio | CPU Time |
|------|------|---------|
| 270 | ~100 sec | ~90–110 sec |

---

### API Response

```json
{
  "estimated_audio_length_sec": 100,
  "estimated_generation_time_sec": 95,
  "processing_mode": "cpu"
}
````

---

## 13. API Design

### Preview

```
POST /preview
```

### Estimate

```
POST /estimate
```

### Generate

```
POST /generate
```

### Status

```
GET /status/{job_id}
```

### Download

```
GET /download/{job_id}
```

---

## 14. File Output

### Formats

| Format | Purpose      |
| ------ | ------------ |
| WAV    | intermediate |
| MP3    | final        |

---

### File Sizes

| Length | Size    |
| ------ | ------- |
| 1 min  | ~1.5 MB |
| 10 min | ~15 MB  |

---

## 15. Hardware Requirements

### Minimum

* 2 vCPU
* 4 GB RAM

### Recommended

* 4–8 vCPU
* 8–16 GB RAM

---

## 16. Scaling Strategy

### Phase 1 (CPU Only)

* Single instance
* 2–4 workers
* Redis queue

### Phase 2

* Horizontal scaling
* Load balancer
* Shared storage

### Phase 3 (Optional GPU)

* Add GPU worker node
* Route large jobs selectively

---

## 17. Smart Features

### Chunk Parallelization

* Major CPU performance boost

### Job Prioritization

* Short jobs first

### Caching Layer

* Avoid recomputation

---

## 18. Limitations

* No fine-grained emotional control
* Limited voice library
* Pitch/tone are approximations
* Long jobs require async handling

---

## 19. Recommended Stack

* FastAPI
* ONNX Runtime
* Redis
* FFmpeg
* Gunicorn

---

## 20. Final Positioning

This system should be treated as:

> A CPU-optimized, async TTS generation platform with real-time preview capabilities

NOT:

> A fully real-time, instant full-length speech system

---

## 21. Future Enhancements

* GPU acceleration node
* Streaming audio playback
* Voice blending
* UI dashboard
* Batch processing tools

---
