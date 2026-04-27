# SurUnplugged - Feasibility Analysis

## 📊 Executive Summary

| Aspect | Feasibility | Confidence |
|--------|-------------|------------|
| **Technical** | ✅ Highly Feasible | 95% |
| **Cost** | ✅ Free (with constraints) | 100% |
| **Timeline** | ✅ MVP in 2-3 weeks | 85% |
| **Quality** | ⚠️ Good, not perfect | 80% |
| **Deployment** | ✅ Feasible (with limitations) | 85% |

**Overall Verdict**: ✅ **GO** - This project is achievable as described.

---

## 🔬 Technical Feasibility

### Component Analysis

#### 1. Stem Separation (Demucs)
| Factor | Assessment |
|--------|------------|
| **Availability** | ✅ Open source (MIT license) |
| **Quality** | ✅ State-of-the-art for free tools |
| **Performance (CPU)** | ⚠️ 2-5 min per song (3-4 min track) |
| **Memory Usage** | ⚠️ ~4GB RAM during processing |
| **Integration** | ✅ Python library, CLI available |

**Verdict**: ✅ Works perfectly. Just need async processing for CPU.

**Processing Modes** (user selectable for speed/quality tradeoff):
| Mode | What it does | Time | Accuracy |
|------|--------------|------|----------|
| Fast | Skip Demucs, run Chordino on full mix | ~30s | 70-75% |
| Balanced | Demucs --two-stems only | ~2-3 min | 80-85% |
| Quality | Full 4-stem separation | ~4-5 min | 85-90% |

```python
# Proven working code
import demucs.separate
demucs.separate.main(["--two-stems", "vocals", "-n", "htdemucs", "input.wav"])
```

#### 2. Chord Detection (Chordino)
| Factor | Assessment |
|--------|------------|
| **Availability** | ✅ Free Vamp plugin |
| **Quality** | ⚠️ 80-85% accuracy on clean audio |
| **Performance** | ✅ Real-time capable |
| **Integration** | ⚠️ Requires vamp-plugin-sdk |

**Known Limitations**:
- Struggles with heavy distortion
- May confuse similar chords (Am vs C, Dm vs F)
- Better on acoustic/pop than metal/electronic

**Mitigation**: Use `no_vocals.wav` (cleaner than full mix)

**Alternative Options** (if Chordino fails):
1. **librosa chromagram + template matching** - Pure Python, 70-75% accuracy
2. **autochord** - Neural network based, requires training
3. **madmom** - Academic quality, complex setup

**Verdict**: ⚠️ Start with Chordino, have fallback ready.

#### 3. MIDI Generation (pretty_midi)
| Factor | Assessment |
|--------|------------|
| **Availability** | ✅ Pure Python, pip installable |
| **Quality** | ✅ Precise control |
| **Complexity** | ✅ Simple API |

**Verdict**: ✅ No concerns.

#### 4. Audio Synthesis (FluidSynth)
| Factor | Assessment |
|--------|------------|
| **Availability** | ✅ Open source |
| **Quality** | ✅ Good with proper soundfonts |
| **Soundfonts** | ✅ Many free options |
| **Integration** | ⚠️ CLI or pyfluidsynth |

**Recommended Soundfonts** (all free):
1. **GeneralUser GS** (31MB) - Great guitar sounds
2. **Timbres of Heaven** (350MB) - Premium quality
3. **FluidR3_GM** (141MB) - Standard quality

**Verdict**: ✅ Works well.

#### 5. Web Audio API (Frontend)
| Factor | Assessment |
|--------|------------|
| **Browser Support** | ✅ All modern browsers |
| **Capabilities** | ✅ Mixing, effects, precise timing |
| **Complexity** | ⚠️ Learning curve, but manageable |

**Key Features Needed**:
- Loading and playing audio files ✅
- Volume control ✅
- Playback position tracking ✅
- Synchronized display updates ✅

**Verdict**: ✅ Well-supported, good documentation available.

---

## 💰 Cost Analysis

### Development Phase (Free)

| Resource | Cost | Notes |
|----------|------|-------|
| Development machine | $0 | Your existing computer |
| Python libraries | $0 | All open source |
| Soundfonts | $0 | Free options available |
| Testing | $0 | Use your own MP3s |

### Deployment Phase

#### Option 1: Minimal Free Tier
| Service | Cost | Capacity |
|---------|------|----------|
| **Hugging Face Spaces** | $0 | 2 vCPU, 16GB RAM, GPU available |
| **Frontend on Vercel** | $0 | Unlimited for static sites |
| **Total** | **$0/month** | ~10-20 songs/day |

#### Option 2: Light Usage (Recommended)
| Service | Cost | Capacity |
|---------|------|----------|
| **Railway** | $0-5 | $5 free credit, then pay-as-go |
| **Redis (Upstash)** | $0 | Free tier sufficient |
| **Total** | **$0-5/month** | ~50-100 songs/day |

#### Option 3: Self-Hosted (Best for no limits)
| Resource | Cost | Notes |
|----------|------|-------|
| Old laptop/Raspberry Pi | $0 | Already owned |
| Electricity | ~$5/month | If running 24/7 |
| Domain (optional) | $10/year | Optional |
| **Total** | **$0-10/month** | Unlimited |

**Verdict**: ✅ Completely achievable at $0/month for personal use.

---

## ⏱️ Timeline Feasibility

### MVP Development (2-3 Weeks)

```
Week 1: Foundation
├── Day 1-2: Project setup, Flask skeleton, file upload
├── Day 3-4: Integrate Demucs, test stem separation
├── Day 5-6: Integrate Chordino, test chord detection
└── Day 7: Connect pipeline, basic job queue

Week 2: Core Features
├── Day 8-9: MIDI generation, FluidSynth integration
├── Day 10-11: Pitch transposition logic
├── Day 12-13: Basic frontend (upload, playback)
└── Day 14: Frontend chord display, progress indicator

Week 3: Polish & Deploy
├── Day 15-16: UI improvements, timeline visualization
├── Day 17-18: Error handling, edge cases
├── Day 19-20: Deployment setup
└── Day 21: Testing with real songs
```

### Vibe Coding Assumptions
- 2-3 hours per day
- AI assistance for boilerplate
- Starting with working examples

**Risk Factors**:
- Chordino setup issues on your OS (-2 days)
- FluidSynth audio glitches (-1 day)
- Unexpected Demucs memory issues (-1 day)

**Buffer**: Plan for 3-4 weeks to be safe.

---

## 🎯 Quality Expectations

### What Will Work Well
1. **Popular songs with clear chord progressions** (Pop, Rock, Folk)
2. **Simple chord structures** (I-IV-V-I, I-V-vi-IV)
3. **Clean recordings** (studio quality)
4. **Acoustic-friendly genres**

### What Might Struggle
1. **Complex jazz harmony** (extended chords, substitutions)
2. **Heavy metal** (distorted guitars confuse detection)
3. **Electronic music** (synthesized sounds)
4. **Live recordings with audience noise**
5. **Very fast tempo changes**

### Expected Accuracy by Genre

| Genre | Chord Accuracy | Backing Quality |
|-------|----------------|-----------------|
| Pop | 85-90% | Excellent |
| Rock | 80-85% | Good |
| Folk/Acoustic | 90-95% | Excellent |
| Jazz | 60-70% | Fair |
| Metal | 50-70% | Poor |
| Electronic | 40-60% | Poor |

**Mitigation**: Add "simple mode" that reduces complex chords to triads.

---

## 🚧 Risk Assessment

### High Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| Chordino hard to install | Delays | Prepare fallback (librosa) |
| CPU processing too slow | UX impact | Set expectations, show progress |
| Soundfont sounds bad | Quality | Test multiple options early |

### Medium Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| Memory issues with long songs | Crashes | Limit file size, chunk processing |
| Hosting costs increase | Budget | Monitor usage, rate limit |
| Browser audio sync issues | UX bugs | Test early, fallback to simple player |

### Low Risk
| Risk | Impact | Mitigation |
|------|--------|------------|
| Copyright concerns | Legal | Personal use only disclaimers |
| Flask performance | Scale | Won't matter at personal scale |

---

## 🔄 Alternatives Considered

### Why Not Use Existing Solutions?

| Solution | Problem |
|----------|---------|
| **Chordify** | Paid for downloads, can't adjust pitch |
| **Ultimate Guitar** | No backing tracks, just tabs |
| **Moises.ai** | Paid subscription for full features |
| **Karaoke apps** | No pitch adjustment, full arrangements |

### Why This Approach?

The unique value is:
1. **Simplified guitar backing** (not full arrangement)
2. **Free pitch adjustment** (existing tools charge for this)
3. **Personal control** (no API limits)
4. **Learning opportunity** (interesting tech stack)

---

## 📋 Pre-requisites Checklist

Before starting development, verify:

### System Dependencies
- [ ] Python 3.10+ installed
- [ ] pip and virtualenv working
- [ ] FFmpeg installed (`ffmpeg -version`)
- [ ] FluidSynth installed (`fluidsynth --version`)
- [ ] 8GB+ RAM available
- [ ] 10GB free disk space

### Python Libraries (Test Installation)
```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Test installations
pip install demucs  # This also installs torch
pip install librosa
pip install pretty-midi
pip install vamp

# Test torch
python -c "import torch; print(torch.__version__)"

# Test demucs
demucs --help
```

### Chordino Setup (Critical Path)
```bash
# Ubuntu
sudo apt-get install vamp-plugin-sdk sonic-annotator

# macOS
brew install vamp-plugin-sdk
# Download Chordino from: https://www.isophonics.net/nnls-chroma

# Verify
vamp-simple-host -l | grep chordino
```

### Download Soundfont
```bash
# Download a free soundfont
wget https://musical-artifacts.com/artifacts/1228/GeneralUser_GS_1.471.zip
unzip GeneralUser_GS_1.471.zip -d soundfonts/
```

---

## ✅ Conclusion

### This Project IS Feasible Because:

1. **All components exist and are proven**
   - Demucs, Chordino, FluidSynth are mature tools
   - Many tutorials and examples available

2. **No novel research required**
   - We're integrating existing tools, not inventing algorithms

3. **Scope is appropriate**
   - MVP is focused (upload → process → play)
   - Advanced features are clearly separated

4. **Deployment is achievable**
   - Free tier options exist
   - Personal scale doesn't need production infrastructure

5. **Quality expectations are realistic**
   - 80% accuracy is acceptable for amateur use
   - "Pleasant, not perfect" is the goal

### Recommended Next Steps

1. **Verify pre-requisites** (checklist above)
2. **Start with smallest working piece** (Flask upload → Demucs → download stems)
3. **Build incrementally** (add chord detection, then MIDI, then frontend)
4. **Test with real songs early** (don't build everything before testing)

---

*Analysis completed: April 2026*
