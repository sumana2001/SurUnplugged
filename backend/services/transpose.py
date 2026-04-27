"""
Pitch Transposition Service for SurUnplugged

Handles transposing chord progressions by semitones.
"""

# Note to number mapping
NOTE_MAP = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11
}

# Number to note mapping (using sharps by default)
REVERSE_MAP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Prefer flats for certain keys (for readability)
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb"}
FLAT_MAP = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def parse_chord(chord: str) -> tuple[str, str]:
    """
    Parse a chord into root note and suffix.
    
    Examples:
        "Am7" -> ("A", "m7")
        "C#maj7" -> ("C#", "maj7")
        "Bb" -> ("Bb", "")
        "N" -> ("N", "")  # No chord
    
    Args:
        chord: Chord string
        
    Returns:
        Tuple of (root, suffix)
    """
    if not chord or chord == "N":
        return ("N", "")
    
    chord = chord.strip()
    
    # Handle sharps and flats
    if len(chord) > 1 and chord[1] in "#b":
        root = chord[:2]
        suffix = chord[2:]
    else:
        root = chord[0]
        suffix = chord[1:]
    
    return (root, suffix)


def transpose_chord(chord: str, semitones: int, use_flats: bool = False) -> str:
    """
    Transpose a single chord by the given number of semitones.
    
    Args:
        chord: Chord string (e.g., "Am7", "C#maj7")
        semitones: Number of semitones to shift (-12 to +12)
        use_flats: Whether to use flat notation instead of sharps
        
    Returns:
        Transposed chord string
        
    Examples:
        transpose_chord("Am", 2) -> "Bm"
        transpose_chord("C", -2) -> "Bb" (or "A#" if use_flats=False)
        transpose_chord("G7", 5) -> "C7"
    """
    root, suffix = parse_chord(chord)
    
    # Handle no-chord marker
    if root == "N":
        return "N"
    
    # Get numeric value of root
    root_num = NOTE_MAP.get(root)
    if root_num is None:
        # Unknown root, return as-is
        return chord
    
    # Transpose
    new_num = (root_num + semitones) % 12
    
    # Get new root note
    if use_flats:
        new_root = FLAT_MAP[new_num]
    else:
        new_root = REVERSE_MAP[new_num]
    
    return new_root + suffix


def transpose_progression(
    chords: list[dict], 
    semitones: int,
    use_flats: bool = False
) -> list[dict]:
    """
    Transpose an entire chord progression.
    
    Args:
        chords: List of chord objects with "time", "duration", "chord" keys
        semitones: Number of semitones to shift
        use_flats: Whether to use flat notation
        
    Returns:
        New list of chord objects with transposed chords
        
    Example input:
        [{"time": 0.0, "duration": 2.0, "chord": "C"},
         {"time": 2.0, "duration": 2.0, "chord": "Am"}]
         
    With semitones=2:
        [{"time": 0.0, "duration": 2.0, "chord": "D"},
         {"time": 2.0, "duration": 2.0, "chord": "Bm"}]
    """
    transposed = []
    
    for chord_obj in chords:
        new_obj = chord_obj.copy()
        original_chord = chord_obj.get("chord", "")
        new_obj["chord"] = transpose_chord(original_chord, semitones, use_flats)
        new_obj["original_chord"] = original_chord
        transposed.append(new_obj)
    
    return transposed


def get_key_suggestion(chords: list[dict]) -> str:
    """
    Suggest the likely key of a chord progression.
    
    This is a simple heuristic based on the most common chord
    and common progressions.
    
    Args:
        chords: List of chord objects
        
    Returns:
        Suggested key (e.g., "C major", "A minor")
    """
    if not chords:
        return "Unknown"
    
    # Count chord occurrences
    chord_counts = {}
    for chord_obj in chords:
        chord = chord_obj.get("chord", "N")
        root, suffix = parse_chord(chord)
        if root != "N":
            chord_counts[chord] = chord_counts.get(chord, 0) + 1
    
    if not chord_counts:
        return "Unknown"
    
    # Most common chord is often the tonic
    most_common = max(chord_counts, key=chord_counts.get)
    root, suffix = parse_chord(most_common)
    
    # Determine major or minor
    if "m" in suffix and "maj" not in suffix:
        return f"{root} minor"
    else:
        return f"{root} major"


# For testing
if __name__ == "__main__":
    # Test transpose_chord
    test_cases = [
        ("C", 2, "D"),
        ("Am", 2, "Bm"),
        ("G7", 5, "C7"),
        ("Bb", 1, "B"),
        ("F#m7", -2, "Em7"),
    ]
    
    print("Testing transpose_chord:")
    for chord, semitones, expected in test_cases:
        result = transpose_chord(chord, semitones)
        status = "✓" if result == expected else f"✗ (got {result})"
        print(f"  {chord} + {semitones:+d} = {expected} {status}")
    
    # Test progression
    print("\nTesting transpose_progression:")
    progression = [
        {"time": 0.0, "duration": 2.0, "chord": "C"},
        {"time": 2.0, "duration": 2.0, "chord": "Am"},
        {"time": 4.0, "duration": 2.0, "chord": "F"},
        {"time": 6.0, "duration": 2.0, "chord": "G"},
    ]
    
    transposed = transpose_progression(progression, 2)
    print("  Original: C - Am - F - G")
    print(f"  +2 semitones: {' - '.join(c['chord'] for c in transposed)}")
