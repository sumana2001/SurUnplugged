"""
API Routes for SurUnplugged
"""
import os
import uuid
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

import config
from utils.audio_utils import convert_to_wav, get_audio_duration

api_bp = Blueprint("api", __name__)

# In-memory job storage (will replace with Redis later)
jobs = {}


@api_bp.route("/upload", methods=["POST"])
def upload_file():
    """
    Upload an MP3 file for processing.
    
    Form data:
        - file: The audio file (MP3, WAV, etc.)
        - mode: Processing mode (fast, balanced, quality) - default: balanced
    
    Returns:
        - job_id: Unique identifier for tracking the job
        - status: Current status (queued)
        - mode: Selected processing mode
    """
    # Check if file is present
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        }), 400
    
    # Get processing mode
    mode = request.form.get("mode", config.DEFAULT_MODE)
    if mode not in config.PROCESSING_MODES:
        return jsonify({
            "error": f"Invalid mode. Allowed: {', '.join(config.PROCESSING_MODES.keys())}"
        }), 400
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Create job directory
    job_dir = config.JOBS_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    original_path = job_dir / f"original{file_ext}"
    file.save(original_path)
    
    # Convert to WAV if not already
    wav_path = job_dir / "input.wav"
    if file_ext != ".wav":
        try:
            convert_to_wav(original_path, wav_path)
        except Exception as e:
            return jsonify({"error": f"Failed to convert file: {str(e)}"}), 500
    else:
        # Just copy if already WAV
        import shutil
        shutil.copy(original_path, wav_path)
    
    # Get audio duration
    try:
        duration = get_audio_duration(wav_path)
    except Exception:
        duration = 0
    
    # Create job record
    mode_info = config.PROCESSING_MODES[mode]
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "mode": mode,
        "progress": 0,
        "current_step": "queued",
        "duration": duration,
        "error": None,
        "created_at": str(Path(original_path).stat().st_mtime),
    }
    
    # Save job metadata
    with open(job_dir / "job.json", "w") as f:
        json.dump(jobs[job_id], f, indent=2)
    
    # TODO: Queue the processing job with Redis Queue
    # For now, we'll process synchronously in a later step
    
    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "mode": mode,
        "estimated_time": mode_info["estimated_time"],
        "message": f"Processing started. Check /api/status/{job_id}"
    }), 202


@api_bp.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """
    Get the status of a processing job.
    
    Returns:
        - job_id: Job identifier
        - status: queued | processing | completed | failed
        - progress: 0-100 percentage
        - current_step: What's currently happening
        - mode: Processing mode used
    """
    # Try to load from memory first
    if job_id in jobs:
        job = jobs[job_id]
    else:
        # Try to load from disk
        job_file = config.JOBS_DIR / job_id / "job.json"
        if not job_file.exists():
            return jsonify({"error": "Job not found"}), 404
        
        with open(job_file) as f:
            job = json.load(f)
            jobs[job_id] = job  # Cache in memory
    
    return jsonify({
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step"],
        "mode": job["mode"],
        "error": job.get("error"),
    })


@api_bp.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    """
    Get the results of a completed job.
    
    Returns:
        - job_id: Job identifier
        - chords: Array of chord objects with time and chord name
        - backing_url: URL to download backing track
        - original_url: URL to download original audio
        - duration: Song duration in seconds
    """
    job_dir = config.JOBS_DIR / job_id
    
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    
    # Load job metadata
    job_file = job_dir / "job.json"
    if not job_file.exists():
        return jsonify({"error": "Job metadata not found"}), 404
    
    with open(job_file) as f:
        job = json.load(f)
    
    if job["status"] != "completed":
        return jsonify({
            "error": f"Job not completed. Current status: {job['status']}",
            "status": job["status"]
        }), 400
    
    # Load chords
    chords_file = job_dir / "chords.json"
    chords = []
    if chords_file.exists():
        with open(chords_file) as f:
            chords = json.load(f)
    
    return jsonify({
        "job_id": job_id,
        "status": "completed",
        "chords": chords,
        "backing_url": f"/api/audio/{job_id}/backing.wav",
        "original_url": f"/api/audio/{job_id}/input.wav",
        "duration": job.get("duration", 0),
    })


@api_bp.route("/audio/<job_id>/<filename>", methods=["GET"])
def get_audio(job_id, filename):
    """Serve audio files for a job."""
    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    audio_path = config.JOBS_DIR / job_id / safe_filename
    
    if not audio_path.exists():
        return jsonify({"error": "Audio file not found"}), 404
    
    return send_file(
        audio_path,
        mimetype="audio/wav",
        as_attachment=False,
        download_name=safe_filename
    )


@api_bp.route("/transpose", methods=["POST"])
def transpose():
    """
    Regenerate backing track with pitch shift.
    
    JSON body:
        - job_id: Existing job ID
        - semitones: Pitch shift (-6 to +6)
    
    Returns:
        - job_id: New job ID for transposed version
        - backing_url: URL to new backing track
        - chords: Transposed chord progression
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    job_id = data.get("job_id")
    semitones = data.get("semitones", 0)
    
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400
    
    # Validate semitones range
    try:
        semitones = int(semitones)
        if not -6 <= semitones <= 6:
            return jsonify({"error": "semitones must be between -6 and 6"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "semitones must be an integer"}), 400
    
    # Check if original job exists
    job_dir = config.JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Original job not found"}), 404
    
    # Load original chords
    chords_file = job_dir / "chords.json"
    if not chords_file.exists():
        return jsonify({"error": "Chords not found for this job"}), 404
    
    with open(chords_file) as f:
        original_chords = json.load(f)
    
    # Transpose chords
    from services.transpose import transpose_progression
    transposed_chords = transpose_progression(original_chords, semitones)
    
    # Create transposed version identifier
    trans_id = f"{job_id}_t{semitones:+d}"
    trans_filename = f"backing_t{semitones:+d}.wav"
    
    # Save transposed chords
    trans_chords_file = job_dir / f"chords_t{semitones:+d}.json"
    with open(trans_chords_file, "w") as f:
        json.dump(transposed_chords, f, indent=2)
    
    # TODO: Generate new backing track with transposed chords
    # For now, return the transposed chords
    
    return jsonify({
        "job_id": trans_id,
        "original_job_id": job_id,
        "semitones": semitones,
        "chords": transposed_chords,
        "backing_url": f"/api/audio/{job_id}/{trans_filename}",
        "message": "Transposed chords generated. Backing track generation coming soon."
    })


@api_bp.route("/modes", methods=["GET"])
def get_modes():
    """Get available processing modes (legacy - use /strategies instead)."""
    return jsonify({
        "modes": {
            name: {
                "description": info["description"],
                "estimated_time": info["estimated_time"],
            }
            for name, info in config.PROCESSING_MODES.items()
        },
        "default": config.DEFAULT_MODE
    })


@api_bp.route("/strategies", methods=["GET"])
def get_strategies():
    """
    Get available backing track strategies.
    
    Returns list of strategies with descriptions:
    - A (other_only): Best for acoustic songs - uses real guitar from stems
    - B (instrumental): Full karaoke - drums + bass + other
    - C (acoustic_mix): Other + light bass - clean unplugged feel
    - D (midi_generated): AI-generated from chords - fallback option
    """
    from services.stem_mixer import list_strategies
    
    strategies = list_strategies()
    
    return jsonify({
        "strategies": strategies,
        "default": "A",
        "recommended": "A",
        "note": "Strategy A (other_only) works best for acoustic/unplugged style songs"
    })


@api_bp.route("/process", methods=["POST"])
def process_track():
    """
    Process a track with specified strategy, pitch, and speed.
    
    This is the main processing endpoint that supports all 4 strategies.
    
    JSON body:
        - job_id: Existing job ID (optional if uploading new file)
        - strategy: A/B/C/D (default: A)
        - pitch_shift: Semitones to shift (-12 to +12, default: 0)
        - speed_factor: Speed multiplier (0.5 to 2.0, default: 1.0)
    
    Or form data with file upload:
        - file: Audio file
        - strategy: A/B/C/D
        - pitch_shift: Semitones
        - speed_factor: Speed multiplier
    """
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        job_id = data.get("job_id")
        strategy = data.get("strategy", "A")
        pitch_shift = data.get("pitch_shift", 0)
        speed_factor = data.get("speed_factor", 1.0)
    else:
        job_id = request.form.get("job_id")
        strategy = request.form.get("strategy", "A")
        pitch_shift = int(request.form.get("pitch_shift", 0))
        speed_factor = float(request.form.get("speed_factor", 1.0))
    
    # Validate strategy
    valid_strategies = ["A", "B", "C", "D", "other_only", "instrumental", "acoustic_mix", "midi_generated"]
    if strategy.upper() not in [s.upper() for s in valid_strategies]:
        return jsonify({"error": f"Invalid strategy. Valid: A, B, C, D"}), 400
    
    # Validate pitch
    try:
        pitch_shift = int(pitch_shift)
        if not -12 <= pitch_shift <= 12:
            return jsonify({"error": "pitch_shift must be between -12 and 12"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "pitch_shift must be an integer"}), 400
    
    # Validate speed
    try:
        speed_factor = float(speed_factor)
        if not 0.5 <= speed_factor <= 2.0:
            return jsonify({"error": "speed_factor must be between 0.5 and 2.0"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "speed_factor must be a number"}), 400
    
    # If job_id provided, reprocess existing stems
    if job_id:
        job_dir = config.JOBS_DIR / job_id
        if not job_dir.exists():
            return jsonify({"error": "Job not found"}), 404
        
        # Check if stems exist (for strategies A/B/C)
        strategy_upper = strategy.upper() if len(strategy) == 1 else strategy
        
        if strategy_upper in ["A", "B", "C", "other_only", "instrumental", "acoustic_mix"]:
            other_wav = job_dir / "other.wav"
            if not other_wav.exists():
                return jsonify({
                    "error": "Stems not found. Run with strategy D or re-upload file.",
                    "suggestion": "Use strategy D (MIDI) or re-run stem separation"
                }), 400
        
        # TODO: Queue reprocessing job
        # For now, return info about what would be done
        
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "strategy": strategy,
            "pitch_shift": pitch_shift,
            "speed_factor": speed_factor,
            "message": "Reprocessing queued. Full implementation coming with frontend."
        }), 202
    
    # No job_id - need file upload
    if "file" not in request.files:
        return jsonify({"error": "Either job_id or file upload required"}), 400
    
    # Handle file upload (similar to /upload endpoint)
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        }), 400
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    job_dir = config.JOBS_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Save file
    original_path = job_dir / f"original{file_ext}"
    file.save(original_path)
    
    # Create job record
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "strategy": strategy,
        "pitch_shift": pitch_shift,
        "speed_factor": speed_factor,
        "progress": 0,
        "current_step": "queued",
        "error": None,
    }
    
    with open(job_dir / "job.json", "w") as f:
        json.dump(jobs[job_id], f, indent=2)
    
    # TODO: Queue processing job
    
    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "strategy": strategy,
        "pitch_shift": pitch_shift,
        "speed_factor": speed_factor,
        "message": f"Processing queued with strategy {strategy}"
    }), 202


@api_bp.route("/adjust/<job_id>", methods=["POST"])
def adjust_audio(job_id):
    """
    Adjust pitch and/or speed for an existing processed job.
    
    This is fast because it uses already-separated stems.
    
    JSON body:
        - pitch_shift: Semitones to shift (-12 to +12)
        - speed_factor: Speed multiplier (0.5 to 2.0)
    
    Returns:
        - backing_url: URL to new adjusted backing track
    """
    job_dir = config.JOBS_DIR / job_id
    if not job_dir.exists():
        return jsonify({"error": "Job not found"}), 404
    
    data = request.get_json() or {}
    pitch_shift = data.get("pitch_shift", 0)
    speed_factor = data.get("speed_factor", 1.0)
    
    # Validate
    try:
        pitch_shift = int(pitch_shift)
        speed_factor = float(speed_factor)
        if not -12 <= pitch_shift <= 12:
            return jsonify({"error": "pitch_shift must be between -12 and 12"}), 400
        if not 0.5 <= speed_factor <= 2.0:
            return jsonify({"error": "speed_factor must be between 0.5 and 2.0"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid pitch_shift or speed_factor"}), 400
    
    # Find source audio
    other_wav = job_dir / "other.wav"
    backing_wav = job_dir / "backing.wav"
    
    if other_wav.exists():
        source = other_wav
    elif backing_wav.exists():
        source = backing_wav
    else:
        return jsonify({"error": "No source audio found"}), 404
    
    # Generate output filename
    output_name = f"backing_p{pitch_shift:+d}_s{speed_factor:.1f}.wav"
    output_path = job_dir / output_name
    
    try:
        from services.audio_processor import process_audio
        process_audio(source, output_path, pitch_shift, speed_factor)
        
        return jsonify({
            "job_id": job_id,
            "pitch_shift": pitch_shift,
            "speed_factor": speed_factor,
            "backing_url": f"/api/audio/{job_id}/{output_name}",
            "message": "Audio adjusted successfully"
        })
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500
