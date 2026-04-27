#!/usr/bin/env python3
"""
SurUnplugged - Test Pipeline Script

This script tests the entire audio processing pipeline end-to-end.
Use this to validate the guitar backing output BEFORE building the frontend.

Usage:
    python test_pipeline.py path/to/your/song.mp3 [mode]

Modes:
    fast      - Skip stem separation, ~30 seconds (lower quality)
    balanced  - Vocal separation only, ~2-3 minutes (recommended)
    quality   - Full stem separation, ~4-5 minutes (best quality)

Example:
    python test_pipeline.py ~/Music/test_song.mp3 fast
"""

import sys
import shutil
from pathlib import Path
import time
import json

# Add the backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from utils.audio_utils import convert_to_wav, get_audio_duration, get_audio_info


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(step_num, text):
    """Print a numbered step"""
    print(f"[Step {step_num}] {text}")


def print_success(text):
    """Print success message"""
    print(f"  ✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"  ❌ {text}")


def print_info(text):
    """Print info message"""
    print(f"  ℹ️  {text}")


def test_dependencies():
    """Test that all required packages are installed"""
    print_header("Checking Dependencies")
    
    missing = []
    
    # Check Python packages
    packages = {
        "flask": "Flask",
        "librosa": "librosa", 
        "numpy": "numpy",
        "pretty_midi": "pretty-midi",
        "pydub": "pydub",
    }
    
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
            print_success(f"{pip_name}")
        except ImportError:
            print_error(f"{pip_name} - NOT INSTALLED")
            missing.append(pip_name)
    
    # Check demucs separately (it's heavy)
    try:
        import demucs
        print_success("demucs")
    except ImportError:
        print_error("demucs - NOT INSTALLED (needed for balanced/quality modes)")
        missing.append("demucs")
    
    # Check command-line tools
    import subprocess
    
    for tool in ["ffmpeg", "fluidsynth"]:
        try:
            result = subprocess.run([tool, "--version"], capture_output=True)
            if result.returncode == 0:
                print_success(f"{tool} (CLI)")
            else:
                print_error(f"{tool} (CLI) - not working")
                missing.append(tool)
        except FileNotFoundError:
            print_error(f"{tool} (CLI) - NOT FOUND")
            missing.append(tool)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join([p for p in missing if p not in ["ffmpeg", "fluidsynth"]]))
        return False
    
    print("\n✅ All dependencies OK!")
    return True


def test_soundfont():
    """Check if soundfont is available"""
    print_header("Checking Soundfont")
    
    from services.audio_renderer import get_soundfont_info
    
    info = get_soundfont_info()
    
    print(f"  Configured path: {info['configured_path']}")
    print(f"  Configured exists: {info['configured_exists']}")
    print(f"  System path: {info['system_path']}")
    print(f"  System exists: {info['system_exists']}")
    
    if info['available']:
        print_success("Soundfont available!")
        return True
    else:
        print_error("No soundfont found!")
        print("\nTo fix, download a soundfont:")
        print("  1. Visit: https://schristiancollins.com/generaluser.php")
        print("  2. Download GeneralUser GS")
        print("  3. Extract and copy .sf2 file to:")
        print(f"     {config.SOUNDFONT_PATH}")
        return False


def run_pipeline(input_file: Path, mode: str = "fast"):
    """Run the full processing pipeline on a test file"""
    
    print_header(f"Processing: {input_file.name}")
    print(f"Mode: {mode}")
    
    # Create test job directory
    test_job_id = f"test_{int(time.time())}"
    job_dir = config.JOBS_DIR / test_job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Job directory: {job_dir}")
    
    start_time = time.time()
    
    try:
        # Step 1: Copy and convert to WAV
        print_step(1, "Converting to WAV...")
        
        input_wav = job_dir / "input.wav"
        
        if input_file.suffix.lower() == ".wav":
            shutil.copy(input_file, input_wav)
        else:
            convert_to_wav(input_file, input_wav)
        
        duration = get_audio_duration(input_wav)
        print_success(f"Converted! Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        
        # Step 2: Stem separation (if not fast mode)
        mode_config = config.PROCESSING_MODES.get(mode, config.PROCESSING_MODES["fast"])
        
        if mode_config.get("use_demucs", False):
            print_step(2, f"Separating stems with Demucs ({mode_config.get('demucs_mode', 'two-stems')})...")
            print_info("This will take a few minutes on CPU...")
            
            from services.stem_separator import separate_stems
            
            stems = separate_stems(input_wav, job_dir, mode_config.get("demucs_mode", "two-stems"))
            chord_input = stems.get("no_vocals", input_wav)
            
            print_success(f"Stems separated! Using: {chord_input.name}")
        else:
            print_step(2, "Skipping stem separation (fast mode)")
            chord_input = input_wav
        
        # Step 3: Chord detection
        print_step(3, "Detecting chords...")
        
        from services.chord_detector import detect_chords
        
        chords = detect_chords(chord_input)
        
        # Save chords
        chords_file = job_dir / "chords.json"
        with open(chords_file, "w") as f:
            json.dump(chords, f, indent=2)
        
        print_success(f"Detected {len(chords)} chord changes")
        
        # Show first few chords
        print("\n  First 10 chords detected:")
        for i, chord in enumerate(chords[:10]):
            print(f"    {chord['time']:6.2f}s - {chord['chord']}")
        if len(chords) > 10:
            print(f"    ... and {len(chords) - 10} more")
        
        # Step 4: Generate MIDI
        print_step(4, "Generating MIDI backing track...")
        
        from services.midi_generator import generate_backing_midi
        
        midi_path = job_dir / "backing.mid"
        generate_backing_midi(chords, midi_path, style="soft_strum")
        
        print_success(f"MIDI generated: {midi_path.name}")
        
        # Step 5: Render to audio
        print_step(5, "Rendering MIDI to audio with FluidSynth...")
        
        from services.audio_renderer import render_midi_to_wav, get_soundfont_info
        
        sf_info = get_soundfont_info()
        if not sf_info['available']:
            print_error("No soundfont available! Cannot render audio.")
            print("  MIDI file was created - you can open it in GarageBand or similar.")
            return job_dir
        
        backing_wav = job_dir / "backing.wav"
        render_midi_to_wav(midi_path, backing_wav)
        
        print_success(f"Audio rendered: {backing_wav.name}")
        
        # Done!
        elapsed = time.time() - start_time
        
        print_header("✅ Processing Complete!")
        print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"\n  Output files in: {job_dir}")
        print(f"    - input.wav (original)")
        print(f"    - chords.json (detected chords)")
        print(f"    - backing.mid (MIDI file)")
        print(f"    - backing.wav (guitar backing track) ⬅️ LISTEN TO THIS!")
        
        if mode_config.get("use_demucs", False):
            print(f"    - vocals.wav (separated vocals)")
            print(f"    - no_vocals.wav (instrumental)")
        
        print(f"\n  🎧 To listen to the backing track:")
        print(f"     open {backing_wav}")
        print(f"\n  🎧 To compare with original:")
        print(f"     open {input_wav}")
        
        return job_dir
        
    except Exception as e:
        print_error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_transpose(job_dir: Path):
    """Test pitch transposition"""
    
    print_header("Testing Pitch Transposition")
    
    chords_file = job_dir / "chords.json"
    if not chords_file.exists():
        print_error("No chords.json found")
        return
    
    with open(chords_file) as f:
        chords = json.load(f)
    
    from services.transpose import transpose_progression
    
    # Test +2 semitones
    transposed = transpose_progression(chords, 2)
    
    print("  Original → Transposed (+2 semitones):")
    for i, (orig, trans) in enumerate(zip(chords[:5], transposed[:5])):
        print(f"    {orig['chord']:6} → {trans['chord']}")
    
    print_success("Transposition working!")


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🎸 SurUnplugged - Audio Pipeline Test                       ║
    ║                                                               ║
    ║   Test the guitar backing generation BEFORE building UI       ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies first
    if not test_dependencies():
        print("\n❌ Please install missing dependencies first.")
        print("   Then run this script again.")
        sys.exit(1)
    
    # Check soundfont
    has_soundfont = test_soundfont()
    
    # If no input file provided, just do dependency check
    if len(sys.argv) < 2:
        print_header("Usage")
        print("  python test_pipeline.py <path/to/song.mp3> [mode]")
        print("\n  Modes: fast, balanced, quality")
        print("  Default: fast (for quick testing)")
        print("\n  Example:")
        print("    python test_pipeline.py ~/Music/test_song.mp3")
        print("    python test_pipeline.py ~/Music/test_song.mp3 balanced")
        
        if not has_soundfont:
            print("\n⚠️  You need to install a soundfont first!")
        
        sys.exit(0)
    
    # Get input file
    input_file = Path(sys.argv[1]).expanduser()
    if not input_file.exists():
        print_error(f"File not found: {input_file}")
        sys.exit(1)
    
    # Get mode
    mode = sys.argv[2] if len(sys.argv) > 2 else "fast"
    if mode not in config.PROCESSING_MODES:
        print_error(f"Invalid mode: {mode}")
        print(f"  Valid modes: {', '.join(config.PROCESSING_MODES.keys())}")
        sys.exit(1)
    
    # Run the pipeline
    job_dir = run_pipeline(input_file, mode)
    
    if job_dir:
        # Test transpose
        test_transpose(job_dir)
        
        print_header("🎯 Next Steps")
        print("  1. Listen to backing.wav - does it sound like guitar unplugged?")
        print("  2. Compare chord detection accuracy with actual song")
        print("  3. Try different modes (fast vs balanced vs quality)")
        print("  4. Let me know what you think!")
        print("\n  If the sound isn't right, we can adjust:")
        print("    - Guitar strumming pattern (midi_generator.py)")
        print("    - Chord voicings (midi_generator.py)")
        print("    - Different soundfont (assets/soundfonts/)")
        print("    - Add reverb/effects (future enhancement)")


if __name__ == "__main__":
    main()
