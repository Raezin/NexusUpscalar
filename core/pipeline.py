import os
import cv2
import time
import threading
import gc
from pathlib import Path

# ── PNG Settings ─────────────────────────────────────────────────────────────
# Use PNG for lossless quality (but JPEG is faster for temp files)
PNG_COMPRESSION = 3  # 0-9, 3 is good balance between quality and size
PNG_PARAMS = [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION]

# ── Batch Size ────────────────────────────────────────────────────────────────
# For Intel Iris Xe with 128MB dedicated + shared memory, use batch size 1
GPU_BATCH_SIZE = 1  # Process one frame at a time for memory safety

# ── RAM Safety ────────────────────────────────────────────────────────────────
RAM_LIMIT_PCT = 70  # Leave headroom for system


def get_ram_usage():
    try:
        import psutil
        return psutil.virtual_memory().percent
    except Exception:
        return 50


class ProcessingPipeline:
    """
    NexusUpscaler - AI-Powered Video Processing Pipeline
    Optimized for Intel Iris Xe with shared memory
    """

    STAGE_ANALYSIS = "analysis"
    STAGE_VFR_CFR = "vfr_cfr"
    STAGE_AUDIO = "audio"
    STAGE_EXTRACTION = "extraction"
    STAGE_UPSCALING = "upscaling"
    STAGE_REBUILD = "rebuild"
    STAGE_ASSEMBLY = "assembly"

    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self.video_info = None

        self.on_status = None
        self.on_progress = None
        self.on_chunk_done = None
        self.on_complete = None
        self.on_error = None
        self.on_stats_update = None
        self.on_stage_update = None
        self.on_extraction_progress = None
        self.on_upscale_progress = None

    # ── Public API ────────────────────────────────────────────────────────────
    def process(self, input_path, output_path, settings=None):
        self.should_stop = False
        self.is_running = True
        thread = threading.Thread(
            target=self._run,
            args=(input_path, output_path, settings),
            daemon=True
        )
        thread.start()
        return thread

    def stop(self):
        self.should_stop = True

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _status(self, msg):
        if self.on_status:
            self.on_status(msg)

    def _stage(self, stage, status, detail=""):
        if self.on_stage_update:
            self.on_stage_update(stage, status, detail)

    def _stats(self, **kwargs):
        if self.on_stats_update:
            self.on_stats_update(kwargs)

    def _format_time(self, seconds):
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}m {s}s"
        else:
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            return f"{h}h {m}m {s}s"

    # ── Main Pipeline ─────────────────────────────────────────────────────────
    def _run(self, input_path, output_path, settings):
        try:
            from core.chunker import VideoChunker
            from core.upscaler import VideoUpscaler

            start_time = time.time()

            settings = settings or {}
            target_res = settings.get("target_res", "1080p")
            enhance = settings.get("enhance", False)
            interpolate = settings.get("interpolate", True)
            target_fps = settings.get("target_fps", 60.0)
            model_path = settings.get("model_path", "model_custom/nexusnet_enhanced_best.pth")
            batch_size = settings.get("batch_size", GPU_BATCH_SIZE)
            ram_limit = settings.get("ram_limit", RAM_LIMIT_PCT)

            input_path = Path(input_path)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            temp_dir = Path("temp") / input_path.stem
            temp_dir.mkdir(parents=True, exist_ok=True)

            chunker = VideoChunker(
                temp_dir=str(temp_dir),
                chunk_duration=60
            )
            
            # Initialize AI upscaler (memory optimized)
            upscaler = VideoUpscaler(
                target_res=target_res,
                enhance=enhance,
                model_path=model_path,
                use_gpu=True  # Use GPU with shared memory
            )

            # ── Stage 1: Analysis ─────────────────────────────────────────
            self._stage(self.STAGE_ANALYSIS, "active", "Reading video metadata...")
            self._status("Analyzing video...")
            t0 = time.time()
            info = chunker.get_video_info(input_path)
            src_fps = info["fps"]
            src_w = info["width"]
            src_h = info["height"]
            duration = info["duration"]
            is_vfr = info["is_vfr"]

            self.video_info = info

            self._stage(
                self.STAGE_ANALYSIS, "done",
                f"{src_w}x{src_h} @ {src_fps:.2f}fps | {duration:.1f}s | {'VFR' if is_vfr else 'CFR'} | {self._format_time(int(time.time()-t0))}"
            )
            self._status(f"Source : {src_w}x{src_h} @ {src_fps:.2f}fps | {duration:.1f}s | {'VFR' if is_vfr else 'CFR'}")

            # ── Stage 2: VFR → CFR (only if needed) ────────────────────────
            process_path = input_path
            if is_vfr:
                self._stage(self.STAGE_VFR_CFR, "active", f"Converting VFR to CFR @ {src_fps:.2f}fps...")
                self._status(f"VFR detected - converting to CFR...")
                t0 = time.time()
                process_path = chunker.convert_vfr_to_cfr(input_path, src_fps, status_callback=self._status)
                elapsed = self._format_time(int(time.time() - t0))
                self._stage(self.STAGE_VFR_CFR, "done", f"CFR @ {src_fps:.2f}fps | {elapsed}")
                self._status(f"✓ VFR → CFR conversion complete")
            else:
                self._stage(self.STAGE_VFR_CFR, "done", "Already CFR - no conversion needed")
                self._status(f"✓ Already CFR - no conversion needed")

            # Check if upscaling is needed
            skip_upscale = not upscaler.needs_upscale(src_w, src_h)
            scale, out_w, out_h = upscaler.calculate_scale(src_w, src_h)

            # Calculate interpolation
            interp_steps, out_fps, interp_method = upscaler.calculate_interpolation_steps(src_fps, target_fps)
            do_interpolate = interpolate and interp_steps > 0

            if not skip_upscale:
                self._status(f"Upscale : {src_w}x{src_h} → {out_w}x{out_h} (AI Model)")
            if do_interpolate:
                self._status(f"Interpolation : {src_fps:.2f} → {out_fps:.0f}fps [{interp_method}]")

            self._status(f"Engine : NexusNet AI Model")
            self._status(f"Format : PNG (Lossless)")
            if enhance:
                self._status(f"Image Enhancement : ON")

            self._stats(
                src_res=f"{src_w}x{src_h}",
                out_res=f"{out_w}x{out_h}",
                src_fps=f"{src_fps:.2f}",
                out_fps=f"{out_fps:.0f}",
                mode="NexusNet AI",
                interp=(f"ON [{interp_method}]" if do_interpolate else "OFF"),
                enhance="ON" if enhance else "OFF",
                elapsed="0s",
                eta="Calculating...",
                speed="—"
            )

            # Load AI Model
            if not upscaler.load_model(status_callback=self._status):
                self._status("❌ Failed to load AI model. Cannot proceed.")
                self._stage(self.STAGE_UPSCALING, "failed", "Model not loaded")
                if self.on_error:
                    self.on_error("AI model failed to load")
                return

            # ── Stage 3: Audio ────────────────────────────────────────────
            audio_path = temp_dir / "audio.aac"
            self._stage(self.STAGE_AUDIO, "active", "Extracting audio...")
            t0 = time.time()
            if info["has_audio"]:
                chunker.extract_audio(input_path, audio_path)
                elapsed = self._format_time(int(time.time() - t0))
                self._stage(self.STAGE_AUDIO, "done", f"Extracted | {elapsed}")
                self._status("Audio extracted ✓")
            else:
                self._stage(self.STAGE_AUDIO, "done", "No audio track")

            chunks = chunker.calculate_chunks(duration)
            total_chunks = len(chunks)
            self._status(f"Split into {total_chunks} chunk(s) · ~{int(src_fps * 60)} frames/chunk")

            sample_src_frame = None
            sample_out_frame = None
            completed_chunks = []
            total_frames_processed = 0

            # ── Process each chunk ────────────────────────────────────────
            for chunk in chunks:
                if self.should_stop:
                    self._status("Stopped by user.")
                    self.is_running = False
                    return

                idx = chunk["index"]
                chunk_output = chunker.get_chunk_output_path(idx)
                frames_dir = chunker.get_chunk_frames_dir(idx)
                out_frames_dir = frames_dir.parent / f"out_frames_{idx:03d}"

                if chunker.chunk_is_done(idx):
                    self._status(f"Chunk {idx+1}/{total_chunks} already done — skipping")
                    completed_chunks.append(chunk_output)
                    if self.on_chunk_done:
                        self.on_chunk_done(idx + 1, total_chunks)
                    continue

                self._status(f"━━ Chunk {idx+1}/{total_chunks} ({chunk['start']:.0f}s → {chunk['end']:.0f}s) ━━")

                # ── Stage 4: Extract ──────────────────────────────────────
                expected = int(chunk["duration"] * src_fps)
                self._stage(self.STAGE_EXTRACTION, "active", f"Chunk {idx+1} — Extracting ~{expected} frames...")
                if self.on_extraction_progress:
                    self.on_extraction_progress(0, expected)

                t0 = time.time()
                frame_paths = chunker.extract_chunk_frames(
                    process_path, chunk, frames_dir, src_fps,
                    status_callback=self._status
                )
                total_frames = len(frame_paths)
                elapsed = self._format_time(int(time.time() - t0))

                if self.on_extraction_progress:
                    self.on_extraction_progress(total_frames, expected)

                self._stage(self.STAGE_EXTRACTION, "done", f"Chunk {idx+1} — {total_frames} frames extracted | {elapsed}")
                self._status(f"  ✓ Extracted {total_frames} frames")

                out_frames_dir.mkdir(parents=True, exist_ok=True)

                # ── Stage 5: AI Upscaling (Memory Optimized) ─────────────────
                self._stage(self.STAGE_UPSCALING, "active", f"Chunk {idx+1} — Upscaling {total_frames} frames...")
                if self.on_upscale_progress:
                    self.on_upscale_progress(0, total_frames, 0)

                upscale_start = time.time()
                out_frame_idx = 0
                prev_out = None
                frames_done = 0

                # ── Process ONE FRAME AT A TIME (memory safe) ─────────────
                for frame_idx in range(total_frames):
                    if self.should_stop:
                        self._status("Stopped.")
                        self.is_running = False
                        return

                    # RAM check
                    while get_ram_usage() > ram_limit:
                        if self.should_stop:
                            break
                        time.sleep(0.1)

                    # Read single frame
                    frame_path = frame_paths[frame_idx]
                    frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    # Capture sample source
                    if sample_src_frame is None:
                        sample_src_frame = frame.copy()

                    # Process single frame with AI model
                    if skip_upscale:
                        processed = [upscaler.enhance_only(frame)]
                    else:
                        processed = upscaler.process_batch([frame], src_w, src_h)

                    # Capture sample output
                    if sample_out_frame is None and processed:
                        sample_out_frame = processed[0].copy()

                    # Write results
                    for out_frame in processed:
                        # Interpolation
                        if do_interpolate and prev_out is not None:
                            motion_mag = upscaler.detect_motion_magnitude(prev_out, out_frame)
                            mid_frames = upscaler.interpolate_frames(
                                prev_out, out_frame,
                                steps=interp_steps,
                                method=interp_method,
                                motion_magnitude=motion_mag,
                                motion_threshold=5.0
                            )
                            for mf in mid_frames:
                                out_path = out_frames_dir / f"frame_{out_frame_idx:08d}.png"
                                cv2.imwrite(str(out_path), mf, PNG_PARAMS)
                                out_frame_idx += 1
                                del mf

                        # Write frame
                        out_path = out_frames_dir / f"frame_{out_frame_idx:08d}.png"
                        cv2.imwrite(str(out_path), out_frame, PNG_PARAMS)
                        out_frame_idx += 1
                        prev_out = out_frame
                        frames_done += 1
                        total_frames_processed += 1

                    # Free memory
                    del frame
                    del processed
                    
                    # Force garbage collection every 10 frames
                    if frame_idx % 10 == 0:
                        gc.collect()

                    # Update progress
                    if self.on_progress:
                        self.on_progress(idx + 1, total_chunks, frames_done, total_frames)

                    # Speed + ETA
                    elapsed_up = time.time() - upscale_start
                    fps_rate = frames_done / elapsed_up if elapsed_up > 0 else 0

                    if self.on_upscale_progress:
                        self.on_upscale_progress(frames_done, total_frames, fps_rate)

                    elapsed_total = time.time() - start_time
                    remaining = max(0, (total_chunks - idx) * total_frames - frames_done)
                    eta = remaining / fps_rate if fps_rate > 0 else 0
                    
                    self._stats(
                        src_res=f"{src_w}x{src_h}",
                        out_res=f"{out_w}x{out_h}",
                        src_fps=f"{src_fps:.2f}",
                        out_fps=f"{out_fps:.0f}",
                        mode="NexusNet AI",
                        interp=(f"ON [{interp_method}]" if do_interpolate else "OFF"),
                        enhance="ON" if enhance else "OFF",
                        elapsed=self._format_time(int(elapsed_total)),
                        eta=self._format_time(int(eta)),
                        speed=f"{fps_rate:.1f} fps"
                    )

                # GC after chunk
                gc.collect()

                upscale_elapsed = self._format_time(int(time.time() - upscale_start))
                self._stage(self.STAGE_UPSCALING, "done", f"Chunk {idx+1} — {out_frame_idx} frames upscaled | {upscale_elapsed}")
                self._status(f"  ✓ Upscaled {out_frame_idx} frames")

                if self.on_upscale_progress:
                    self.on_upscale_progress(total_frames, total_frames, 0)

                chunker.cleanup_chunk(frames_dir)

                # ── Stage 6: Rebuild ──────────────────────────────────────
                self._stage(self.STAGE_REBUILD, "active", f"Chunk {idx+1} — Encoding {out_frame_idx} frames...")
                self._status(f"  Encoding chunk {idx+1}...")
                t0 = time.time()
                chunker.rebuild_chunk_video(out_frames_dir, chunk_output, out_fps, frame_ext="png")
                elapsed = self._format_time(int(time.time() - t0))
                self._stage(self.STAGE_REBUILD, "done", f"Chunk {idx+1} encoded | {elapsed}")
                self._status(f"  ✓ Chunk {idx+1} encoded")

                chunker.cleanup_chunk(out_frames_dir)
                gc.collect()

                completed_chunks.append(chunk_output)

                if self.on_chunk_done:
                    self.on_chunk_done(idx + 1, total_chunks)

                self._status(f"  ✓ Chunk {idx+1}/{total_chunks} complete [{self._format_time(int(time.time()-start_time))} elapsed]")

            # ── Stage 7: Assembly ─────────────────────────────────────────
            self._stage(self.STAGE_ASSEMBLY, "active", f"Merging {total_chunks} chunks...")
            self._status("Assembling final video...")
            t0 = time.time()
            audio_arg = str(audio_path) if info["has_audio"] and audio_path.exists() else None
            chunker.concatenate_chunks(completed_chunks, output_path, audio_arg)
            elapsed = self._format_time(int(time.time() - t0))
            self._stage(self.STAGE_ASSEMBLY, "done", f"Assembled | {elapsed}")

            self._status("Cleaning up temp files...")
            chunker.cleanup_all_temp()

            total_time = self._format_time(int(time.time() - start_time))
            self._status(f"Total time   : {total_time}")
            self._status(f"Output saved : {output_path}")

            self.is_running = False

            if self.on_complete:
                self.on_complete(str(output_path), sample_src_frame, sample_out_frame)

        except Exception as e:
            self.is_running = False
            if self.on_error:
                self.on_error(str(e))
            raise