#!/usr/bin/env python3
"""
SurUnplugged - Test Pipeline Script (v2)

Usage:
    python test_pipeline.py path/to/song.mp3 [strategy] [--pitch N] [--speed X]

Strategies:
    A (other_only)   - Uses 'other' stem only. Best for acoustic songs!
    B (instrumental) - Full instrumental (drums + bass + other)
    C (acoustic_mix) - Other stem + light bass
    D (midi)         - AI-generated guitar from chords (fallback)
"""

import sys
import shutil
from pathlib import Path
import time
import json

sys.path.insert(0, str(Path(__file__).parent))

import config
from utils.audio_utils import convert_to_wav, get_audio_duration, get_audio_info


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(step_num, text):
    print(f"[Step {step_num}] {text}")


def print_success(text):
    print(f"  OK: {text}")


def print_error(text):
    print(f"  ERROR: {text}")


def print_info(text):
    print(f"  INFO: {text}")


def test_dependencies():
    print_header("Checking Dependencies")
    missing = []
    pkgs = [("flask", "Flask"), ("librosa", "librosa"), ("numpy", "numpy"),
            ("pretty_midi", "pretty-midi"), ("pydub", "pydub"), ("soundfile", "soundfile")]
    for import_name, pip_name in pkgs:
        try:
            __import__(import_name)
            print_success(pip_name)
        except ImportError:
            print_error(f"{pip_name} - NOT INSTALLED")
            missing.append(pip_name)
    try:
        import demucs
        print_success("demucs")
    except ImportError:
        print_error("demucs - NOT INSTALLED")
        missing.append("demucs")
    import subprocess
    for tool, args in [("ffmpeg", ["-version"]), ("fluidsynth", ["--version"])]:
        try:
            result = subprocess.run([tool] + args, capture_output=True)
            if result.returncode == 0:
                print_success(f"{tool} (CLI)")
            else:
                missing.append(tool)
        except FileNotFoundError:
            print_error(f"{tool} - NOT FOUND")
            missing.append(tool)
    if missing:
        print(f"\nMissing: {', '.join(missing)}")
        return False
    print("\nAll dependencies OK!")
    return True


def test_soundfont():
    print_header("Checking Soundfont")
    from services.audio_renderer import get_soundfont_info
    info = get_soundfont_info()
    if info["available"]:
        print_success("Soundfont available!")
        return True
    print_error("No soundfont (needed for MIDI strategy D)")
    return False


STRATEGY_MAP = {
    "A": "other_only", "B": "instrumental", "C": "acoustic_mix", "D": "midi_generated",
    "other_only": "other_only", "instrumental": "instrumental", "acoustic_mix": "acoustic_mix",
    "midi_generated": "midi_generated", "midi": "midi_generated",
}


def run_pipeline(input_file, strategy="A", pitch_shift=0, speed_factor=1.0):
    strategy = STRATEGY_MAP.get(strategy.upper() if len(strategy) == 1 else strategy, "other_only")
    print_header(f"Processing: {input_file.name}")
    print(f"Strategy: {strategy}")
    if pitch_shift != 0:
        print(f"Pitch: {pitch_shift:+d} semitones")
    if speed_factor != 1.0:
        print(f"Speed: {speed_factor:.1f}x")

    job_dir = config.JOBS_DIR / f"test_{int(time.time())}"
    job_dir.mkdir(parents=True, exist_ok=True)
    print(f"Job directory: {job_dir}")
    start_time = time.time()

    try:
        print_step(1, "Converting to WAV...")
        input_wav = job_dir / "input.wav"
        if input_file.suffix.lower() == ".wav":
            shutil.copy(input_file, input_wav)
        else:
            convert_to_wav(input_file, input_wav)
        duration = get_audio_duration(input_wav)
        print_success(f"Converted! Duration: {duration:.1f}s")

        if strategy == "midi_generated":
            return run_midi_strategy(job_dir, input_wav, duration, pitch_shift, speed_factor, start_time)

        print_step(2, "Separating stems with Demucs...")
        print_info("This takes a few minutes on CPU")
        from services.stem_separator import separate_stems
        separate_stems(input_wav, job_dir, "full")

        print_success("Stems separated!")
        available_stems = {}
        for stem_name in ["vocals", "drums", "bass", "other"]:
            stem_path = job_dir / f"{stem_name}.wav"
            if stem_path.exists():
                available_stems[stem_name] = stem_path
                print(f"      - {stem_name}.wav")

        print_step(3, "Creating backing track...")
        from services.stem_mixer import create_backing_track, BACKING_STRATEGIES
        desc = BACKING_STRATEGIES.get(strategy, {}).get("description", "")
        if desc:
            print_info(desc)

        backing_wav = job_dir / "backing.wav"
        create_backing_track(
            stem_paths=available_stems,
            output_path=backing_wav,
            strategy=strategy,
            semitones=pitch_shift,
            speed_factor=speed_factor,
        )
        print_success("Backing track created!")

        with open(job_dir / "metadata.json", "w") as f:
            json.dump({"strategy": strategy, "pitch_shift": pitch_shift, "speed_factor": speed_factor}, f)

        elapsed = time.time() - start_time
        print_header("Processing Complete!")
        print(f"  Time: {elapsed:.1f}s")
        print(f"\n  Listen: open {backing_wav}")
        return job_dir

    except Exception as e:
        print_error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_midi_strategy(job_dir, input_wav, duration, pitch_shift, speed_factor, start_time):
    print_step(2, "Running MIDI strategy...")
    from services.chord_detector import detect_chords, detect_tempo

    print_step(3, "Detecting tempo...")
    detected_tempo = detect_tempo(input_wav)
    print_success(f"Tempo: {detected_tempo:.0f} BPM")

    adjusted_tempo = detected_tempo * speed_factor
    if adjusted_tempo < 90:
        auto_style = "slow_ballad"
    elif adjusted_tempo < 120:
        auto_style = "ballad"
    else:
        auto_style = "continuous_strum"
    print_info(f"Style: {auto_style}")

    print_step(4, "Detecting chords...")
    chords = detect_chords(input_wav)
    if pitch_shift != 0:
        from services.transpose import transpose_progression
        chords = transpose_progression(chords, pitch_shift)
    with open(job_dir / "chords.json", "w") as f:
        json.dump({"tempo": detected_tempo, "style": auto_style, "chords": chords}, f)
    print_success(f"Detected {len(chords)} chords")

    print_step(5, "Generating MIDI...")
    from services.midi_generator import generate_backing_midi
    midi_path = job_dir / "backing.mid"
    td = duration / speed_factor if speed_factor != 1.0 else duration
    generate_backing_midi(chords, midi_path, style=auto_style, tempo=int(adjusted_tempo), total_duration=td)

    print_step(6, "Rendering audio...")
    from services.audio_renderer import render_midi_to_wav, get_soundfont_info
    if not get_soundfont_info()["available"]:
        print_error("No soundfont!")
        return job_dir

    backing_wav = job_dir / "backing.wav"
    render_midi_to_wav(midi_path, backing_wav)

    elapsed = time.time() - start_time
    print_header("Done!")
    print(f"  Listen: open {backing_wav}")
    return job_dir


def main():
    print("\n  SurUnplugged - Backing Track Generator\n")

    if not test_dependencies():
        sys.exit(1)
    test_soundfont()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?")
    parser.add_argument("strategy", nargs="?", default="A")
    parser.add_argument("--pitch", type=int, default=0)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    if not args.input:
        print("Usage: python test_pipeline.py <song.mp3> [A/B/C/D] [--pitch N] [--speed X]")
        print("\nStrategies:")
        print("  A - other stem (guitars) - BEST FOR ACOUSTIC!")
        print("  B - Full instrumental")
        print("  C - Other + bass")
        print("  D - MIDI generated (fallback)")
        print("\nExample: python test_pipeline.py ~/Music/kabira.mp3 A --pitch -2")
        sys.exit(0)

    input_file = Path(args.input).expanduser()
    if not input_file.exists():
        print_error(f"Not found: {input_file}")
        sys.exit(1)

    run_pipeline(input_file, args.strategy, args.pitch, args.speed)


if __name__ == "__main__":
    main()
