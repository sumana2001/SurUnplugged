#!/usr/bin/env python3
"""
SurUnplugged - Test Pipeline Script (v2)

This script tests the entire audio processing pipeline end-to-end.
Supports 4 backing track strategies with pitch shifting and speed control.

Usage:
    python test_pipeline.py path/to/song.mp3 [strategy] [--pitch N] [--speed X]

Strategies:
    A (other_only)   - Uses 'other' stem only (guitars, piano). Best for acoustic songs!
    B (instrumental) - Full instrumental (drums + bass + other, no vocals)
    C (acoustic_mix) - Other stem + light bass. Clean unplugged style.
    D (midi)         - AI-generated guitar from detected chords (fallback)

Options:
    --pitch N    - Shift pitch by N semitones (-12 to +12). Use negative to lower.
    --speed X    - Change speed (0.5 to 2.0). 0.8 = slower for practice.

Examples:
    python test_pipeline.py ~/Music/kabira.mp3 A
    python test_pipeline.py ~/Music/tum_hi_ho.mp3 A --pitch -2 --speed 0.8
    python test_pipeline.py ~/Music/song.mp3 B --pitch 3
    python test_pipeline.py ~/Music/song.mp3 D  # Use MIDI fallback
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
        "soundfile": "soundfile",
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
        print_error("demucs - NOT INSTALLED (needed for stem separation)")
        missing.append("demucs")
    
    # Check command-line tools
    import subprocess
    
    cli_tools = [
        ("ffmpeg", ["-version"]),
        ("fluidsynth", ["--version"]),
    ]
    
    for tool, args in cli_tools:
        try:
            result = subprocess.run([tool] + args, capture_output=True)
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
    
    if info['available']:
        print_success("Soundfont available!")
        return True
    else:
        print_error("No soundfont found (needed for MIDI strategy D)")
        return False


# Strategy mapping
STRATEGY_MAP = {
    "A": "other_only",
    "B": "instrumental", 
    "C": "acoustic_mix",
    "D": "midi_generated",
    "other_only": "other_only",
    "instrumental": "instrumental",
    "acoustic_mix": "acoustic_mix",  
    "midi_generated": "midi_generated",
    "midi": "midi_generated",
}


def run_pipeline(
    input_file: Path, 
    strategy: str = "A",
    pitch_shift: int = 0,
    speed_factor: float = 1.0
):
    """
    Run the full processing pipeline with specified strategy.
    
    Args:
        input_file: Path to input audio file
        strategy: A/B/C/D or full name (other_only, instrumental, acoustic_mix, midi_generated)
        pitch_shift: Semitones to shift (-12 to +12)
        speed_factor: Speed multiplier (0.5 to 2.0)
    """
    
    # Map strategy letter to full name
    strategy = STRATEGY_MAP.get(strategy.upper() if len(strategy) == 1 else strategy, "other_only")
    
    print_header(f"Processing: {input_file.name}")
    print(f"Strategy: {strategy}")
    print(f"Pitch: {pitch_shift:+d} semitones" if pitch_shift != 0 else "Pitch: original")
    print(f"Speed: {speed_factor:.1f}x" if speed_factor != 1.0 else "Speed: original")
    
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
        
        #=============================================================
        # Strategy D: MIDI Generated (no stem separation needed)
        #=============================================================
        if strategy == "midi_generated":
            return run_midi_strategy(job_dir, input_wav, duration, pitch_shift, speed_factor, start_time)
        
        #=============================================================
        # Strategies A/B/C: Stem-based (need Demucs separation)
        #=============================================================
        
        # Step 2: Full stem separation with Demucs
        print_step(2, "Separating stems with Demucs (full 4-stem)...")
        print_info("This will take a few minutes on CPU. Get some coffee ☕")
        
        from services.stem_separator import separate_stems
        
        stems = separate_stems(input_wav, job_dir, "full")
        
        # Show available stems
        print_success("Stems separated!")
        available_stems = {}
        for stem_name in ["vocals", "drums", "bass", "other"]:
            stem_path = job_dir / f"{stem_name}.wav"
            if stem_path.exists():
                available_stems[stem_name] = stem_path
                print(f"      ✓ {stem_name}.wav")
        
        # Step 3: Create backing track based on strategy
        print_step(3, f"Creating backing track with strategy: {strategy}...")
        
        from services.stem_mixer import create_backing_track, BACKING_STRATEGIES
        
        strategy_info = BACKING_STRATEGIES.get(strategy, BACKING_STRATEGIES["other_only"])
        print_info(strategy_info["description"])
        
        backing_wav = job_dir / "backing.wav"
        
        create_backing_track(
            stem_paths=available_stems,
            output_path=backing_wav,
            strategy=strategy,
            semitones=pitch_shift,
            speed_factor=speed_factor,
        )
        
        print_success(f"Backing track created: {backing_wav.name}")
        
        # Save metadata
        metadata = {
            "strategy": strategy,
            "pitch_shift": pitch_shift,
            "speed_factor": speed_factor,
            "duration": duration,
            "stems_available": list(available_stems.keys()),
        }
        with open(job_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Done!
        elapsed = time.time() - start_time
        
        print_header("✅ Processing Complete!")
        print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"\n  Output files in: {job_dir}")
        print(f"    - input.wav (original)")
        print(f"    - vocals.wav / drums.wav / bass.wav / other.wav (separated)")
        print(f"    - backing.wav ⬅️ YOUR BACKING TRACK!")
        
        print(f"\n  🎧 Listen to the backing track:")
        print(f"     open {backing_wav}")
        
        print(f"\n  🎧 Compare with 'other' stem directly:")
        print(f"     open {job_dir / 'other.wav'}")
        
        return job_dir
        
    except Exception as e:
        print_error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_midi_strategy(job_dir: Path, input_wav: Path, duration: float, pitch_shift: int, speed_factor: float, start_time: float):
    """
    Run MIDI-based backing track generation (Strategy D).
    This is the fallback when stem separation doesn't work well.
    """
    
    print_step(2, "Running MIDI strategy (no stem separation)...")
    
    # Detect tempo and chords
    print_step(3, "Detecting tempo...")
    from services.chord_detector import detect_chords, detect_tempo
    
    detected_tempo = detect_tempo(input_wav)
    print_success(f"Detected tempo: {detected_tempo:.0f} BPM")
    
    # Adjust tempo for speed factor
    adjusted_tempo = detected_tempo * speed_factor
    
    # Auto-select style based on tempo
    if adjusted_tempo < 90:
        auto_style = "slow_ballad"
        print_info(f"Slow song → using 'slow_ballad' style")
    elif adjusted_tempo < 120:
        auto_style = "ballad"
        print_info(f"Mid-tempo → using 'ballad' style")
    else:
        auto_style = "continuous_strum"
        print_info(f"Upbeat → using 'continuous_strum' style")
    
    # Detect chords
    print_step(4, "Detecting chords...")
    chords = detect_chords(input_wav)
    
    # Transpose chords if pitch shift requested
    if pitch_shift != 0:
        from services.transpose import transpose_progression
        chords = transpose_progression(chords, pitch_shift)
        print_info(f"Transposed chords by {pitch_shift:+d} semitones")
    
    # Save chords
    chords_file = job_dir / "chords.json"
    with open(chords_file, "w") as f:
        json.dump({
            "tempo": detected_tempo,
            "adjusted_tempo": adjusted_tempo,
            "style": auto_style,
            "pitch_shift": pitch_shift,
            "chords": chords
        }, f, indent=2)
    
    print_success(f"Detected {len(chords)} chord changes")
    
    # Generate MIDI
    print_step(5, "Generating MIDI backing...")
    from services.midi_generator import generate_backing_midi
    
    midi_path = job_dir / "backing.mid"
    adjusted_duration = duration / speed_factor if speed_factor != 1.0 else duration
    
    generate_backing_midi(
        chords,
        midi_path,
        style=auto_style,
        tempo=int(adjusted_tempo),
        total_duration=adjusted_duration
    )
    
    print_success(f"MIDI generated: {midi_path.name}")
    
    # Render to audio
    print_step(6, "Rendering MIDI to audio...")
    from services.audio_renderer import render_midi_to_wav, get_soundfont_info
    
    sf_info = get_soundfont_info()
    if not sf_info['available']:
        print_error("No soundfont available! Cannot render audio.")
        print("  MIDI file was created - you can open it in GarageBand.")
        return job_dir
    
    backing_wav = job_dir / "backing.wav"
    render_midi_to_wav(midi_path, backing_wav)
    
    print_success(f"Audio rendered: {backing_wav.name}")
    
    # Save metadata
    metadata = {
        "strategy": "midi_generated",
        "pitch_shift": pitch_shift,
        "speed_factor": speed_factor,
        "tempo": detected_tempo,
        "adjusted_tempo": adjusted_tempo,
        "style": auto_style,
        "duration": duration,
    }
    with open(job_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Done!
    elapsed = time.time() - start_time
    
    print_header("✅ Processing Complete!")
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"\n  Output files in: {job_dir}")
    print(f"    - input.wav (original)")
    print(f"    - chords.json (detected chords)")
    print(f"    - backing.mid (MIDI file)")
    print(f"    - backing.wav ⬅️ YOUR BACKING TRACK!")
    
    print(f"\n  🎧 Listen to the backing track:")
    print(f"     open {backing_wav}")
    
    return job_dir


def test_reprocess(job_dir: Path, pitch_shift: int = 0, speed_factor: float = 1.0):
    """
    Reprocess an existing job with different pitch/speed.
    Useful for quickly testing different settings without re-running Demucs.
    """
    from services.audio_processor import process_audio
    
    print_header("Reprocessing with new settings")
    print(f"  Pitch: {pitch_shift:+d} semitones")
    print(f"  Speed: {speed_factor:.1f}x")
    
    other_wav = job_dir / "other.wav"
    backing_wav = job_dir / "backing.wav"
    
    if other_wav.exists():
        source = other_wav
    elif backing_wav.exists():
        source = backing_wav
    else:
        print_error("No source audio found to reprocess")
        return
    
    output_name = f"backing_p{pitch_shift:+d}_s{speed_factor:.1f}.wav"
    output_path = job_dir / output_name
    
    process_audio(source, output_path, pitch_shift, speed_factor)
    
    print_success(f"Created: {output_name}")
    print(f"\n  🎧 Listen: open {output_path}")


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                                                                       ║
    ║   🎸 SurUnplugged - Audio Pipeline Test (v2)                          ║
    ║                                                                       ║
    ║   Create guitar/acoustic backing tracks for singing practice          ║
    ║                                                                       ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies first
    if not test_dependencies():
        print("\n❌ Please install missing dependencies first.")
        sys.exit(1)
    
    # Check soundfont (only needed for MIDI strategy)
    has_soundfont = test_soundfont()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="SurUnplugged backing track generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Strategies:
  A (other_only)   - Uses 'other' stem (guitars, piano). BEST FOR ACOUSTIC SONGS!
  B (instrumental) - Full instrumental (drums + bass + other)
  C (acoustic_mix) - Other stem + light bass. Clean unplugged feel.
  D (midi)         - AI-generated guitar from chords (fallback)

Examples:
  python test_pipeline.py ~/Music/kabira.mp3 A
  python test_pipeline.py ~/Music/tum_hi_ho.mp3 A --pitch -2
  python test_pipeline.py ~/Music/song.mp3 C --pitch -3 --speed 0.8
  python test_pipeline.py ~/Music/song.mp3 D  # MIDI fallback
        """
    )
    parser.add_argument("input", nargs="?", help="Path to audio file (mp3, wav, etc.)")
    parser.add_argument("strategy", nargs="?", default="A", 
                        help="Strategy: A/B/C/D (default: A)")
    parser.add_argument("--pitch", type=int, default=0,
                        help="Pitch shift in semitones (-12 to +12)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speed factor (0.5 to 2.0)")
    
    args = parser.parse_args()
    
    # If no input file provided, show help
    if not args.input:
        print_header("Usage")
        print("  python test_pipeline.py <song.mp3> [strategy] [--pitch N] [--speed X]")
        print("\n  STRATEGIES:")
        print("    A  → Uses 'other' stem (guitars, piano) - BEST FOR ACOUSTIC SONGS!")
        print("    B  → Full instrumental (drums + bass + other)")  
        print("    C  → Other + light bass (clean unplugged)")
        print("    D  → AI-generated MIDI (fallback when stems don't work)")
        print("\n  OPTIONS:")
        print("    --pitch -2  → Lower pitch by 2 semitones (for higher voice)")
        print("    --pitch 3   → Raise pitch by 3 semitones")
        print("    --speed 0.8 → Slow down to 80% (for practice)")
        print("\n  EXAMPLES:")
        print("    python test_pipeline.py ~/Music/kabira.mp3 A")
        print("    python test_pipeline.py ~/Music/tum_hi_ho.mp3 A --pitch -2 --speed 0.8")
        
        if not has_soundfont:
            print("\n⚠️  Soundfont needed for MIDI strategy (D). See above.")
        
        sys.exit(0)
    
    # Validate input file
    input_file = Path(args.input).expanduser()
    if not input_file.exists():
        print_error(f"File not found: {input_file}")
        sys.exit(1)
    
    # Validate strategy
    valid_strategies = ["A", "B", "C", "D", "other_only", "instrumental", "acoustic_mix", "midi_generated", "midi"]
    if args.strategy.upper() not in [s.upper() for s in valid_strategies]:
        print_error(f"Invalid strategy: {args.strategy}")
        print(f"  Valid: A, B, C, D")
        sys.exit(1)
    
    # Validate pitch
    if not -12 <= args.pitch <= 12:
        print_error(f"Invalid pitch: {args.pitch}")
        print("  Range: -12 to +12 semitones")
        sys.exit(1)
    
    # Validate speed
    if not 0.5 <= args.speed <= 2.0:
        print_error(f"Invalid speed: {args.speed}")
        print("  Range: 0.5 to 2.0")
        sys.exit(1)
    
    # Run the pipeline!
    job_dir = run_pipeline(
        input_file, 
        strategy=args.strategy,
        pitch_shift=args.pitch,
        speed_factor=args.speed
    )
    
    if job_dir:
        print_header("🎯 What's Next?")
        print("  1. Listen to backing.wav - does it match your needs?")
        print("  2. Try different settings:")
        print(f"     --pitch -2  → Lower (if song is too high for you)")
        print(f"     --pitch 3   → Higher (if song is too low)")
        print(f"     --speed 0.8 → Slower (for practice)")
        print("\n  3. Try different strategies:")
        print("     A → Best for acoustic/unplugged songs")
        print("     B → Full karaoke instrumental")
        print("     C → Clean acoustic mix")
        print("     D → AI-generated (if stems don't sound good)")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
SurUnplugged - Test Pipeline Script (v2)

This script tests the entire audio processing pipeline end-to-end.
Supports 4 backing track strategies with pitch shifting and speed control.

Usage:
    python test_pipeline.py path/to/song.mp3 [strategy] [--pitch N] [--speed X]

Strategies:
    A (other_only)   - Uses 'other' stem only (guitars, piano). Best for acoustic songs!
    B (instrumental) - Full instrumental (drums + bass + other, no vocals)
    C (acoustic_mix) - Other stem + light bass. Clean unplugged style.
    D (midi)         - AI-generated guitar from detected chords (fallback)

Options:
    --pitch N    - Shift pitch by N semitones (-12 to +12). Use negative to lower.
    --speed X    - Change speed (0.5 to 2.0). 0.8 = slower for practice.

Examples:
    python test_pipeline.py ~/Music/kabira.mp3 A
    python test_pipeline.py ~/Music/tum_hi_ho.mp3 A --pitch -2 --speed 0.8
    python test_pipeline.py ~/Music/song.mp3 B --pitch 3
    python test_pipeline.py ~/Music/song.mp3 D  # Use MIDI fallback
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
    
    # ffmpeg uses -version (single dash), fluidsynth uses --version (double dash)
    cli_tools = [
        ("ffmpeg", ["-version"]),
        ("fluidsynth", ["--version"]),
    ]
    
    for tool, args in cli_tools:
        try:
            result = subprocess.run([tool] + args, capture_output=True)
            # ffmpeg returns 0 on success
            if result.returncode == 0:
                print_success(f"{tool} (CLI)")
            else:
                print_error(f"{tool} (CLI) - not working (exit code {result.returncode})")
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


# Strategy mapping
STRATEGY_MAP = {
    "A": "other_only",
    "B": "instrumental", 
    "C": "acoustic_mix",
    "D": "midi_generated",
    "other_only": "other_only",
    "instrumental": "instrumental",
    "acoustic_mix": "acoustic_mix",  
    "midi_generated": "midi_generated",
    "midi": "midi_generated",
}


def run_pipeline(
    input_file: Path, 
    strategy: str = "A",
    pitch_shift: int = 0,
    speed_factor: float = 1.0
):
    """
    Run the full processing pipeline with specified strategy.
    
    Args:
        input_file: Path to input audio file
        strategy: A/B/C/D or full name (other_only, instrumental, acoustic_mix, midi_generated)
        pitch_shift: Semitones to shift (-12 to +12)
        speed_factor: Speed multiplier (0.5 to 2.0)
    """
    
    # Map strategy letter to full name
    strategy = STRATEGY_MAP.get(strategy.upper() if len(strategy) == 1 else strategy, "other_only")
    
    print_header(f"Processing: {input_file.name}")
    print(f"Strategy: {strategy}")
    print(f"Pitch: {pitch_shift:+d} semitones" if pitch_shift != 0 else "Pitch: original")
    print(f"Speed: {speed_factor:.1f}x" if speed_factor != 1.0 else "Speed: original")
    
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
        
        #=============================================================
        # Strategy D: MIDI Generated (no stem separation needed)
        #=============================================================
        if strategy == "midi_generated":
            return run_midi_strategy(job_dir, input_wav, duration, pitch_shift, speed_factor, start_time)
        
        #=============================================================
        # Strategies A/B/C: Stem-based (need Demucs separation)
        #=============================================================
        
        # Step 2: Full stem separation with Demucs
        print_step(2, "Separating stems with Demucs (full 4-stem)...")
        print_info("This will take a few minutes on CPU. Get some coffee ☕")
        
        from services.stem_separator import separate_stems
        
        stems = separate_stems(input_wav, job_dir, "full")
        
        # Show available stems
        print_success("Stems separated!")
        available_stems = {}
        for stem_name in ["vocals", "drums", "bass", "other"]:
            stem_path = job_dir / f"{stem_name}.wav"
            if stem_path.exists():
                available_stems[stem_name] = stem_path
                print(f"      ✓ {stem_name}.wav")
        
        # Step 3: Create backing track based on strategy
        print_step(3, f"Creating backing track with strategy: {strategy}...")
        
        from services.stem_mixer import create_backing_track, BACKING_STRATEGIES
        
        strategy_info = BACKING_STRATEGIES.get(strategy, BACKING_STRATEGIES["other_only"])
        print_info(strategy_info["description"])
        
        backing_wav = job_dir / "backing.wav"
        
        create_backing_track(
            stem_paths=available_stems,
            output_path=backing_wav,
            strategy=strategy,
            semitones=pitch_shift,
            speed_factor=speed_factor,
        )
        
        print_success(f"Backing track created: {backing_wav.name}")
        
        # Save metadata
        metadata = {
            "strategy": strategy,
            "pitch_shift": pitch_shift,
            "speed_factor": speed_factor,
            "duration": duration,
            "stems_available": list(available_stems.keys()),
        }
        with open(job_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Done!
        elapsed = time.time() - start_time
        
        print_header("✅ Processing Complete!")
        print(f"  Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"\n  Output files in: {job_dir}")
        print(f"    - input.wav (original)")
        print(f"    - vocals.wav / drums.wav / bass.wav / other.wav (separated)")
        print(f"    - backing.wav ⬅️ YOUR BACKING TRACK!")
        
        print(f"\n  🎧 Listen to the backing track:")
        print(f"     open {backing_wav}")
        
        print(f"\n  🎧 Compare with 'other' stem directly:")
        print(f"     open {job_dir / 'other.wav'}")
        
        return job_dir
        
    except Exception as e:
        print_error(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_midi_strategy(job_dir: Path, input_wav: Path, duration: float, pitch_shift: int, speed_factor: float, start_time: float):
    """
    Run MIDI-based backing track generation (Strategy D).
    This is the fallback when stem separation doesn't work well.
    """
    
    print_step(2, "Running MIDI strategy (no stem separation)...")
    
    # Detect tempo and chords
    print_step(3, "Detecting tempo...")
    from services.chord_detector import detect_chords, detect_tempo
    
    detected_tempo = detect_tempo(input_wav)
    print_success(f"Detected tempo: {detected_tempo:.0f} BPM")
    
    # Adjust tempo for speed factor
    adjusted_tempo = detected_tempo * speed_factor
    
    # Auto-select style based on tempo
    if adjusted_tempo < 90:
        auto_style = "slow_ballad"
        print_info(f"Slow song → using 'slow_ballad' style")
    elif adjusted_tempo < 120:
        auto_style = "ballad"
        print_info(f"Mid-tempo → using 'ballad' style")
    else:
        auto_style = "continuous_strum"
        print_info(f"Upbeat → using 'continuous_strum' style")
    
    # Detect chords
    print_step(4, "Detecting chords...")
    chords = detect_chords(input_wav)
    
    # Transpose chords if pitch shift requested
    if pitch_shift != 0:
        from services.transpose import transpose_progression
        chords = transpose_progression(chords, pitch_shift)
        print_info(f"Transposed chords by {pitch_shift:+d} semitones")
    
    # Save chords
    chords_file = job_dir / "chords.json"
    with open(chords_file, "w") as f:
        json.dump({
            "tempo": detected_tempo,
            "adjusted_tempo": adjusted_tempo,
            "style": auto_style,
            "pitch_shift": pitch_shift,
            "chords": chords
        }, f, indent=2)
    
    print_success(f"Detected {len(chords)} chord changes")
    
    # Generate MIDI
    print_step(5, "Generating MIDI backing...")
    from services.midi_generator import generate_backing_midi
    
    midi_path = job_dir / "backing.mid"
    # Adjust duration for speed factor
    adjusted_duration = duration / speed_factor if speed_factor != 1.0 else duration
    
    generate_backing_midi(
        chords,
        midi_path,
        style=auto_style,
        tempo=int(adjusted_tempo),
        total_duration=adjusted_duration
    )
    
    print_success(f"MIDI generated: {midi_path.name}")
    
    # Render to audio
    print_step(6, "Rendering MIDI to audio...")
    from services.audio_renderer import render_midi_to_wav, get_soundfont_info
    
    sf_info = get_soundfont_info()
    if not sf_info['available']:
        print_error("No soundfont available! Cannot render audio.")
        print("  MIDI file was created - you can open it in GarageBand.")
        return job_dir
    
    backing_wav = job_dir / "backing.wav"
    render_midi_to_wav(midi_path, backing_wav)
    
    print_success(f"Audio rendered: {backing_wav.name}")
    
    # Save metadata
    metadata = {
        "strategy": "midi_generated",
        "pitch_shift": pitch_shift,
        "speed_factor": speed_factor,
        "tempo": detected_tempo,
        "adjusted_tempo": adjusted_tempo,
        "style": auto_style,
        "duration": duration,
    }
    with open(job_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Done!
    elapsed = time.time() - start_time
    
    print_header("✅ Processing Complete!")
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"\n  Output files in: {job_dir}")
    print(f"    - input.wav (original)")
    print(f"    - chords.json (detected chords)")
    print(f"    - backing.mid (MIDI file)")
    print(f"    - backing.wav ⬅️ YOUR BACKING TRACK!")
    
    print(f"\n  🎧 Listen to the backing track:")
    print(f"     open {backing_wav}")
    
    return job_dir
        
        # Step 3: Detect tempo from the music
        print_step(3, "Detecting tempo...")
        
        from services.chord_detector import detect_chords, detect_tempo
        
        detected_tempo = detect_tempo(chord_input)
        print_success(f"Detected tempo: {detected_tempo:.0f} BPM")
        
        # Choose style based on tempo
        # Slow songs (< 90 BPM) like "Tum Hi Ho" get slow_ballad style
        # Mid-tempo (90-120 BPM) get ballad style
        # Upbeat (> 120 BPM) get continuous_strum
        if detected_tempo < 90:
            auto_style = "slow_ballad"
            print_info(f"Slow song detected → using 'slow_ballad' style (sparse, sustained)")
        elif detected_tempo < 120:
            auto_style = "ballad"
            print_info(f"Mid-tempo song → using 'ballad' style (bass + chord pattern)")
        else:
            auto_style = "continuous_strum"
            print_info(f"Upbeat song → using 'continuous_strum' style")
        
        # Step 4: Chord detection
        print_step(4, "Detecting chords...")
        
        chords = detect_chords(chord_input)
        
        # Save chords
        chords_file = job_dir / "chords.json"
        with open(chords_file, "w") as f:
            json.dump({
                "tempo": detected_tempo,
                "style": auto_style,
                "chords": chords
            }, f, indent=2)
        
        print_success(f"Detected {len(chords)} chord changes")
        
        # Show first few chords
        print("\n  First 10 chords detected:")
        for i, chord in enumerate(chords[:10]):
            print(f"    {chord['time']:6.2f}s - {chord['chord']}")
        if len(chords) > 10:
            print(f"    ... and {len(chords) - 10} more")
        
        # Step 5: Generate MIDI
        print_step(5, "Generating MIDI backing track (humanized)...")
        print_info(f"Using style='{auto_style}' at tempo={detected_tempo:.0f} BPM")
        
        from services.midi_generator import generate_backing_midi
        
        midi_path = job_dir / "backing.mid"
        # Use detected tempo and auto-selected style
        generate_backing_midi(
            chords, 
            midi_path, 
            style=auto_style,             # Auto-selected based on tempo!
            tempo=int(detected_tempo),    # Use actual song tempo!
            total_duration=duration       # Fill to end of song
        )
        
        print_success(f"MIDI generated: {midi_path.name}")
        
        # Step 6: Render to audio
        print_step(6, "Rendering MIDI to audio with FluidSynth...")
        
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
        data = json.load(f)
    
    # Handle both old format (list) and new format (dict with 'chords' key)
    if isinstance(data, dict) and 'chords' in data:
        chords = data['chords']
    else:
        chords = data
    
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
