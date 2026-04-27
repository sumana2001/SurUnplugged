"""
Audio Rendering Service for SurUnplugged

Converts MIDI to WAV audio using FluidSynth.
"""
import subprocess
from pathlib import Path

import config


def render_midi_to_wav(
    midi_path: Path | str,
    output_path: Path | str,
    soundfont_path: Path | str | None = None,
    sample_rate: int = 44100,
    gain: float = 1.0
) -> Path:
    """
    Render a MIDI file to WAV using FluidSynth.
    
    Args:
        midi_path: Path to input MIDI file
        output_path: Path for output WAV file
        soundfont_path: Path to .sf2 soundfont file (uses default if None)
        sample_rate: Output sample rate (default 44100)
        gain: Output gain multiplier (default 1.0)
        
    Returns:
        Path to rendered WAV file
        
    Raises:
        FileNotFoundError: If MIDI or soundfont not found
        RuntimeError: If FluidSynth fails
    """
    midi_path = Path(midi_path)
    output_path = Path(output_path)
    
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")
    
    # Find soundfont
    if soundfont_path:
        soundfont_path = Path(soundfont_path)
    else:
        soundfont_path = config.SOUNDFONT_PATH
    
    # If configured soundfont doesn't exist, try to find a system soundfont
    if not soundfont_path.exists():
        soundfont_path = _find_system_soundfont()
    
    if not soundfont_path or not soundfont_path.exists():
        raise FileNotFoundError(
            f"No soundfont found. Please download a .sf2 file and place it at: "
            f"{config.SOUNDFONT_PATH}"
        )
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build FluidSynth command
    # -ni: no interactive mode
    # -g: gain
    # -r: sample rate
    # -F: output file
    cmd = [
        "fluidsynth",
        "-ni",
        "-g", str(gain),
        "-r", str(sample_rate),
        "-F", str(output_path),
        str(soundfont_path),
        str(midi_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FluidSynth rendering failed: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError(
            "FluidSynth not found. Install with: brew install fluidsynth"
        )
    
    if not output_path.exists():
        raise RuntimeError("FluidSynth did not produce output file")
    
    return output_path


def _find_system_soundfont() -> Path | None:
    """
    Try to find a soundfont on the system.
    
    Common locations on macOS/Linux.
    """
    common_paths = [
        # macOS Homebrew
        Path("/opt/homebrew/share/soundfonts/default.sf2"),
        Path("/usr/local/share/soundfonts/default.sf2"),
        
        # Linux common locations
        Path("/usr/share/soundfonts/FluidR3_GM.sf2"),
        Path("/usr/share/soundfonts/default.sf2"),
        Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        
        # User local
        Path.home() / ".local/share/soundfonts/default.sf2",
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    return None


def get_soundfont_info() -> dict:
    """
    Get information about available soundfonts.
    
    Returns:
        Dictionary with soundfont status and paths
    """
    configured = config.SOUNDFONT_PATH
    system = _find_system_soundfont()
    
    return {
        "configured_path": str(configured),
        "configured_exists": configured.exists() if configured else False,
        "system_path": str(system) if system else None,
        "system_exists": system.exists() if system else False,
        "available": (configured and configured.exists()) or (system and system.exists()),
    }


# For testing
if __name__ == "__main__":
    import sys
    
    print("Soundfont status:")
    info = get_soundfont_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    if len(sys.argv) > 2:
        midi_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2])
        
        print(f"\nRendering {midi_file} to {output_file}...")
        
        try:
            result = render_midi_to_wav(midi_file, output_file)
            print(f"Success! Output: {result}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nUsage: python audio_renderer.py <input.mid> <output.wav>")
