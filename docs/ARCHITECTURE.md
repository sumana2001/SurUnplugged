# SurUnplugged - System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  CLIENT                                      │
│                          (React + Vite + Tailwind)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Browser                                                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐  │    │
│  │  │ Upload   │  │ Player   │  │ Controls │  │ Chord Timeline      │  │    │
│  │  │ Zone     │  │ (WebAudio│  │ (Pitch,  │  │ (Canvas/SVG)        │  │    │
│  │  │          │  │  API)    │  │  Volume) │  │                     │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                         HTTP REST (JSON + Audio files)                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FLASK BACKEND                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  API Layer                                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ POST /upload │  │GET /status/* │  │GET /result/* │  │POST /trans │  │  │
│  │  │              │  │              │  │              │  │    pose    │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │  │
│  └─────────┼─────────────────┼─────────────────┼────────────────┼─────────┘  │
│            │                 │                 │                │            │
│  ┌─────────▼─────────────────▼─────────────────▼────────────────▼─────────┐  │
│  │  Job Manager                                                            │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │  │
│  │  │ Queue Job   │ ←→ │ Check Status│ ←→ │ Get Results │                 │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           REDIS QUEUE (RQ)                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Job: process_song(job_id)                                              │  │
│  │                                                                         │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │  │
│  │  │ Queued   │ →  │ Running  │ →  │ Complete │ or │ Failed           │  │  │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PROCESSING PIPELINE                                    │
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │  1. DEMUCS   │ →  │ 2. CHORDINO  │ →  │ 3. MIDI GEN  │ →  │4. RENDER   │  │
│  │              │    │              │    │              │    │            │  │
│  │ Input:       │    │ Input:       │    │ Input:       │    │ Input:     │  │
│  │  original.wav│    │ no_vocals.wav│    │  chords.json │    │ backing.mid│  │
│  │              │    │              │    │              │    │            │  │
│  │ Output:      │    │ Output:      │    │ Output:      │    │ Output:    │  │
│  │  vocals.wav  │    │  chords.json │    │  backing.mid │    │backing.wav │  │
│  │  no_vocals   │    │              │    │              │    │            │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────────────┘  │
│         │                   │                   │                  │          │
│         ▼                   ▼                   ▼                  ▼          │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         FILE STORAGE                                    │  │
│  │  storage/jobs/{job_id}/                                                 │  │
│  │  ├── original.wav                                                       │  │
│  │  ├── vocals.wav                                                         │  │
│  │  ├── no_vocals.wav                                                      │  │
│  │  ├── chords.json                                                        │  │
│  │  ├── backing.mid                                                        │  │
│  │  ├── backing.wav         ← Main output                                  │  │
│  │  └── backing_t{n}.wav    ← Transposed versions                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request Flow Diagrams

### Upload Flow

```
┌────────┐          ┌─────────┐          ┌───────────┐          ┌────────┐
│ Client │          │  Flask  │          │   Redis   │          │ Worker │
└───┬────┘          └────┬────┘          └─────┬─────┘          └───┬────┘
    │                    │                     │                    │
    │  POST /upload      │                     │                    │
    │  (MP3 file)        │                     │                    │
    │───────────────────>│                     │                    │
    │                    │                     │                    │
    │                    │  Generate job_id    │                    │
    │                    │  Save to storage/   │                    │
    │                    │  Convert MP3→WAV    │                    │
    │                    │─────────────────────│                    │
    │                    │                     │                    │
    │                    │  enqueue(process)   │                    │
    │                    │────────────────────>│                    │
    │                    │                     │                    │
    │  { job_id }        │                     │                    │
    │<───────────────────│                     │                    │
    │                    │                     │   dequeue()        │
    │                    │                     │<───────────────────│
    │                    │                     │                    │
    │                    │                     │   JOB DATA         │
    │                    │                     │───────────────────>│
    │                    │                     │                    │
    │                    │                     │                    │  PROCESSING...
    │                    │                     │                    │  (2-5 minutes)
    │                    │                     │                    │
```

### Status Polling Flow

```
┌────────┐          ┌─────────┐          ┌───────────┐
│ Client │          │  Flask  │          │   Redis   │
└───┬────┘          └────┬────┘          └─────┬─────┘
    │                    │                     │
    │  GET /status/abc   │                     │
    │───────────────────>│                     │
    │                    │  get_job(abc)       │
    │                    │────────────────────>│
    │                    │                     │
    │                    │  { status, progress}│
    │                    │<────────────────────│
    │                    │                     │
    │  { processing: 45%}│                     │
    │<───────────────────│                     │
    │                    │                     │
    │    ... repeat every 2 seconds ...        │
    │                    │                     │
    │  GET /status/abc   │                     │
    │───────────────────>│                     │
    │                    │                     │
    │  { completed }     │                     │
    │<───────────────────│                     │
    │                    │                     │
```

### Playback Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  React App                                                           │   │
│  │                                                                      │   │
│  │  ┌──────────────┐      ┌───────────────────┐      ┌──────────────┐  │   │
│  │  │ ChordDisplay │ ←──  │ useAudioPlayer()  │  ──→ │ Timeline     │  │   │
│  │  │              │      │                   │      │              │  │   │
│  │  │ Shows: "Am"  │      │ currentTime: 45.2 │      │ Playhead ──│ │  │   │
│  │  └──────────────┘      │ duration: 180.5   │      └──────────────┘  │   │
│  │                        │ isPlaying: true   │                        │   │
│  │                        └─────────┬─────────┘                        │   │
│  │                                  │                                  │   │
│  │                    ┌─────────────▼─────────────┐                    │   │
│  │                    │      Web Audio API        │                    │   │
│  │                    │                           │                    │   │
│  │                    │  ┌─────────────────────┐  │                    │   │
│  │                    │  │ AudioContext        │  │                    │   │
│  │                    │  │ ├─ AudioBuffer      │  │                    │   │
│  │                    │  │ ├─ GainNode         │──┼──→ 🔊 Speakers     │   │
│  │                    │  │ └─ AnalyserNode     │  │                    │   │
│  │                    │  └─────────────────────┘  │                    │   │
│  │                    │                           │                    │   │
│  │                    └───────────────────────────┘                    │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Processing Modes

Users can choose processing mode based on speed vs quality tradeoff:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FAST MODE (~30 seconds)                                                    │
│  ════════════════════════                                                   │
│                                                                             │
│  input.wav ─────────────────────────────────────→ Chordino → chords.json   │
│                                                                             │
│  • Skips Demucs entirely                                                    │
│  • Chord detection on full mix (vocals may confuse detection)               │
│  • Accuracy: 70-75%                                                         │
│  • Best for: acoustic songs, quick preview                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  BALANCED MODE (~2-3 minutes) ⭐ RECOMMENDED                                │
│  ═══════════════════════════════════════════                                │
│                                                                             │
│  input.wav → Demucs (--two-stems) → no_vocals.wav → Chordino → chords.json │
│                                                                             │
│  • Fast vocal-only separation                                               │
│  • Chord detection on instrumental                                          │
│  • Accuracy: 80-85%                                                         │
│  • Best for: most songs                                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  QUALITY MODE (~4-5 minutes)                                                │
│  ═══════════════════════════                                                │
│                                                                             │
│  input.wav → Demucs (full) → bass + drums + other → Chordino → chords.json │
│                                                                             │
│  • Full 4-stem separation                                                   │
│  • Can isolate "other" stem (cleaner harmony, no drums)                     │
│  • Accuracy: 85-90%                                                         │
│  • Best for: complex arrangements, heavy drums                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Mode Comparison

| Mode | CPU Time | Memory | Accuracy | Use Case |
|------|----------|--------|----------|----------|
| **Fast** | ~30 sec | 1 GB | 70-75% | Quick preview, simple songs |
| **Balanced** | ~2-3 min | 4 GB | 80-85% | Default for most songs |
| **Quality** | ~4-5 min | 4 GB | 85-90% | Complex/busy arrangements |

---

## 🎵 Audio Processing Pipeline Details

### Pipeline Stages (Balanced Mode)

```
INPUT                STAGE 1              STAGE 2              STAGE 3              STAGE 4              OUTPUT
─────                ───────              ───────              ───────              ───────              ──────

                     ┌─────────────┐
                     │   DEMUCS    │
                     │ htdemucs    │      ┌─────────────┐
                     │ --two-stems │ ───→ │  CHORDINO   │
                     │             │      │  Vamp       │      ┌─────────────┐
 ┌──────────┐        │ CPU: ~3min  │      │  Plugin     │ ───→ │  MIDI GEN   │
 │          │        │ RAM: ~4GB   │      │             │      │  pretty_midi│      ┌─────────────┐
 │  input   │        └──────┬──────┘      │ CPU: ~10sec │      │             │ ───→ │  FLUIDSYNTH │      ┌──────────┐
 │  .mp3    │ ───────────→  │             │ RAM: ~1GB   │      │ CPU: ~1sec  │      │  + soundfont│ ───→ │ backing  │
 │          │               │             └──────┬──────┘      │ RAM: ~100MB │      │             │      │ .wav     │
 └──────────┘               │                    │             └──────┬──────┘      │ CPU: ~5sec  │      └──────────┘
                            │                    │                    │             │ RAM: ~500MB │
                            ▼                    ▼                    ▼             └──────┬──────┘
                    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐           │
                    │ vocals.wav    │    │ chords.json   │    │ backing.mid   │           ▼
                    │ no_vocals.wav │    │               │    │               │    ┌───────────────┐
                    └───────────────┘    │ [             │    │ MIDI notes    │    │ backing.wav   │
                                         │   {time: 0.0, │    │ with timing,  │    │               │
                                         │    chord: C}, │    │ velocity,     │    │ Playable      │
                                         │   {time: 2.5, │    │ duration      │    │ guitar audio  │
                                         │    chord: Am},│    │               │    │               │
                                         │   ...         │    └───────────────┘    └───────────────┘
                                         │ ]             │
                                         └───────────────┘
```

### Performance by Mode

| Mode | MP3→WAV | Demucs | Chordino | MIDI+Render | **Total** |
|------|---------|--------|----------|-------------|-----------|
| Fast | 5 sec | SKIP | 10 sec | 6 sec | **~20-30 sec** |
| Balanced | 5 sec | 2-3 min | 10 sec | 6 sec | **~2-3 min** |
| Quality | 5 sec | 4-5 min | 10 sec | 6 sec | **~4-5 min** |

---

## 🎹 Pitch Transposition Architecture

### Chord Transposition Flow

```
INPUT                    PROCESS                         OUTPUT
─────                    ───────                         ──────

 User selects:           ┌─────────────────────────┐
 pitch = -2              │  Transpose Algorithm    │
                         │                         │
 ┌─────────────────┐     │  For each chord:        │     ┌─────────────────┐
 │ Original Chords │     │  ┌─────────────────┐   │     │ Transposed      │
 │                 │     │  │ Parse chord     │   │     │                 │
 │ C, Am, F, G     │────→│  │ "Am7" → A=9, m7 │   │────→│ Bb, Gm, Eb, F   │
 │                 │     │  │                 │   │     │                 │
 │ (chords.json)   │     │  │ Shift root      │   │     │ (transposed.json│
 └─────────────────┘     │  │ (9 + -2) % 12   │   │     └────────┬────────┘
                         │  │ = 7 = G         │   │              │
                         │  │                 │   │              │
                         │  │ Rebuild chord   │   │              ▼
                         │  │ G + m7 = "Gm7"  │   │     ┌─────────────────┐
                         │  └─────────────────┘   │     │ MIDI Generator  │
                         │                         │     │ (same as before)│
                         └─────────────────────────┘     │                 │
                                                         │ backing_t-2.mid │
                                                         └────────┬────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │ FluidSynth      │
                                                         │                 │
                                                         │ backing_t-2.wav │
                                                         └─────────────────┘
```

### Note Number Mapping

```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ C  │ C# │ D  │ D# │ E  │ F  │ F# │ G  │ G# │ A  │ A# │ B  │
│ 0  │ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │ 8  │ 9  │ 10 │ 11 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘

Example: Transpose Am → pitch -3

  A = 9
  9 + (-3) = 6
  6 % 12 = 6
  6 = F#
  
  Result: F#m
```

---

## 🎨 Frontend Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               App.jsx                                        │
│                                                                              │
│  State:                                                                      │
│  ├── jobId: string | null                                                   │
│  ├── status: 'idle' | 'uploading' | 'processing' | 'ready' | 'error'       │
│  ├── songData: { chords, backingUrl, duration }                            │
│  └── pitch: number (-6 to +6)                                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                      │    │
│  │  {status === 'idle' && <FileUpload onUpload={handleUpload} />}      │    │
│  │                                                                      │    │
│  │  {status === 'processing' && <ProgressBar job={jobId} />}           │    │
│  │                                                                      │    │
│  │  {status === 'ready' && (                                            │    │
│  │    <>                                                                │    │
│  │      <ChordDisplay chords={songData.chords} time={currentTime} />   │    │
│  │      <AudioPlayer                                                   │    │
│  │        url={songData.backingUrl}                                    │    │
│  │        onTimeUpdate={setCurrentTime}                                │    │
│  │      />                                                             │    │
│  │      <PitchSlider value={pitch} onChange={handlePitchChange} />     │    │
│  │      <Timeline chords={songData.chords} time={currentTime} />       │    │
│  │    </>                                                              │    │
│  │  )}                                                                  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


Component Tree:

App
├── FileUpload
│   └── DropZone (react-dropzone)
│
├── ProgressBar
│   └── useJobStatus() hook (polls API)
│
├── ChordDisplay
│   └── useCurrentChord() hook
│
├── AudioPlayer
│   ├── PlayPauseButton
│   ├── SeekBar
│   ├── VolumeSlider
│   └── useAudioPlayer() hook (Web Audio API)
│
├── PitchSlider
│   └── RangeInput (-6 to +6)
│
└── Timeline
    ├── ChordMarkers[]
    └── Playhead
```

---

## 🗃️ Data Models

### Job Object (Backend)

```python
@dataclass
class Job:
    id: str                    # UUID
    status: str                # queued | processing | completed | failed
    progress: int              # 0-100
    current_step: str          # stem_separation | chord_detection | midi_gen | rendering
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None
    
    # Paths (relative to storage/jobs/{id}/)
    original_path: str         # original.wav
    vocals_path: str           # vocals.wav
    no_vocals_path: str        # no_vocals.wav
    chords_path: str           # chords.json
    backing_path: str          # backing.wav
    
    # Metadata
    duration: float            # seconds
    transposed_versions: dict  # {-2: "backing_t-2.wav", 3: "backing_t3.wav"}
```

### Chord Object (JSON)

```json
{
  "chords": [
    {
      "time": 0.0,
      "duration": 2.5,
      "chord": "C",
      "root": "C",
      "type": "major"
    },
    {
      "time": 2.5,
      "duration": 2.0,
      "chord": "Am",
      "root": "A",
      "type": "minor"
    }
  ],
  "metadata": {
    "total_duration": 180.5,
    "detected_key": "C major",
    "tempo_estimate": 120
  }
}
```

### Song Data (Frontend)

```typescript
interface SongData {
  jobId: string;
  status: 'processing' | 'ready' | 'error';
  progress: number;
  
  chords: Chord[];
  backingUrl: string;
  originalUrl: string;
  duration: number;
  
  currentPitch: number;
  transposedChords: Chord[];  // After pitch shift
  transposedBackingUrl: string;
}

interface Chord {
  time: number;
  duration: number;
  chord: string;
}
```

---

## 🔐 Security Considerations

### Input Validation

```python
# File upload constraints
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg'}
MAX_DURATION = 600  # 10 minutes

# Rate limiting (per IP)
MAX_UPLOADS_PER_HOUR = 10
MAX_CONCURRENT_JOBS = 2
```

### Storage Security

```
storage/
└── jobs/
    └── {uuid}/        ← UUID prevents enumeration
        ├── original.wav
        └── ...

# Cleanup policy
- Delete jobs older than 24 hours
- Delete failed jobs after 1 hour
- Maximum storage per user: 1 GB
```

---

## 📊 Monitoring & Logging

### Key Metrics to Track

```python
# Processing metrics
job_processing_duration_seconds  # Histogram
job_status_count                 # Counter by status
stem_separation_duration         # Histogram
chord_detection_accuracy         # Gauge (manual input)

# System metrics
cpu_usage_percent
memory_usage_bytes
disk_usage_bytes
active_jobs_count

# API metrics
request_count                    # Counter by endpoint
request_duration_seconds         # Histogram
error_count                      # Counter by error type
```

### Logging Format

```python
# Structured logging
{
    "timestamp": "2026-04-27T10:30:00Z",
    "level": "INFO",
    "job_id": "abc123",
    "stage": "chord_detection",
    "message": "Detected 42 chord changes",
    "duration_ms": 8500,
    "chords_count": 42
}
```

---

## 🚀 Deployment Architecture

### Development (Local)

```
┌─────────────────────────────────────────────────────────────┐
│  Your Machine                                                │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ Frontend   │  │ Backend    │  │ Redis (Docker)         │ │
│  │ localhost  │  │ localhost  │  │ localhost:6379         │ │
│  │ :5173      │  │ :5000      │  │                        │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
│                                                              │
│  Storage: ./storage/jobs/                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Production (Free Tier)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌─────────────────────┐          ┌─────────────────────────────────────┐   │
│  │     VERCEL          │          │     HUGGING FACE SPACES             │   │
│  │  (Static Frontend)  │          │  (Flask + Worker)                   │   │
│  │                     │   API    │                                     │   │
│  │  React App          │ ───────→ │  ┌─────────────┐  ┌─────────────┐  │   │
│  │  (CDN deployed)     │          │  │ Flask API   │  │ RQ Worker   │  │   │
│  │                     │          │  │ (Gunicorn)  │  │             │  │   │
│  │  surunplugged       │          │  └──────┬──────┘  └──────┬──────┘  │   │
│  │  .vercel.app        │          │         │                │         │   │
│  │                     │          │         └────────┬───────┘         │   │
│  └─────────────────────┘          │                  │                 │   │
│                                   │         ┌────────▼────────┐        │   │
│                                   │         │ Persistent      │        │   │
│                                   │         │ Storage         │        │   │
│                                   │         │ (/data/)        │        │   │
│                                   │         └─────────────────┘        │   │
│                                   │                                     │   │
│                                   │  surunplugged.hf.space              │   │
│                                   └─────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

*Architecture Document v1.0 - April 2026*
