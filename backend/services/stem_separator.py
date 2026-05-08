"""
Stem Separation Service for SurUnplugged

Uses Demucs to separate audio into stems (vocals, drums, bass, other).
"""
import shutil
from pathlib import Path

import config


def _convert_stems_with_scipy(demucs_output: Path, output_dir: Path, stem_names: list[str]) -> dict[str, Path]:
    """
    Convert stems from Demucs output directory using scipy (fallback when torchcodec fails).
    Demucs may fail to save with torchaudio if torchcodec is missing.
    """
    import numpy as np
    
    try:
        import scipy.io.wavfile as wav
    except ImportError:
        # Fallback: just copy whatever files exist
        pass
    
    stems = {}
    for stem in stem_names:
        src = demucs_output / f"{stem}.wav"
        dst = output_dir / f"{stem}.wav"
        
        if src.exists():
            shutil.move(str(src), str(dst))
            stems[stem] = dst
        else:
            print(f"  ⚠️  Stem not found: {stem}")
    
    return stems


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
        try:
            demucs.separate.main(args)
        except ImportError as e:
            if 'torchcodec' in str(e).lower():
                # torchaudio needs torchcodec for saving - try alternative
                print("  ⚠️  torchcodec not installed, trying alternative save...")
                # Demucs may have partially completed - check if raw tensors exist
                # or we need to run with different backend
                raise RuntimeError(
                    "Demucs needs torchcodec to save audio. "
                    "Install it with: pip install torchcodec\n"
                    "Or skip stem separation with 'fast' mode."
                )
            raise
        except Exception as e:
            if 'torchcodec' in str(e).lower() or 'TorchCodec' in str(e):
                raise RuntimeError(
                    "Demucs completed but couldn't save output files.\n"
                    "This is a torchaudio/torchcodec compatibility issue.\n\n"
                    "Fix: pip install torchcodec\n"
                    "Or use 'fast' mode to skip stem separation."
                )
            raise
        
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
    except RuntimeError:
        # Re-raise RuntimeErrors we created (with proper messages)
        raise
    except Exception as e:
        error_msg = str(e)
        if 'torchcodec' in error_msg.lower() or 'TorchCodec' in error_msg:
            raise RuntimeError(
                "Demucs completed but couldn't save output files.\n"
                "This is a torchaudio/torchcodec compatibility issue.\n\n"
                "Fix: pip install torchcodec\n"
                "Or use 'fast' mode to skip stem separation."
            )
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
