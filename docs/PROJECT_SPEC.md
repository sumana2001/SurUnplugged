# SurUnplugged - Technical Specification

> **An acoustic guitar backing track generator with pitch control for amateur singers**

## 🎯 Problem Statement

Karaoke tracks are often produced in keys that don't match everyone's vocal range. Professional singers can adapt, but amateur singers struggle, resulting in uncomfortable singing experiences. 

**SurUnplugged** creates simplified acoustic guitar backing tracks (like MTV Unplugged sessions) that:
- Sound pleasant even with pitch adjustments
- Are forgiving for imperfect vocals
- Help users learn songs at their comfortable pitch

---

## 🎵 Core User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. UPLOAD      2. WAIT           3. ADJUST       4. SING       │
│  ────────       ──────────        ──────────      ─────────     │
│  Upload MP3  →  Processing     →  Set pitch   →  Play along    │
│               (1-5 minutes)       (-6 to +6)    with backing    │
│                                   semitones                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                  │
│                    (React + Vite + Tailwind)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ File Upload │  │ Audio Player│  │ Chord Timeline + Controls   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP/REST
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND (Python)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  API Layer: /upload, /status, /result, /transpose            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Job Queue (Redis Queue or Celery) - Async Processing        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE                              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   DEMUCS     │ →  │   CHORDINO   │ →  │   MIDI GENERATOR     │  │
│  │ (Stem Split) │    │ (Chord Det.) │    │ (pretty_midi +       │  │
│  └──────────────┘    └──────────────┘    │  FluidSynth)         │  │
│                                          └──────────────────────┘  │
│                                                     │               │
│                                                     ▼               │
│                                          ┌──────────────────────┐  │
│                                          │  Guitar Backing WAV  │  │
│                                          └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Tech Stack (Final Decision)

| Component | Technology | Reason |
|-----------|------------|--------|
| **Backend** | Python + Flask | Familiar, integrates well with ML libraries |
| **Task Queue** | Redis Queue (RQ) | Lightweight, simpler than Celery |
| **Stem Separation** | Demucs (htdemucs) | Best open-source, Facebook/Meta quality |
| **Chord Detection** | Chordino (via vamp) | Standard for chord recognition |
| **MIDI Generation** | pretty_midi | Simple Python library |
| **MIDI → Audio** | FluidSynth | Reliable, free soundfonts available |
| **Frontend** | React + Vite + Tailwind CSS | Modern DX, fast builds, easy Vercel deploy |
| **Audio Playback** | Web Audio API | Precise control, mixing capabilities |
| **Deployment** | Railway / Render / Hugging Face Spaces | Free tiers, GPU options later |

---

## ⚡ Processing Modes (User Choice)

Users can choose their preferred processing mode based on speed vs quality tradeoff:

| Mode | Description | CPU Time | Quality | Best For |
|------|-------------|----------|---------|----------|
| **Fast** | Chord detection on full mix | ~30 sec | ⭐⭐ (70-75%) | Quick preview, simple songs |
| **Balanced** | Vocal separation (--two-stems) | ~2-3 min | ⭐⭐⭐ (80-85%) | Most songs (recommended) |
| **Quality** | Full stem separation | ~4-5 min | ⭐⭐⭐⭐ (85-90%) | Complex arrangements |

### Mode Details

```
┌─────────────────────────────────────────────────────────────────────┐
│  FAST MODE                                                          │
│  ──────────                                                         │
│  input.wav ─────────────────────────→ Chordino ──→ chords.json     │
│                                                                     │
│  • Skips Demucs entirely                                            │
│  • Chord detection on full mix (vocals may confuse detection)       │
│  • Best for acoustic/simple songs                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  BALANCED MODE (Recommended)                                        │
│  ───────────────────────────                                        │
│  input.wav ──→ Demucs (--two-stems) ──→ no_vocals.wav ──→ Chordino │
│                                                                     │
│  • Fast vocal removal only                                          │
│  • Chord detection on instrumental                                  │
│  • Good balance of speed and accuracy                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  QUALITY MODE                                                       │
│  ────────────                                                       │
│  input.wav ──→ Demucs (full) ──→ bass+drums+other ──→ Chordino     │
│                                                                     │
│  • Full 4-stem separation                                           │
│  • Can use "other" stem (cleaner harmony)                          │
│  • Best for complex songs with heavy drums                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Processing Pipeline Details

### Step 1: Audio Input
```python
# Input: MP3 file
# Output: WAV file (44.1kHz, stereo)

from pydub import AudioSegment
audio = AudioSegment.from_mp3("input.mp3")
audio.export("input.wav", format="wav")
```

### Step 2: Stem Separation (Demucs) - Balanced/Quality modes only
```bash
# Uses htdemucs model (smallest, fastest)
# CPU processing: ~2-5 minutes for a 3-minute song
demucs --two-stems=vocals input.wav

# Output:
# separated/htdemucs/input/vocals.wav
# separated/htdemucs/input/no_vocals.wav  (accompaniment)
```

### Step 3: Chord Detection (Chordino)
```python
# Using vamp plugin
import vamp
import librosa

y, sr = librosa.load("no_vocals.wav", sr=44100)
chords = vamp.collect(y, sr, "nnls-chroma:chordino")

# Output format:
# [{"time": 0.0, "chord": "C"}, {"time": 2.5, "chord": "Am"}, ...]
```

### Step 4: MIDI Generation
```python
import pretty_midi

def chord_to_midi_notes(chord_name, octave=3):
    """Convert chord name to MIDI note numbers"""
    # C major at octave 3: [48, 52, 55] (C3, E3, G3)
    # Implementation maps chord roots and types to notes
    pass

pm = pretty_midi.PrettyMIDI()
guitar = pretty_midi.Instrument(program=25)  # Acoustic Guitar

for chord_info in chord_progression:
    notes = chord_to_midi_notes(chord_info["chord"])
    for note in notes:
        guitar.notes.append(pretty_midi.Note(
            velocity=80,
            pitch=note,
            start=chord_info["time"],
            end=chord_info["time"] + duration
        ))

pm.instruments.append(guitar)
pm.write("backing.mid")
```

### Step 5: MIDI → Audio (FluidSynth)
```bash
fluidsynth -ni guitar.sf2 backing.mid -F backing.wav -r 44100
```

---

## 🎹 Pitch Transposition Logic

```python
NOTE_MAP = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

REVERSE_MAP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def transpose_chord(chord: str, semitones: int) -> str:
    """
    Transpose a chord by given semitones.
    Example: transpose_chord("Am7", 2) → "Bm7"
    """
    # Extract root note (handles sharps/flats)
    if len(chord) > 1 and chord[1] in "#b":
        root = chord[:2]
        suffix = chord[2:]
    else:
        root = chord[0]
        suffix = chord[1:]
    
    root_num = NOTE_MAP.get(root, 0)
    new_num = (root_num + semitones) % 12
    return REVERSE_MAP[new_num] + suffix
```

---

## 🎸 Guitar Styles (MVP: Soft Strum Only)

### Style 1: Soft Strum (Default)
```python
def soft_strum_pattern(chord_notes, start_time, duration):
    """
    Gentle downstroke strum
    Pattern: Play all notes with slight timing offset
    """
    notes = []
    for i, pitch in enumerate(chord_notes):
        notes.append({
            "pitch": pitch,
            "start": start_time + (i * 0.02),  # 20ms between strings
            "duration": duration - (i * 0.02),
            "velocity": 70 - (i * 5)  # Gradual decrease
        })
    return notes
```

### Future Styles (Post-MVP)
- **Fingerpicking**: Arpeggio patterns (bass → treble)
- **Ballad**: Slow, sustained chords with reverb
- **Pop Acoustic**: Rhythmic strumming pattern

---

## 🖥️ API Specification

### `POST /upload`
Upload an MP3 file for processing.

```json
// Request: multipart/form-data
// field: "file" (MP3)
// field: "mode" (optional) - "fast" | "balanced" | "quality" (default: "balanced")

// Response:
{
    "job_id": "abc123",
    "status": "queued",
    "mode": "balanced",
    "message": "Processing started. Check /status/abc123"
}
```

### `GET /status/{job_id}`
Check processing status.

```json
// Response:
{
    "job_id": "abc123",
    "status": "processing",  // queued | processing | completed | failed
    "progress": 45,          // percentage
    "current_step": "chord_detection",  // stem_separation | chord_detection | midi_gen | rendering
    "mode": "balanced",
    "estimated_time": 120    // seconds remaining
}
```

### `GET /result/{job_id}`
Get processed results.

```json
// Response:
{
    "job_id": "abc123",
    "chords": [
        {"time": 0.0, "duration": 2.5, "chord": "C"},
        {"time": 2.5, "duration": 2.0, "chord": "Am"}
    ],
    "backing_url": "/audio/abc123/backing.wav",
    "original_url": "/audio/abc123/original.wav",
    "duration": 180.5
}
```

### `POST /transpose`
Regenerate backing track with pitch shift.

```json
// Request:
{
    "job_id": "abc123",
    "semitones": -2
}

// Response:
{
    "job_id": "abc123_t-2",
    "backing_url": "/audio/abc123/backing_t-2.wav",
    "chords": [
        {"time": 0.0, "duration": 2.5, "chord": "Bb"},
        {"time": 2.5, "duration": 2.0, "chord": "Gm"}
    ]
}
```

---

## 🎨 Frontend Features (MVP)

### Core UI Elements
1. **Upload Zone**: Drag-and-drop or file picker
2. **Processing Mode Selector**: Fast / Balanced / Quality toggle
3. **Progress Indicator**: Status + progress bar during processing
4. **Audio Player**: 
   - Play/Pause button
   - Seek bar with time display
   - Volume control
5. **Pitch Control**: Slider from -6 to +6 semitones
6. **Current Chord Display**: Large, visible chord name
7. **Simple Timeline**: Visual bar showing chord changes

### Wireframe
```
┌─────────────────────────────────────────────────────────────┐
│  🎸 SurUnplugged                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     Drop your MP3 here or click to upload           │   │
│  │                    📁                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Processing Mode:                                           │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐               │
│  │  ⚡ Fast  │  │ ⭐ Balanced │  │ 💎 Quality│               │
│  │  ~30 sec │  │  ~2-3 min  │  │  ~4-5 min │               │
│  └──────────┘  └────────────┘  └───────────┘               │
│                    ▲ selected                               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Processing: ████████████░░░░░░░░ 60%               │   │
│  │  Current step: Detecting chords... (Balanced mode)   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │           ╔══════════════════════╗                  │   │
│  │           ║         Am           ║  ← Current       │   │
│  │           ╚══════════════════════╝    Chord         │   │
│  │                                                      │   │
│  │  ▶️ ━━━━━━━━━━●━━━━━━━━━━━━━━━  1:23 / 3:45         │   │
│  │                                                      │   │
│  │  🔊 ━━━━━━━●━━━━━━━                                  │   │
│  │                                                      │   │
│  │  Pitch:  -6 ━━━━━━━●━━━━━━━ +6    [Current: 0]     │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │ C    │  Am   │  F    │  G    │  C    │ Am  │    │   │
│  │  │──────│───────│───────│───────│───────│─────│    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                    ^ playhead                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Final Project Structure

```
SurUnplugged/
├── backend/
│   ├── app.py                 # Flask app entry point
│   ├── config.py              # Configuration settings
│   ├── requirements.txt       # Python dependencies
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # API endpoints
│   │   └── validators.py      # Input validation
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── stem_separator.py  # Demucs wrapper
│   │   ├── chord_detector.py  # Chordino/vamp wrapper
│   │   ├── midi_generator.py  # Chord → MIDI
│   │   ├── audio_renderer.py  # MIDI → WAV (FluidSynth)
│   │   └── transpose.py       # Pitch shifting logic
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── process_song.py    # Background job definition
│   │
│   └── utils/
│       ├── __init__.py
│       └── audio_utils.py     # Helper functions
│
├── frontend/                  # React + Vite
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── public/
│   │   └── favicon.ico
│   └── src/
│       ├── main.jsx           # Entry point
│       ├── App.jsx            # Main app component
│       ├── index.css          # Tailwind imports
│       ├── api/
│       │   └── client.js      # API functions
│       ├── components/
│       │   ├── FileUpload.jsx
│       │   ├── ModeSelector.jsx   # Fast/Balanced/Quality toggle
│       │   ├── AudioPlayer.jsx
│       │   ├── ChordDisplay.jsx
│       │   ├── PitchSlider.jsx
│       │   ├── Timeline.jsx
│       │   └── ProgressBar.jsx
│       ├── hooks/
│       │   ├── useAudioPlayer.js   # Web Audio API hook
│       │   └── useJobStatus.js     # Polling hook
│       └── utils/
│           └── chords.js      # Chord utilities
│
├── assets/
│   └── soundfonts/
│       └── acoustic_guitar.sf2
│
├── storage/                   # Created at runtime
│   └── jobs/
│       └── {job_id}/
│           ├── original.wav
│           ├── vocals.wav
│           ├── no_vocals.wav
│           ├── chords.json
│           ├── backing.mid
│           ├── backing.wav
│           └── backing_t{n}.wav  # Transposed versions
│
├── docker-compose.yml         # Local development
├── Dockerfile                 # Production build
├── README.md
├── PROJECT_SPEC.md           # This file
├── FEASIBILITY.md
├── DEVELOPMENT_PLAN.md
└── PROJECT_CONTEXT.md        # Living development notes
```

---

## 🔧 Dependencies

### Python (backend/requirements.txt)
```
flask==3.0.0
flask-cors==4.0.0
redis==5.0.0
rq==1.15.1
demucs==4.0.1
torch>=2.0.0
librosa==0.10.1
pydub==0.25.1
pretty-midi==0.2.10
vamp==1.1.0
numpy==1.26.0
```

### System Dependencies
```bash
# Ubuntu/Debian
apt-get install fluidsynth ffmpeg libsndfile1

# macOS
brew install fluidsynth ffmpeg
```

### Soundfont
- **Recommended**: GeneralUser GS or FluidR3_GM.sf2
- **Guitar-specific**: Acoustic_Grand_Piano.sf2 (subset)
- Source: https://musical-artifacts.com/artifacts?formats=sf2

---

## 🚀 Deployment Considerations

### Local Development
- Docker Compose with Flask + Redis
- Volumes for storage persistence
- Hot reload enabled

### Production (Free Tier Options)

| Platform | Pros | Cons |
|----------|------|------|
| **Railway** | Easy Docker deploy, $5 free credit/month | Limited CPU time |
| **Render** | Free tier, background workers | Cold starts |
| **Hugging Face Spaces** | Free GPU available, great for ML | Learning curve |
| **Fly.io** | Generous free tier, persistent volumes | Configuration complexity |

**Recommendation**: Start with **Hugging Face Spaces** (Gradio or Docker) for the ML backend, static hosting (Vercel/Netlify) for frontend.

---

## ⚠️ Known Limitations

1. **Processing Time**: CPU-only Demucs takes 2-5 minutes per song
2. **Chord Accuracy**: ~80-85% accuracy on pop/rock songs
3. **Complex Chords**: May simplify jazz chords (Cmaj9 → Cmaj7)
4. **Source Quality**: Low bitrate MP3s reduce accuracy
5. **Storage**: Each processed song uses ~100-200MB

---

## 🎯 Success Metrics

For personal use, success means:
- [ ] Can process any MP3 successfully (>90% of uploads)
- [ ] Chord detection sounds "right" when playing along
- [ ] Pitch shifting produces pleasant audio (no artifacts)
- [ ] Full processing completes in < 5 minutes
- [ ] UI is intuitive enough for friends to use without instructions

---

*Last Updated: April 2026*
