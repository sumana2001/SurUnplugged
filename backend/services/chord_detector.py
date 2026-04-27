"""
Chord Detection Service for SurUnplugged

Detects chords from audio using librosa chromagram analysis.
(Fallback implementation - can be enhanced with Chordino/Vamp later)
"""
import json
from pathlib import Path

import numpy as np


# Chord templates for matching
CHORD_TEMPLATES = {
    # Major chords (root, major 3rd, perfect 5th)
    "C": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
    "C#": [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    "D": [0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    "D#": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
    "E": [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    "F": [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    "F#": [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    "G": [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    "G#": [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
    "A": [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    "A#": [0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    "B": [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1],
    
    # Minor chords (root, minor 3rd, perfect 5th)
    "Cm": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    "C#m": [0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    "Dm": [0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0],
    "D#m": [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
    "Em": [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    "Fm": [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0],
    "F#m": [0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    "Gm": [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0],
    "G#m": [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
    "Am": [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    "A#m": [0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    "Bm": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
}


def detect_chords(
    audio_path: Path | str,
    hop_length: int = 4096,
    min_duration: float = 0.5
) -> list[dict]:
    """
    Detect chords from an audio file using chromagram analysis.
    
    Args:
        audio_path: Path to audio file (WAV recommended)
        hop_length: Number of samples between frames (affects time resolution)
        min_duration: Minimum chord duration in seconds (to avoid rapid changes)
        
    Returns:
        List of chord objects:
        [
            {"time": 0.0, "duration": 2.5, "chord": "C"},
            {"time": 2.5, "duration": 2.0, "chord": "Am"},
            ...
        ]
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    try:
        import librosa
    except ImportError:
        raise RuntimeError("librosa not installed. Install with: pip install librosa")
    
    # Load audio
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    
    # Compute chromagram
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    
    # Get time for each frame
    times = librosa.times_like(chroma, sr=sr, hop_length=hop_length)
    
    # Match each frame to best chord
    chord_sequence = []
    
    for i, frame in enumerate(chroma.T):
        # Normalize frame
        frame_norm = frame / (np.linalg.norm(frame) + 1e-8)
        
        # Find best matching chord template
        best_chord = "N"  # No chord
        best_score = 0.5  # Threshold
        
        for chord_name, template in CHORD_TEMPLATES.items():
            template_norm = np.array(template) / np.linalg.norm(template)
            score = np.dot(frame_norm, template_norm)
            
            if score > best_score:
                best_score = score
                best_chord = chord_name
        
        chord_sequence.append({
            "time": float(times[i]),
            "chord": best_chord,
            "confidence": float(best_score),
        })
    
    # Merge consecutive same chords and apply minimum duration
    merged_chords = []
    current_chord = None
    current_start = 0.0
    
    for i, item in enumerate(chord_sequence):
        if current_chord is None:
            current_chord = item["chord"]
            current_start = item["time"]
        elif item["chord"] != current_chord:
            # Check duration
            duration = item["time"] - current_start
            if duration >= min_duration and current_chord != "N":
                merged_chords.append({
                    "time": round(current_start, 3),
                    "duration": round(duration, 3),
                    "chord": current_chord,
                })
            current_chord = item["chord"]
            current_start = item["time"]
    
    # Add last chord
    if current_chord and current_chord != "N":
        final_time = times[-1] if len(times) > 0 else 0
        duration = final_time - current_start
        if duration >= min_duration:
            merged_chords.append({
                "time": round(current_start, 3),
                "duration": round(duration, 3),
                "chord": current_chord,
            })
    
    return merged_chords


def detect_chords_with_vamp(audio_path: Path | str) -> list[dict]:
    """
    Detect chords using Chordino Vamp plugin (higher accuracy).
    
    This requires:
    - vamp Python package
    - Chordino Vamp plugin installed
    
    Falls back to librosa-based detection if Vamp is not available.
    """
    try:
        import vamp
        import librosa
        
        y, sr = librosa.load(str(audio_path), sr=44100, mono=True)
        
        # Run Chordino
        results = vamp.collect(y, sr, "nnls-chroma:chordino")
        
        chords = []
        for item in results.get("list", []):
            timestamp = float(item.get("timestamp", 0))
            duration = float(item.get("duration", 0))
            label = item.get("label", "N")
            
            if label and label != "N":
                chords.append({
                    "time": round(timestamp, 3),
                    "duration": round(duration, 3),
                    "chord": label,
                })
        
        return chords
        
    except ImportError:
        print("Vamp not available, falling back to librosa-based detection")
        return detect_chords(audio_path)
    except Exception as e:
        print(f"Vamp detection failed: {e}, falling back to librosa")
        return detect_chords(audio_path)


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        print(f"Detecting chords in: {test_file}")
        
        try:
            chords = detect_chords(test_file)
            print(f"\nDetected {len(chords)} chords:")
            for chord in chords[:20]:  # Show first 20
                print(f"  {chord['time']:6.2f}s - {chord['chord']:6s} ({chord['duration']:.2f}s)")
            
            if len(chords) > 20:
                print(f"  ... and {len(chords) - 20} more")
                
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python chord_detector.py <audio_file>")
