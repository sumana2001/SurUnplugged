# SurUnplugged - Project Context

> **Living document for tracking development progress, decisions, and context**
> 
> Update this file as we build the project. Reference it when resuming work.

---

## 📋 Quick Reference

| Item | Value |
|------|-------|
| **Project Name** | SurUnplugged |
| **Purpose** | Acoustic guitar backing generator with pitch control |
| **Target User** | Amateur singers (personal use, shared free) |
| **Tech Stack** | Flask (Python) + React (Vite) + Tailwind |
| **Status** | 🟡 Planning Complete |

---

## 🎯 Current Phase

### Phase: 0 - Environment Setup
**Status**: Not Started

**Next Action**: Verify system dependencies are installed

---

## 📝 Session Log

### Session 1: April 27, 2026 - Project Planning
**What we did:**
- Created PROJECT_SPEC.md with full technical specification
- Created FEASIBILITY.md with risk analysis
- Created DEVELOPMENT_PLAN.md with vibe coding approach
- Decided on React + Vite instead of vanilla JS for frontend

**Key Decisions:**
1. **Frontend Framework**: React + Vite + Tailwind (not vanilla JS)
2. **Backend**: Python Flask (familiar to developer)
3. **Processing**: CPU-only (willing to wait)
4. **MVP Scope**: Core features only (upload → guitar backing → pitch control)
5. **Deployment Target**: Local first, then Hugging Face/Vercel (free)

**Open Questions:**
- None at this time

---

## 🏗️ Architecture Decisions

### ADR-001: Python Flask over Go
**Decision**: Use Flask for backend
**Reason**: Developer more comfortable with Python, simpler ML library integration
**Trade-offs**: Slightly lower performance, but irrelevant at personal scale

### ADR-002: React + Vite over vanilla JS
**Decision**: Use React with Vite for frontend
**Reason**: Modern developer experience, component reusability, easier state management
**Trade-offs**: Requires build step, slightly more complex setup

### ADR-003: Redis Queue over Celery
**Decision**: Use RQ (Redis Queue) for background tasks
**Reason**: Simpler than Celery, sufficient for this use case
**Trade-offs**: Less features, but we don't need them

### ADR-004: Demucs htdemucs model
**Decision**: Use htdemucs (hybrid transformer) model
**Reason**: Best quality-to-speed ratio, --two-stems mode for efficiency
**Trade-offs**: Still slow on CPU, but acceptable

### ADR-005: Chordino for chord detection
**Decision**: Start with Chordino via Vamp
**Reason**: Standard tool, good accuracy on pop/rock
**Fallback**: librosa chromagram if Chordino installation fails

### ADR-006: Three Processing Modes
**Decision**: Let user choose between Fast/Balanced/Quality modes
**Reason**: Reduces CPU load when not needed, gives users control
**Options**:
- Fast: Skip Demucs, chord detect on full mix (~30s, 70-75% accuracy)
- Balanced: Demucs --two-stems only (~2-3 min, 80-85% accuracy)  
- Quality: Full 4-stem separation (~4-5 min, 85-90% accuracy)

---

## 🔧 Environment Setup Status

### System Dependencies
- [ ] Python 3.10+ 
- [ ] Node.js 18+
- [ ] FFmpeg
- [ ] FluidSynth
- [ ] Vamp plugin SDK
- [ ] Chordino plugin

### Python Environment
- [ ] Virtual environment created
- [ ] requirements.txt installed
- [ ] Demucs verified working
- [ ] librosa verified working
- [ ] pretty_midi verified working

### Node Environment
- [ ] npm/yarn working
- [ ] Vite project initialized
- [ ] Tailwind configured

### Assets
- [ ] Guitar soundfont downloaded
- [ ] Test MP3 files ready

---

## 🐛 Known Issues & Workarounds

*None yet - this section will track bugs and their solutions*

<!--
Example format:
### Issue: Demucs runs out of memory
**Symptoms**: Crashes on songs > 5 minutes
**Workaround**: Process in chunks or use --segment flag
**Status**: Resolved / Open
-->

---

## 📁 File Structure Progress

```
SurUnplugged/
├── docs/
│   ├── PROJECT_SPEC.md       ✅ Created
│   ├── FEASIBILITY.md        ✅ Created
│   ├── DEVELOPMENT_PLAN.md   ✅ Created
│   ├── PROJECT_CONTEXT.md    ✅ Created (this file)
│   └── ARCHITECTURE.md       🔲 To create
│
├── backend/                   🔲 Not started
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── api/
│   ├── services/
│   ├── tasks/
│   └── utils/
│
├── frontend/                  🔲 Not started
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api/
│   └── ...
│
├── assets/                    🔲 Not started
│   └── soundfonts/
│
└── storage/                   🔲 Not started (created at runtime)
```

---

## 🎵 Test Songs

Songs to use for testing (across different genres):

| Song | Artist | Genre | Expected Chords | Notes |
|------|--------|-------|-----------------|-------|
| Wonderwall | Oasis | Rock | Em7, G, Dsus4, A7sus4 | Good test |
| Let It Be | Beatles | Pop | C, G, Am, F | Simple I-V-vi-IV |
| Hotel California | Eagles | Rock | Bm, F#, A, E, G, D, Em | Complex |
| *Your choice* | - | - | - | Personal favorites |

---

## 🔗 Useful Links

### Documentation
- [Demucs GitHub](https://github.com/facebookresearch/demucs)
- [Chordino](https://www.isophonics.net/nnls-chroma)
- [FluidSynth](https://www.fluidsynth.org/)
- [pretty_midi](https://craffel.github.io/pretty-midi/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

### Soundfonts
- [GeneralUser GS](https://schristiancollins.com/generaluser.php)
- [Musical Artifacts](https://musical-artifacts.com/artifacts?formats=sf2)

### Deployment
- [Hugging Face Spaces](https://huggingface.co/spaces)
- [Vercel](https://vercel.com/)
- [Railway](https://railway.app/)

---

## 💡 Ideas for Later

*Features to consider after MVP*

1. **Multiple guitar styles** - fingerpicking, ballad, pop strum
2. **Reverb/effects** - Add ambience to guitar output
3. **Vocal markers** - Show "sing here" indicators
4. **Export mix** - Download final backing track
5. **Song library** - Save and revisit processed songs
6. **Collaborative playlists** - Share with friends
7. **Mobile app** - React Native version

---

## 📊 Metrics & Performance

*Will track after initial implementation*

| Metric | Target | Actual |
|--------|--------|--------|
| Processing time (3min song) | < 5 min | TBD |
| Chord accuracy (pop songs) | > 80% | TBD |
| Memory usage | < 4GB | TBD |
| UI responsiveness | < 100ms | TBD |

---

## 🗓️ Timeline

| Phase | Planned | Actual | Status |
|-------|---------|--------|--------|
| Phase 0: Setup | Day 1 | - | 🔲 Not Started |
| Phase 1: Backend Foundation | Days 2-4 | - | 🔲 Not Started |
| Phase 2: Audio Pipeline | Days 5-9 | - | 🔲 Not Started |
| Phase 3: Pitch | Days 10-11 | - | 🔲 Not Started |
| Phase 4: Frontend | Days 12-16 | - | 🔲 Not Started |
| Phase 5: Polish | Days 17-19 | - | 🔲 Not Started |
| Phase 6: Deploy | Days 20-21 | - | 🔲 Not Started |

---

*Last Updated: April 27, 2026*
