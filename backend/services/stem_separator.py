"""
Stem Separation Service for SurUnplugged

Uses Demucs to separate audio into stems (vocals, drums, bass, other).
"""
from pathlib import Path

import config


def separate_stems(
    input_path: Path | str,
    output_dir: Path | str,
    mode: str = "two-stems"
) -> dict[str, Path]:
    """
    Separate audio into stems using Demucs.
    
    Args:
        input_path: Path to input WAV file
        output_dir: Directory to save output stems
        mode: Separation mode
            - "two-stems": vocals + no_vocals (faster)
            - "full": vocals + drums + bass + other (slower)
    
    Returns:
        Dictionary mapping stem names to paths:
        - two-stems: {"vocals": Path, "no_vocals": Path}
        - full: {"vocals": Path, "drums": Path, "bass": Path, "other": Path}
        
    Raises:
        RuntimeError: If separation fails
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        import demucs.separate
        
        # Build Demucs arguments
        args = [
            "-n", config.DEMUCS_MODEL,
            "-o", str(output_dir),
        ]
        
        if mode == "two-stems":
            args.extend(["--two-stems", "vocals"])
        
        args.append(str(input_path))
        
        # Run Demucs
        demucs.separate.main(args)
        
        # Find output files
        # Demucs outputs to: output_dir/htdemucs/input_filename/
        stem_name = input_path.stem
        demucs_output = output_dir / config.DEMUCS_MODEL / stem_name
        
        if mode == "two-stems":
            # Move files to job directory root for easier access
            vocals_src = demucs_output / "vocals.wav"
            no_vocals_src = demucs_output / "no_vocals.wav"
            
            vocals_dst = output_dir / "vocals.wav"
            no_vocals_dst = output_dir / "no_vocals.wav"
            
            if vocals_src.exists():
                vocals_src.rename(vocals_dst)
            if no_vocals_src.exists():
                no_vocals_src.rename(no_vocals_dst)
            
            return {
                "vocals": vocals_dst,
                "no_vocals": no_vocals_dst,
            }
        else:
            # Full separation
            stems = {}
            for stem in ["vocals", "drums", "bass", "other"]:
                src = demucs_output / f"{stem}.wav"
                dst = output_dir / f"{stem}.wav"
                if src.exists():
                    src.rename(dst)
                    stems[stem] = dst
            
            return stems
            
    except ImportError:
        raise RuntimeError(
            "Demucs not installed. Install with: pip install demucs"
        )
    except Exception as e:
        raise RuntimeError(f"Stem separation failed: {e}")


# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        input_file = Path(sys.argv[1])
        output_dir = Path(sys.argv[2])
        mode = sys.argv[3] if len(sys.argv) > 3 else "two-stems"
        
        print(f"Separating stems from {input_file}...")
        print(f"Mode: {mode}")
        
        try:
            stems = separate_stems(input_file, output_dir, mode)
            print(f"Output stems:")
            for name, path in stems.items():
                print(f"  {name}: {path}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python stem_separator.py <input.wav> <output_dir> [mode]")
        print("Modes: two-stems (default), full")
