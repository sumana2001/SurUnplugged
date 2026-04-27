"""
Audio Utilities for SurUnplugged

Helper functions for audio file handling and conversion.
"""
import subprocess
from pathlib import Path


def convert_to_wav(input_path: Path | str, output_path: Path | str) -> Path:
    """
    Convert audio file to WAV format using FFmpeg.
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output WAV file
        
    Returns:
        Path to the output WAV file
        
    Raises:
        RuntimeError: If conversion fails
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # FFmpeg command for high-quality WAV conversion
    # -y: overwrite output
    # -i: input file
    # -acodec pcm_s16le: 16-bit PCM audio
    # -ar 44100: 44.1kHz sample rate
    # -ac 2: stereo
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg conversion failed: {e.stderr}")
    
    return output_path


def get_audio_duration(audio_path: Path | str) -> float:
    """
    Get the duration of an audio file in seconds using FFprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds
        
    Raises:
        RuntimeError: If duration cannot be determined
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Use ffprobe to get duration
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Failed to get audio duration: {e}")


def get_audio_info(audio_path: Path | str) -> dict:
    """
    Get detailed information about an audio file.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Dictionary with audio metadata
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Get duration, sample rate, channels using ffprobe
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels,duration:format=duration,size",
        "-of", "json",
        str(audio_path)
    ]
    
    try:
        import json
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        
        stream = data.get("streams", [{}])[0]
        format_info = data.get("format", {})
        
        return {
            "duration": float(format_info.get("duration", 0)),
            "sample_rate": int(stream.get("sample_rate", 0)),
            "channels": int(stream.get("channels", 0)),
            "file_size": int(format_info.get("size", 0)),
        }
    except Exception as e:
        return {
            "duration": 0,
            "sample_rate": 0,
            "channels": 0,
            "file_size": audio_path.stat().st_size if audio_path.exists() else 0,
            "error": str(e)
        }


def validate_audio_file(audio_path: Path | str, max_duration: float = 600) -> tuple[bool, str]:
    """
    Validate an audio file for processing.
    
    Args:
        audio_path: Path to audio file
        max_duration: Maximum allowed duration in seconds (default: 10 minutes)
        
    Returns:
        Tuple of (is_valid, message)
    """
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        return False, "File not found"
    
    # Check file size (max 100MB)
    max_size = 100 * 1024 * 1024
    if audio_path.stat().st_size > max_size:
        return False, f"File too large (max {max_size // (1024*1024)}MB)"
    
    try:
        duration = get_audio_duration(audio_path)
        if duration > max_duration:
            return False, f"Audio too long (max {max_duration // 60} minutes)"
        if duration < 5:
            return False, "Audio too short (min 5 seconds)"
    except RuntimeError as e:
        return False, f"Invalid audio file: {e}"
    
    return True, "Valid"


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        print(f"Testing with: {test_file}")
        
        info = get_audio_info(test_file)
        print(f"Audio info: {info}")
        
        valid, msg = validate_audio_file(test_file)
        print(f"Validation: {msg}")
    else:
        print("Usage: python audio_utils.py <audio_file>")
