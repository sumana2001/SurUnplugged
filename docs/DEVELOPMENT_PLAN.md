# SurUnplugged - Development Plan

## 🎯 Vibe Coding Approach

This is a **collaborative vibe coding** project where:
- **AI (me)**: Writes most of the code, handles boilerplate, debugging, and complex logic
- **You**: Make decisions, test locally, provide feedback, handle environment setup

### How We'll Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIBE CODING WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  YOU                              AI (ME)                       │
│  ───                              ───────                       │
│  • Set up environment             • Generate code               │
│  • Run commands                   • Explain what code does      │
│  • Test features                  • Debug errors you share      │
│  • Share error messages           • Suggest architecture        │
│  • Make product decisions         • Write documentation         │
│  • Click around the UI            • Refactor when needed        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 Development Phases

### Phase 0: Environment Setup (Day 1)
**Your responsibility with my guidance**

#### Tasks:
- [ ] Install Python 3.10+ 
- [ ] Install Node.js 18+ and npm
- [ ] Install system dependencies (FFmpeg, FluidSynth)
- [ ] Install Vamp plugin SDK + Chordino
- [ ] Download a guitar soundfont
- [ ] Clone/initialize the repository

#### Commands I'll Give You:
```bash
# macOS setup
brew install python@3.10 node ffmpeg fluidsynth

# Create project structure
mkdir -p backend frontend assets/soundfonts storage/jobs

# Python virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate
```

#### Verification Tests:
```bash
# Each of these should work
python3 --version      # 3.10+
node --version         # 18+
ffmpeg -version        # Any version
fluidsynth --version   # Any version
```

---

### Phase 1: Backend Foundation (Days 2-4)
**I write, you run and test**

#### 1.1 Flask App Skeleton
```
backend/
├── app.py              # Flask app with CORS
├── config.py           # Settings (paths, limits)
├── requirements.txt    # Dependencies
└── api/
    └── routes.py       # /upload, /status, /result endpoints
```

**Milestone**: Upload an MP3, get a job_id back, see it in /storage/jobs/

#### 1.2 File Processing Basics
- MP3 → WAV conversion
- Job status tracking (in-memory for now)

**Milestone**: Upload MP3, download WAV conversion

#### 1.3 Redis Queue Setup
- Install Redis locally or use Docker
- Background job processing

**Milestone**: Upload triggers background job, status endpoint works

---

### Phase 2: Audio Processing Pipeline (Days 5-9)
**The heart of the application**

#### 2.0 Processing Modes Implementation
The pipeline supports three modes (user selectable):

| Mode | What Happens | Time |
|------|--------------|------|
| **Fast** | Skip Demucs → Chordino on full mix | ~30s |
| **Balanced** | Demucs --two-stems → Chordino | ~2-3 min |
| **Quality** | Full Demucs → Chordino on "other" | ~4-5 min |

#### 2.1 Demucs Integration (Balanced/Quality modes)
```python
# services/stem_separator.py
def separate_stems(input_wav, output_dir, mode="balanced"):
    """Run Demucs to separate vocals from accompaniment
    
    mode='balanced': --two-stems (fast, vocals + no_vocals)
    mode='quality': full separation (vocals, drums, bass, other)
    """
```

**Your Test**: 
1. Upload a song you know well (try both Balanced and Quality modes)
2. Wait for processing
3. Listen to `vocals.wav` and `no_vocals.wav`
4. Compare quality vs time tradeoff

**Milestone**: Clean vocal/instrumental separation with mode support

#### 2.2 Chord Detection
```python
# services/chord_detector.py
def detect_chords(audio_path, mode="balanced"):
    """Extract chord progression using Chordino
    
    Fast mode: runs on full mix
    Balanced/Quality: runs on separated instrumental
    """
    return [{"time": 0.0, "chord": "C"}, ...]
```

**Your Test**:
1. Process same song with all 3 modes
2. Compare chord accuracy for each
3. Note the time vs accuracy tradeoff

**Milestone**: Chord JSON file generated with mode-appropriate accuracy

#### 2.3 MIDI Generation
```python
# services/midi_generator.py
def generate_midi(chords, style="soft_strum"):
    """Convert chord progression to MIDI"""
```

**Your Test**:
1. Open generated MIDI in a player
2. Does it sound like guitar strums?
3. Do the chords change at the right times?

**Milestone**: Playable MIDI file

#### 2.4 Audio Synthesis (FluidSynth)
```python
# services/audio_renderer.py
def render_midi_to_wav(midi_path, soundfont_path, output_path):
    """Convert MIDI to WAV using FluidSynth"""
```

**Your Test**:
1. Play the generated WAV
2. Does it sound like acoustic guitar?
3. Is the audio quality acceptable?

**Milestone**: Complete pipeline produces guitar backing WAV

---

### Phase 3: Pitch Transposition (Days 10-11)

#### 3.1 Transpose Logic
```python
# services/transpose.py
def transpose_chord(chord, semitones):
    """Shift chord by semitones: Am + 2 = Bm"""

def transpose_progression(chords, semitones):
    """Transpose entire progression"""
```

#### 3.2 Regeneration Endpoint
- POST /transpose triggers new MIDI → WAV generation
- Cache transposed versions

**Your Test**:
1. Original key: C major
2. Transpose +2: Should be D major
3. Transpose -3: Should be A major
4. Play and verify each sounds correct

**Milestone**: Pitch shifting works perfectly

---

### Phase 4: React Frontend (Days 12-16)
**Modern UI with React + Vite + Tailwind**

#### 4.1 Project Setup
```bash
cd frontend
npm create vite@latest . -- --template react
npm install -D tailwindcss postcss autoprefixer
npm install axios react-dropzone
npx tailwindcss init -p
```

#### 4.2 Component Development Order

**Step 1: Upload Component**
```jsx
// components/FileUpload.jsx
// Drag & drop zone, progress indicator
```
**Your Test**: Can you upload a file? Does it show progress?

**Step 2: Job Status Polling**
```jsx
// hooks/useJobStatus.js
// Poll /status/{job_id} every 2 seconds
```
**Your Test**: Does the UI update as processing progresses?

**Step 3: Audio Player**
```jsx
// components/AudioPlayer.jsx
// Play/pause, seek, volume using Web Audio API
```
**Your Test**: Can you play the backing track?

**Step 4: Chord Display**
```jsx
// components/ChordDisplay.jsx
// Large chord name, updates with playback
```
**Your Test**: Does the chord change at the right time?

**Step 5: Pitch Slider**
```jsx
// components/PitchSlider.jsx
// -6 to +6 slider, triggers regeneration
```
**Your Test**: Does changing pitch create a new backing track?

**Step 6: Timeline Visualization**
```jsx
// components/Timeline.jsx
// Visual bar with chord markers
```
**Your Test**: Can you see chord changes on the timeline?

---

### Phase 5: Polish & Integration (Days 17-19)

#### Tasks:
- [ ] Error handling (upload failures, processing errors)
- [ ] Loading states and skeletons
- [ ] Mobile-responsive design
- [ ] Edge case handling (long songs, weird formats)
- [ ] Performance optimization

#### Nice-to-haves (if time):
- [ ] Dark mode
- [ ] Keyboard shortcuts (space = play/pause)
- [ ] Remember last used pitch setting
- [ ] Download backing track

---

### Phase 6: Deployment (Days 20-21)

#### Backend (Hugging Face Spaces or Railway)
```dockerfile
# Dockerfile
FROM python:3.10-slim
RUN apt-get update && apt-get install -y ffmpeg fluidsynth
COPY backend/ /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:7860"]
```

#### Frontend (Vercel)
```bash
cd frontend
npm run build
# Deploy dist/ to Vercel
```

#### Environment Variables:
```
BACKEND_URL=https://your-space.hf.space
MAX_FILE_SIZE_MB=50
REDIS_URL=...
```

---

## 🎮 Your Role in Each Phase

### Phase 0-1: Setup
| Task | You Do | I Do |
|------|--------|------|
| Install dependencies | ✅ Run commands | Provide commands |
| Verify installations | ✅ Check output | Interpret errors |
| Create files | Run create command | Provide content |

### Phase 2-3: Backend
| Task | You Do | I Do |
|------|--------|------|
| Write Python code | Copy-paste | Generate code |
| Run tests | ✅ Execute | Provide test commands |
| Report accuracy | ✅ Listen & compare | Adjust algorithms |
| Debug errors | ✅ Share tracebacks | Fix issues |

### Phase 4: Frontend
| Task | You Do | I Do |
|------|--------|------|
| npm commands | ✅ Run | Provide commands |
| See if UI works | ✅ Click around | Generate components |
| Report visual bugs | ✅ Screenshot/describe | Fix CSS |
| Test on mobile | ✅ Open on phone | Responsive fixes |

### Phase 5-6: Deploy
| Task | You Do | I Do |
|------|--------|------|
| Create accounts | ✅ Vercel, HF | Provide links |
| Connect repos | ✅ GitHub setup | Configure files |
| Test production | ✅ Use the app | Fix prod issues |

---

## 🚨 When to Ask Me for Help

**Always share:**
1. **Error messages** - Full traceback, not just "it doesn't work"
2. **What you expected** vs **what happened**
3. **Steps you took** before the error
4. **Environment info** if relevant (OS, Python version)

**Examples of good questions:**
- "I ran `demucs input.wav` and got this error: [paste error]"
- "The chord detection says Am but I hear C major at 0:45"
- "The UI isn't updating when processing finishes, here's the console: [screenshot]"

---

## 📊 Progress Tracker

### Milestones Checklist

#### Phase 0: Environment ⬜
- [ ] Python 3.10+ working
- [ ] Node.js 18+ working
- [ ] FFmpeg installed
- [ ] FluidSynth installed
- [ ] Chordino/Vamp working
- [ ] Soundfont downloaded

#### Phase 1: Backend Foundation ⬜
- [ ] Flask app runs
- [ ] File upload works
- [ ] MP3 → WAV conversion
- [ ] Job status tracking
- [ ] Redis queue operational

#### Phase 2: Audio Pipeline ⬜
- [ ] Demucs separates stems
- [ ] Chordino detects chords
- [ ] MIDI generated correctly
- [ ] FluidSynth renders audio
- [ ] Full pipeline end-to-end

#### Phase 3: Pitch ⬜
- [ ] Transpose logic correct
- [ ] API endpoint works
- [ ] Cached versions working

#### Phase 4: Frontend ⬜
- [ ] Upload component
- [ ] Status polling
- [ ] Audio player
- [ ] Chord display synced
- [ ] Pitch slider functional
- [ ] Timeline visualization

#### Phase 5: Polish ⬜
- [ ] Error handling
- [ ] Mobile responsive
- [ ] Performance optimized

#### Phase 6: Deploy ⬜
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] End-to-end working

---

## 🎯 Definition of Done

The MVP is complete when you can:

1. ✅ Open the website on your phone
2. ✅ Upload "Wonderwall" by Oasis (or similar)
3. ✅ Wait 3-5 minutes for processing
4. ✅ See the chord progression: Em7, G, Dsus4, A7sus4...
5. ✅ Play the acoustic guitar backing
6. ✅ Shift pitch down 2 semitones to match your voice
7. ✅ Sing along comfortably
8. ✅ Feel good about it 🎸

---

## 🚀 Let's Start!

Ready to begin? Here's the first step:

**Tell me:**
1. What's your operating system? (macOS confirmed)
2. Do you have Python and Node.js installed?
3. Should I generate the initial project files now?

We'll take it one phase at a time!

---

*Plan created: April 2026*
