# Soundfonts for SurUnplugged

This directory should contain `.sf2` soundfont files for FluidSynth to render MIDI to audio.

## Recommended Soundfonts

### GeneralUser GS (Recommended)
- Size: ~31MB
- Quality: Excellent guitar sounds
- Download: https://schristiancollins.com/generaluser.php

### FluidR3_GM
- Size: ~141MB  
- Quality: Good all-around
- Usually available via package managers

## Setup Instructions

1. Download a soundfont file (`.sf2`)
2. Rename it to `guitar.sf2` or update `config.py`
3. Place it in this directory

## Quick Setup (macOS)

```bash
# Option 1: Download GeneralUser GS
curl -L -o GeneralUser.zip https://www.schristiancollins.com/soundfonts/GeneralUser_GS_v1.471.zip
unzip GeneralUser.zip
mv "GeneralUser GS v1.471.sf2" guitar.sf2
rm GeneralUser.zip

# Option 2: Use system soundfont (if available)
ln -s /opt/homebrew/share/soundfonts/default.sf2 guitar.sf2
```

## Notes

- Soundfont files are large and not committed to git
- The app will try to find system soundfonts as fallback
- Guitar-specific soundfonts produce better results than general MIDI
