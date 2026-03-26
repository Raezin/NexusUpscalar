import os
import cv2
import subprocess
import json
import shutil
from pathlib import Path


class VideoChunker:
    """
    NexusUpscaler - GPU Accelerated Video Chunker
    -----------------------------------------------
    Uses Intel Iris Xe via QSV for all FFmpeg ops:
      - VFR→CFR conversion  : h264_qsv encode
      - Frame extraction    : h264_qsv decode (PNG format for lossless quality)
      - Chunk rebuild       : h264_qsv encode
      - Concatenation       : stream copy (no encode)

    CPU usage during FFmpeg ops: ~15-20%
    GPU usage during FFmpeg ops: ~40-60%
    Speed vs CPU: 4-12x faster
    """

    def __init__(self, temp_dir="temp",
                 chunk_duration=60):
        self.temp_dir       = Path(temp_dir)
        self.chunk_duration = chunk_duration
        self.temp_dir.mkdir(exist_ok=True)
        self._qsv_available = self._check_qsv()

    # ── QSV Detection ─────────────────────────────────────────────────────────
    def _check_qsv(self):
        """
        Verify QSV works on this system.
        Falls back to CPU if QSV unavailable.
        """
        try:
            result = subprocess.run([
                "ffmpeg", "-hide_banner",
                "-hwaccel", "qsv",
                "-f", "lavfi",
                "-i", "testsrc=duration=1:size=128x72:rate=30",
                "-c:v", "h264_qsv",
                "-f", "null", "-"
            ], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def _decode_flags(self):
        """
        Returns FFmpeg decode flags.
        Uses QSV hardware decode if available.
        """
        if self._qsv_available:
            return [
                "-hwaccel",        "qsv",
                "-hwaccel_output_format", "qsv",
                "-c:v",            "h264_qsv",
            ]
        return []

    def _encode_flags(self, crf=18, preset="fast"):
        """
        Returns FFmpeg encode flags.
        Uses QSV hardware encode if available.
        QSV uses -global_quality instead of -crf.
        """
        if self._qsv_available:
            # QSV quality: 1=best, 51=worst
            # Map CRF 18 → QSV quality ~23
            qsv_quality = max(1, min(51, crf + 5))
            return [
                "-c:v",            "h264_qsv",
                "-global_quality", str(qsv_quality),
                "-preset",         "fast",
                "-look_ahead",     "1",
            ]
        return [
            "-c:v",    "libx264",
            "-crf",    str(crf),
            "-preset", preset,
            "-threads", "7",
        ]

    # ── Video Analysis ────────────────────────────────────────────────────────
    def get_video_info(self, video_path):
        """Get complete video metadata using ffprobe"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(video_path)
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed: {result.stderr}"
            )

        data = json.loads(result.stdout)

        video_stream = next(
            (s for s in data["streams"]
             if s["codec_type"] == "video"), None
        )
        audio_stream = next(
            (s for s in data["streams"]
             if s["codec_type"] == "audio"), None
        )

        if video_stream is None:
            raise RuntimeError(
                "No video stream found."
            )

        duration = float(data["format"]["duration"])

        fps_str  = video_stream.get(
            "r_frame_rate", "30/1"
        )
        num, den = fps_str.split("/")
        fps      = float(num) / float(den)

        avg_str      = video_stream.get(
            "avg_frame_rate", fps_str
        )
        avg_num, avg_den = avg_str.split("/")
        avg_fps = (
            float(avg_num) / float(avg_den)
            if float(avg_den) > 0 else fps
        )

        is_vfr = abs(fps - avg_fps) > 1.0

        nb_frames = video_stream.get("nb_frames", None)
        if nb_frames and nb_frames != "N/A":
            total_frames = int(nb_frames)
        else:
            total_frames = int(duration * fps)

        total_frames = max(
            total_frames, int(duration * fps)
        )

        return {
            "duration":    duration,
            "fps":         fps,
            "avg_fps":     avg_fps,
            "is_vfr":      is_vfr,
            "width":       int(video_stream["width"]),
            "height":      int(video_stream["height"]),
            "has_audio":   audio_stream is not None,
            "total_frames": total_frames,
            "expected_frames_per_min": int(fps * 60),
            "qsv_available": self._qsv_available,
        }

    # ── VFR → CFR Conversion ──────────────────────────────────────────────────
    def convert_vfr_to_cfr(self, video_path, fps,
                            status_callback=None):
        """
        Convert VFR to CFR using Intel Xe QSV.
        GPU encode = 4-6x faster than CPU.
        CPU stays at ~15-20% during this operation.
        """
        cfr_path = self.temp_dir / "input_cfr.mp4"

        engine = "Intel Xe QSV" if self._qsv_available \
            else "CPU (7 cores)"

        if status_callback:
            status_callback(
                f"Converting VFR → CFR at "
                f"{fps:.2f}fps ({engine})..."
            )

        if self._qsv_available:
            cmd = [
                "ffmpeg", "-y",
                "-hwaccel",        "qsv",
                "-i",              str(video_path),
                "-vf",             f"fps={fps}",
                "-vsync",          "cfr",
            ] + self._encode_flags(crf=23) + [
                "-c:a", "copy",
                str(cfr_path)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-threads", "7",
                "-i",       str(video_path),
                "-vf",      f"fps={fps}",
                "-vsync",   "cfr",
                "-c:v",     "libx264",
                "-crf",     "23",
                "-preset",  "veryfast",
                "-threads", "7",
                "-c:a",     "copy",
                str(cfr_path)
            ]

        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        if result.returncode != 0:
            # QSV failed — fallback to CPU
            if self._qsv_available:
                if status_callback:
                    status_callback(
                        "QSV failed — falling back to CPU..."
                    )
                self._qsv_available = False
                return self.convert_vfr_to_cfr(
                    video_path, fps, status_callback
                )
            raise RuntimeError(
                f"VFR→CFR failed:\n{result.stderr}"
            )

        if status_callback:
            status_callback(
                f"VFR→CFR complete ✓ ({engine})"
            )

        return cfr_path

    # ── Chunk Calculation ─────────────────────────────────────────────────────
    def calculate_chunks(self, duration):
        chunks = []
        start  = 0.0
        index  = 0
        while start < duration:
            end = min(
                start + self.chunk_duration, duration
            )
            chunks.append({
                "index":    index,
                "start":    start,
                "end":      end,
                "duration": end - start
            })
            start = end
            index += 1
        return chunks

    # ── Audio Extraction ──────────────────────────────────────────────────────
    def extract_audio(self, video_path, output_path):
        """Extract audio — light op, CPU is fine"""
        cmd = [
            "ffmpeg", "-y",
            "-threads", "4",
            "-i",       str(video_path),
            "-vn",
            "-acodec",  "aac",
            "-ab",      "192k",
            str(output_path)
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        return result.returncode == 0

    # ── Frame Extraction (PNG format for lossless quality) ────────────────────
    def extract_chunk_frames(self, video_path, chunk,
                              frames_dir, fps,
                              status_callback=None):
        """
        Extract ALL frames using Intel Xe QSV decode.
        Saves as PNG for lossless quality (better for AI upscaling).
        PNG preserves all details needed for the AI model.
        """
        frames_dir = Path(frames_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)

        expected = int(chunk["duration"] * fps)
        engine   = "Intel Xe QSV" if self._qsv_available \
            else "CPU"

        if status_callback:
            status_callback(
                f"  Extracting ~{expected} frames "
                f"({fps:.2f}fps × "
                f"{chunk['duration']:.1f}s) "
                f"[{engine}]..."
            )

        # Use PNG format for lossless quality
        # PNG compression level 3 (good balance between speed and size)
        if self._qsv_available:
            # QSV hardware decode path with PNG output
            cmd = [
                "ffmpeg", "-y",
                "-hwaccel",   "qsv",
                "-c:v",       "h264_qsv",
                "-ss",        str(chunk["start"]),
                "-i",         str(video_path),
                "-t",         str(chunk["duration"]),
                "-vsync",     "0",
                "-frame_pts", "1",
                "-vf",        "hwdownload,format=nv12",
                "-compression_level", "3",  # PNG compression level
                "-pred",      "mixed",       # Better PNG compression
                str(frames_dir / "frame_%08d.png")
            ]
        else:
            # CPU fallback with PNG output
            cmd = [
                "ffmpeg", "-y",
                "-threads",   "7",
                "-ss",        str(chunk["start"]),
                "-i",         str(video_path),
                "-t",         str(chunk["duration"]),
                "-vsync",     "0",
                "-frame_pts", "1",
                "-compression_level", "3",
                "-pred",      "mixed",
                str(frames_dir / "frame_%08d.png")
            ]

        result = subprocess.run(
            cmd, capture_output=True, text=True
        )

        if result.returncode != 0:
            # QSV decode failed — try CPU fallback
            if self._qsv_available:
                if status_callback:
                    status_callback(
                        "  QSV decode failed — "
                        "trying CPU fallback..."
                    )
                cmd = [
                    "ffmpeg", "-y",
                    "-threads",   "7",
                    "-ss",        str(chunk["start"]),
                    "-i",         str(video_path),
                    "-t",         str(chunk["duration"]),
                    "-vsync",     "0",
                    "-frame_pts", "1",
                    "-compression_level", "3",
                    "-pred",      "mixed",
                    str(frames_dir / "frame_%08d.png")
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Frame extraction failed:\n"
                        f"{result.stderr}"
                    )
            else:
                raise RuntimeError(
                    f"Frame extraction failed:\n"
                    f"{result.stderr}"
                )

        frames = sorted(
            frames_dir.glob("frame_*.png")
        )
        actual = len(frames)

        if status_callback:
            if actual < expected * 0.90:
                status_callback(
                    f"  ⚠ Low frame count: "
                    f"{actual} vs expected {expected}"
                )
            else:
                status_callback(
                    f"  ✓ {actual} frames extracted "
                    f"[{engine}] "
                    f"({actual/chunk['duration']:.1f}fps)"
                )

        return frames

    # ── Video Rebuild ─────────────────────────────────────────────────────────
    def rebuild_chunk_video(self, frames_dir,
                             output_path, fps,
                             frame_ext="png"):
        """
        Rebuild video from PNG frames using Intel Xe QSV.
        GPU encode = 4-6x faster than CPU libx264.
        High quality output with CRF equivalent 18.
        """
        if self._qsv_available:
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(
                    Path(frames_dir) /
                    f"frame_%08d.{frame_ext}"
                ),
            ] + self._encode_flags(crf=18) + [
                "-pix_fmt", "yuv420p",
                "-vsync",   "cfr",
                str(output_path)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-threads",   "7",
                "-framerate", str(fps),
                "-i", str(
                    Path(frames_dir) /
                    f"frame_%08d.{frame_ext}"
                ),
                "-c:v",    "libx264",
                "-crf",    "18",
                "-preset", "fast",
                "-threads", "7",
                "-pix_fmt", "yuv420p",
                "-vsync",   "cfr",
                str(output_path)
            ]

        result = subprocess.run(
            cmd, capture_output=True, text=True
        )

        if result.returncode != 0:
            # QSV encode failed — fallback to CPU
            if self._qsv_available:
                self._qsv_available = False
                return self.rebuild_chunk_video(
                    frames_dir, output_path,
                    fps, frame_ext
                )
            raise RuntimeError(
                f"Chunk rebuild failed:\n{result.stderr}"
            )

    # ── Concatenation ─────────────────────────────────────────────────────────
    def concatenate_chunks(self, chunk_videos,
                           output_path,
                           audio_path=None):
        """
        Merge chunks using stream copy — no re-encode.
        Fast on both CPU and GPU.
        """
        concat_file = self.temp_dir / "concat_list.txt"

        with open(concat_file, "w") as f:
            for cv in chunk_videos:
                safe = str(
                    os.path.abspath(cv)
                ).replace("\\", "/")
                f.write(f"file '{safe}'\n")

        if audio_path and Path(audio_path).exists():
            temp_video = self.temp_dir / \
                "temp_no_audio.mp4"

            result = subprocess.run([
                "ffmpeg", "-y",
                "-f",    "concat",
                "-safe", "0",
                "-i",    str(concat_file),
                "-c",    "copy",
                str(temp_video)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(
                    f"Concat failed:\n{result.stderr}"
                )

            result = subprocess.run([
                "ffmpeg", "-y",
                "-i",    str(temp_video),
                "-i",    str(audio_path),
                "-c:v",  "copy",
                "-c:a",  "aac",
                "-shortest",
                str(output_path)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(
                    f"Audio mux failed:\n{result.stderr}"
                )
        else:
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f",    "concat",
                "-safe", "0",
                "-i",    str(concat_file),
                "-c",    "copy",
                str(output_path)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(
                    f"Concat failed:\n{result.stderr}"
                )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def cleanup_chunk(self, frames_dir):
        if Path(frames_dir).exists():
            shutil.rmtree(frames_dir)

    def cleanup_all_temp(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(exist_ok=True)

    # ── Resume Support ────────────────────────────────────────────────────────
    def chunk_is_done(self, chunk_index):
        path = self.get_chunk_output_path(chunk_index)
        return (path.exists() and
                path.stat().st_size > 1024)

    def get_chunk_output_path(self, chunk_index):
        return (
            self.temp_dir /
            f"chunk_{chunk_index:03d}.mp4"
        )

    def get_chunk_frames_dir(self, chunk_index):
        return (
            self.temp_dir /
            f"frames_chunk_{chunk_index:03d}"
        )