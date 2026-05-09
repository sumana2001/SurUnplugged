"""
Stem Mixer Service for SurUnplugged

Mixes separated audio stems into custom backing tracks.
Supports 4 strategies for creating guitar/unplugged style backings.
"""
from pathlib import Path
import numpy as np


# Available backing strategies
BACKING_STRATEGIES = {
    "other_only": {
        "name": "Guitar/Other Only",
        "description": "Uses only the 'other' stem (guitars, piano, synths). Best for acoustic songs.",
        "stems": ["other"],
        "volumes": {"other": 1.0},
    },
    "instrumental": {
        "name": "Full Instrumental",
        "description": "Combines drums + bass + other (everything except vocals). Full karaoke feel.",
        "stems": ["drums", "bass", "other"],
        "volumes": {"drums": 0.8, "bass": 0.9, "other": 1.0},
    },
    "acoustic_mix": {
        "name": "Acoustic Mix",
        "description": "Other stem with light bass. Clean unplugged style.",
        "stems": ["other", "bass"],
        "volumes": {"other": 1.0, "bass": 0.4},
    },
    "midi_generated": {
        "name": "MIDI Generated",
        "description": "AI-generated guitar from detected chords. Use when stems don't work well.",
        "stems": [],  # No stems needed, uses MIDI
        "volumes": {},
    },
}


def list_strategies() -> list[dict]:
    """
    List all available backing track strategies.
    
    Returns:
        List of strategy info dictionaries
    """
    return [
        {
            "id": strategy_id,
            "name": info["name"],
            "description": info["description"],
            "requires_stems": len(info["stems"]) > 0,
        }
        for strategy_id, info in BACKING_STRATEGIES.items()
    ]


def mix_stems(
    stem_paths: dict[str, Path],
    output_path: Path | str,
    strategy: str = "other_only",
    custom_volumes: dict[str, float] = None,
    sample_rate: int = 22050
) -> Path:
    """
    Mix audio stems according to a strategy.
    
    Args:
        stem_paths: Dictionary mapping stem names to file paths
                    e.g., {"vocals": Path, "drums": Path, "bass": Path, "other": Path}
        output_path: Path for the output mixed file
        strategy: One of the BACKING_STRATEGIES keys
        custom_volumes: Optional volume overrides (0.0 to 1.0 per stem)
        sample_rate: Sample rate for processing
        
    Returns:
        Path to the mixed output file
        
    Raises:
        ValueError: If strategy is invalid or required stems are missing
    """
    output_path = Path(output_path)
    
    if strategy not in BACKING_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}. Valid: {list(BACKING_STRATEGIES.keys())}")
    
    strategy_info = BACKING_STRATEGIES[strategy]
    required_stems = strategy_info["stems"]
    
    if not required_stems:
        raise ValueError(f"Strategy '{strategy}' doesn't use stems. Use MIDI generation instead.")
    
    # Check required stems exist
    missing = [s for s in required_stems if s not in stem_paths or not Path(stem_paths[s]).exists()]
    if missing:
        raise ValueError(f"Missing required stems for '{strategy}': {missing}")
    
    try:
        import librosa
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(f"Required package not installed: {e}")
    
    # Get volumes (use custom if provided, else defaults)
    volumes = strategy_info["volumes"].copy()
    if custom_volumes:
        volumes.update(custom_volumes)
    
    print(f"  🎚️  Mixing stems with strategy: {strategy_info['name']}")
    
    # Load and mix stems
    mixed = None
    max_length = 0
    
    for stem_name in required_stems:
        stem_path = Path(stem_paths[stem_name])
        volume = volumes.get(stem_name, 1.0)
        
        print(f"      + {stem_name} @ {volume:.0%} volume")
        
        # Load stem
        y, sr = librosa.load(str(stem_path), sr=sample_rate, mono=False)
        
        # Ensure stereo
        if y.ndim == 1:
            y = np.array([y, y])
        
        # Apply volume
        y = y * volume
        
        # Mix
        if mixed is None:
            mixed = y
            max_length = y.shape[1]
        else:
            # Handle length differences
            if y.shape[1] > max_length:
                # Pad existing mix
                pad_length = y.shape[1] - max_length
                mixed = np.pad(mixed, ((0, 0), (0, pad_length)), mode='constant')
                max_length = y.shape[1]
            elif y.shape[1] < max_length:
                # Pad new stem
                pad_length = max_length - y.shape[1]
                y = np.pad(y, ((0, 0), (0, pad_length)), mode='constant')
            
            mixed = mixed + y
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(mixed))
    if max_val > 1.0:
        mixed = mixed / max_val * 0.95
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), mixed.T, sample_rate)
    
    print(f"  ✅ Mixed backing track saved: {output_path.name}")
    
    return output_path


def create_backing_track(
    stem_paths: dict[str, Path],
    output_path: Path | str,
    strategy: str = "other_only",
    semitones: float = 0,
    speed_factor: float = 1.0,
    custom_volumes: dict[str, float] = None,
    sample_rate: int = 22050
) -> Path:
    """
    Create a complete backing track with mixing, pitch shift, and speed control.
    
    This is the main function to use for creating backing tracks from stems.
    
    Args:
        stem_paths: Dictionary mapping stem names to file paths
        output_path: Path for the final output file
        strategy: Backing strategy (other_only, instrumental, acoustic_mix)
        semitones: Pitch shift (-12 to +12)
        speed_factor: Speed multiplier (0.5 to 2.0)
        custom_volumes: Optional volume overrides per stem
        sample_rate: Sample rate for processing
        
    Returns:
        Path to the final backing track
    """
    from services.audio_processor import process_audio
    
    output_path = Path(output_path)
    
    # First, mix the stems
    if semitones == 0 and speed_factor == 1.0:
        # No post-processing needed, mix directly to output
        return mix_stems(
            stem_paths, 
            output_path, 
            strategy, 
            custom_volumes, 
            sample_rate
        )
    else:
        # Mix to temporary file, then process
        temp_path = output_path.parent / f"temp_mix_{output_path.stem}.wav"
        
        mix_stems(stem_paths, temp_path, strategy, custom_volumes, sample_rate)
        
        # Apply pitch/speed processing
        process_audio(temp_path, output_path, semitones, speed_factor, sample_rate)
        
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
        
        return output_path


def get_recommended_strategy(stem_paths: dict[str, Path]) -> str:
    """
    Recommend the best strategy based on available stems.
    
    Args:
        stem_paths: Dictionary of available stem paths
        
    Returns:
        Recommended strategy ID
    """
    available_stems = [s for s, p in stem_paths.items() if Path(p).exists()]
    
    if "other" in available_stems:
        if "bass" in available_stems:
            return "acoustic_mix"  # Best unplugged feel
        return "other_only"
    elif "drums" in available_stems and "bass" in available_stems:
        return "instrumental"
    else:
        return "midi_generated"  # Fallback
