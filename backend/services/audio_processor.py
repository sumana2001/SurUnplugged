"""
Audio Processing Service for SurUnplugged

Handles pitch shifting and speed changes for audio files.
Uses librosa for high-quality audio manipulation.
"""
from pathlib import Path
import numpy as np


def pitch_shift(
    input_path: Path | str,
    output_path: Path | str,
    semitones: float,
    sample_rate: int = 22050
) -> Path:
    """
    Shift the pitch of an audio file without changing speed.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output audio file
        semitones: Number of semitones to shift (negative = lower, positive = higher)
                   Range: -12 to +12 (one octave each direction)
        sample_rate: Sample rate for processing
        
    Returns:
        Path to the output file
        
    Example:
        # Lower pitch by 2 semitones (for higher voice range)
        pitch_shift("song.wav", "song_lower.wav", -2)
        
        # Raise pitch by 3 semitones
        pitch_shift("song.wav", "song_higher.wav", 3)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if semitones == 0:
        # No change needed, just copy
        import shutil
        shutil.copy(input_path, output_path)
        return output_path
    
    try:
        import librosa
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(f"Required package not installed: {e}")
    
    print(f"  🎵 Pitch shifting by {semitones:+d} semitones...")
    
    # Load audio
    y, sr = librosa.load(str(input_path), sr=sample_rate, mono=False)
    
    # Handle stereo
    if y.ndim == 2:
        # Process each channel
        y_shifted = np.array([
            librosa.effects.pitch_shift(channel, sr=sr, n_steps=semitones)
            for channel in y
        ])
    else:
        y_shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
    
    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y_shifted.T if y_shifted.ndim == 2 else y_shifted, sr)
    
    return output_path


def change_speed(
    input_path: Path | str,
    output_path: Path | str,
    speed_factor: float,
    sample_rate: int = 22050
) -> Path:
    """
    Change the speed of an audio file without changing pitch.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output audio file
        speed_factor: Speed multiplier
                      0.5 = half speed (slower)
                      1.0 = original speed
                      1.5 = 1.5x speed (faster)
                      Range: 0.5 to 2.0
        sample_rate: Sample rate for processing
        
    Returns:
        Path to the output file
        
    Example:
        # Slow down to 80% speed for practice
        change_speed("song.wav", "song_slow.wav", 0.8)
        
        # Speed up to 120%
        change_speed("song.wav", "song_fast.wav", 1.2)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Clamp speed factor to safe range
    speed_factor = max(0.5, min(2.0, speed_factor))
    
    if speed_factor == 1.0:
        # No change needed, just copy
        import shutil
        shutil.copy(input_path, output_path)
        return output_path
    
    try:
        import librosa
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(f"Required package not installed: {e}")
    
    print(f"  ⏱️  Changing speed to {speed_factor:.1f}x...")
    
    # Load audio
    y, sr = librosa.load(str(input_path), sr=sample_rate, mono=False)
    
    # Handle stereo
    if y.ndim == 2:
        y_stretched = np.array([
            librosa.effects.time_stretch(channel, rate=speed_factor)
            for channel in y
        ])
    else:
        y_stretched = librosa.effects.time_stretch(y, rate=speed_factor)
    
    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y_stretched.T if y_stretched.ndim == 2 else y_stretched, sr)
    
    return output_path


def process_audio(
    input_path: Path | str,
    output_path: Path | str,
    semitones: float = 0,
    speed_factor: float = 1.0,
    sample_rate: int = 22050
) -> Path:
    """
    Apply both pitch shift and speed change to an audio file.
    
    This is more efficient than calling pitch_shift and change_speed separately
    as it only loads/saves the audio once.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output audio file
        semitones: Pitch shift in semitones (-12 to +12)
        speed_factor: Speed multiplier (0.5 to 2.0)
        sample_rate: Sample rate for processing
        
    Returns:
        Path to the output file
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # If no changes needed, just copy
    if semitones == 0 and speed_factor == 1.0:
        import shutil
        shutil.copy(input_path, output_path)
        return output_path
    
    try:
        import librosa
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(f"Required package not installed: {e}")
    
    print(f"  🎛️  Processing audio: pitch={semitones:+d} semitones, speed={speed_factor:.1f}x")
    
    # Load audio
    y, sr = librosa.load(str(input_path), sr=sample_rate, mono=False)
    
    # Process
    def process_channel(channel):
        result = channel
        
        # Apply speed change first (time stretch)
        if speed_factor != 1.0:
            result = librosa.effects.time_stretch(result, rate=speed_factor)
        
        # Then apply pitch shift
        if semitones != 0:
            result = librosa.effects.pitch_shift(result, sr=sr, n_steps=semitones)
        
        return result
    
    if y.ndim == 2:
        y_processed = np.array([process_channel(channel) for channel in y])
    else:
        y_processed = process_channel(y)
    
    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), y_processed.T if y_processed.ndim == 2 else y_processed, sr)
    
    return output_path


def get_audio_info(audio_path: Path | str) -> dict:
    """
    Get information about an audio file.
    
    Returns:
        Dictionary with duration, sample_rate, channels
    """
    audio_path = Path(audio_path)
    
    try:
        import librosa
        
        y, sr = librosa.load(str(audio_path), sr=None, mono=False)
        duration = librosa.get_duration(y=y, sr=sr)
        channels = 1 if y.ndim == 1 else y.shape[0]
        
        return {
            "duration": duration,
            "sample_rate": sr,
            "channels": channels,
            "path": str(audio_path),
        }
    except Exception as e:
        return {"error": str(e)}
