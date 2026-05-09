# SurUnplugged 🎸

Create acoustic/unplugged-style backing tracks for singing practice. Perfect for amateur singers who want guitar backing that matches their vocal range.

## What it does

Upload any song and get a clean acoustic backing track:
- **Separates real instruments** from the original song using AI (Demucs)
- **Adjusts pitch** to match your voice (±12 semitones)
- **Changes speed** for practice (0.5x to 2.0x)

## 4 Backing Track Strategies

| Strategy | Name | Description | Best For |
|----------|------|-------------|----------|
| **A** | Other Only | Uses guitar/piano stems from original | Acoustic songs (Kabira, Tum Hi Ho) |
| **B** | Instrumental | Full instrumental (drums + bass + other) | Full karaoke feel |
| **C** | Acoustic Mix | Other stem + light bass | Clean unplugged style |
| **D** | MIDI Generated | AI-generated guitar from detected chords | When stems don't work |

## Quick Start (Testing)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Test with your song (strategy A recommended for acoustic songs)
python test_pipeline.py ~/Music/kabira.mp3 A

# Adjust pitch and speed
python test_pipeline.py ~/Music/song.mp3 A --pitch -2 --speed 0.8
```

## Tech Stack

- **Backend**: Python/Flask
- **Stem Separation**: Demucs (Facebook AI)
- **Audio Processing**: librosa, soundfile
- **MIDI Generation**: pretty_midi + FluidSynth (fallback)
- **Frontend**: React + Vite (coming soon)

## Project Structure

```
SurUnplugged/
├── backend/
│   ├── services/
│   │   ├── stem_separator.py    # Demucs wrapper
│   │   ├── stem_mixer.py        # Mix stems (strategies A/B/C)
│   │   ├── audio_processor.py   # Pitch shift & speed change
│   │   ├── chord_detector.py    # Chord detection (for strategy D)
│   │   └── midi_generator.py    # MIDI generation (for strategy D)
│   ├── test_pipeline.py         # Command-line testing
│   └── api/routes.py            # REST API
├── docs/
└── frontend/                    # Coming soon
```

## API Endpoints

- `GET /api/strategies` - List available backing strategies
- `POST /api/process` - Process a song with strategy/pitch/speed
- `POST /api/adjust/{job_id}` - Adjust pitch/speed for existing job
- `GET /api/audio/{job_id}/{file}` - Download audio files

## License

MIT