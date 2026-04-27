"""
Song Processing Task for SurUnplugged

This module contains the main processing pipeline that:
1. Separates stems (if enabled by mode)
2. Detects chords
3. Generates MIDI backing track
4. Renders to WAV using FluidSynth
"""
import json
from pathlib import Path
from typing import Callable

import config


def update_job_status(
    job_dir: Path,
    status: str,
    progress: int,
    current_step: str,
    error: str | None = None
):
    """Update job status in the job.json file."""
    job_file = job_dir / "job.json"
    
    if job_file.exists():
        with open(job_file) as f:
            job = json.load(f)
    else:
        job = {}
    
    job.update({
        "status": status,
        "progress": progress,
        "current_step": current_step,
        "error": error,
    })
    
    with open(job_file, "w") as f:
        json.dump(job, f, indent=2)


def process_song(
    job_id: str,
    mode: str = "balanced",
    progress_callback: Callable[[int, str], None] | None = None
) -> dict:
    """
    Process a song through the full pipeline.
    
    Args:
        job_id: Unique job identifier
        mode: Processing mode (fast, balanced, quality)
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with processing results
        
    Raises:
        FileNotFoundError: If job directory doesn't exist
        RuntimeError: If processing fails
    """
    job_dir = config.JOBS_DIR / job_id
    
    if not job_dir.exists():
        raise FileNotFoundError(f"Job directory not found: {job_dir}")
    
    input_wav = job_dir / "input.wav"
    if not input_wav.exists():
        raise FileNotFoundError(f"Input WAV not found: {input_wav}")
    
    mode_config = config.PROCESSING_MODES.get(mode, config.PROCESSING_MODES["balanced"])
    
    def update_progress(progress: int, step: str):
        update_job_status(job_dir, "processing", progress, step)
        if progress_callback:
            progress_callback(progress, step)
    
    try:
        # Step 1: Stem separation (if enabled)
        update_progress(10, "stem_separation")
        
        if mode_config.get("use_demucs", False):
            from services.stem_separator import separate_stems
            
            demucs_mode = mode_config.get("demucs_mode", "two-stems")
            stems = separate_stems(input_wav, job_dir, demucs_mode)
            chord_input = stems.get("no_vocals", input_wav)
        else:
            # Fast mode: use original audio for chord detection
            chord_input = input_wav
        
        update_progress(40, "chord_detection")
        
        # Step 2: Chord detection
        from services.chord_detector import detect_chords
        
        chords = detect_chords(chord_input)
        
        # Save chords
        chords_file = job_dir / "chords.json"
        with open(chords_file, "w") as f:
            json.dump(chords, f, indent=2)
        
        update_progress(60, "midi_generation")
        
        # Step 3: Generate MIDI
        from services.midi_generator import generate_backing_midi
        
        midi_path = job_dir / "backing.mid"
        generate_backing_midi(chords, midi_path)
        
        update_progress(80, "audio_rendering")
        
        # Step 4: Render MIDI to WAV
        from services.audio_renderer import render_midi_to_wav
        
        backing_wav = job_dir / "backing.wav"
        render_midi_to_wav(midi_path, backing_wav)
        
        # Done!
        update_job_status(job_dir, "completed", 100, "completed")
        
        return {
            "status": "completed",
            "chords": chords,
            "backing_path": str(backing_wav),
        }
        
    except Exception as e:
        error_msg = str(e)
        update_job_status(job_dir, "failed", 0, "error", error_msg)
        raise RuntimeError(f"Processing failed: {error_msg}")


# For testing the pipeline directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_job_id = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) > 2 else "fast"
        
        print(f"Processing job {test_job_id} in {mode} mode...")
        
        def progress_cb(progress, step):
            print(f"  [{progress}%] {step}")
        
        try:
            result = process_song(test_job_id, mode, progress_cb)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python process_song.py <job_id> [mode]")
