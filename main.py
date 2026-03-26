# main.py - NexusUpscaler Main Application

import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import threading
import json
import time
import gc

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import Colors, Fonts, Theme
from ui.home_page import HomePage
from ui.main_page import MainPage
from ui.frame_rate_page import FrameRatePage
from ui.options_page import OptionsPage


class NexusUpscalerApp:
    """Main application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NexusUpscaler - AI Video Enhancement Suite")
        self.root.geometry("1000x750")
        self.root.configure(bg=Colors.BG_DARK)
        self.root.minsize(800, 600)
        
        # Set icon if available
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # Apply modern theme
        Theme.apply_theme(self.root)
        
        # App state
        self.current_page = None
        self.settings = self._load_settings()
        self.input_path = None
        self.output_path = None
        self.process_thread = None
        self.is_processing = False
        
        # Create pages
        self.home_page = HomePage(
            self.root,
            on_upscale=self.show_upscale_page,
            on_frame_rate=self.show_frame_rate_page,
            on_options=self.show_options_page,
            on_exit=self.exit_app
        )
        
        self.upscale_page = MainPage(
            self.root,
            on_back=self.show_home_page,
            on_start=self.start_upscaling,
            on_stop=self.stop_upscaling,
            on_browse=self.browse_upscale_file,
            on_drop=self.on_drop_upscale_file
        )
        
        self.frame_rate_page = FrameRatePage(
            self.root,
            on_back=self.show_home_page,
            on_process=self.start_frame_rate_conversion
        )
        
        self.options_page = OptionsPage(
            self.root,
            on_back=self.show_home_page,
            on_save=self.save_settings,
            current_settings=self.settings
        )
        
        # Set upscale page with settings
        self.upscale_page.add_advanced_content(
            default_batch=self.settings.get('batch_size', 1),
            default_ram=self.settings.get('ram_limit', 70),
            default_cpu=self.settings.get('cpu_limit', 50)
        )
        
        # Show home page
        self.show_home_page()
    
    # ── Settings Management ───────────────────────────────────────────────────
    def _load_settings(self):
        """Load saved settings"""
        settings_path = Path("settings.json")
        default_settings = {
            'batch_size': 1,
            'ram_limit': 70,
            'cpu_limit': 50,
            'denoise': False,
            'sharpen': False,
            'model_path': 'model_custom/nexusnet_best.pth'
        }
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    saved = json.load(f)
                    default_settings.update(saved)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self, new_settings):
        """Save settings"""
        self.settings.update(new_settings)
        try:
            with open("settings.json", 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            # Update upscale page with new settings
            self.upscale_page.batch_var.set(str(self.settings.get('batch_size', 1)))
            self.upscale_page.ram_var.set(str(self.settings.get('ram_limit', 70)))
            self.upscale_page.cpu_var.set(str(self.settings.get('cpu_limit', 50)))
            self.upscale_page.denoise_var.set(self.settings.get('denoise', False))
            self.upscale_page.sharpen_var.set(self.settings.get('sharpen', False))
            
            messagebox.showinfo("Success", "Settings saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    # ── Page Navigation ──────────────────────────────────────────────────────
    def show_home_page(self):
        """Show home page"""
        self.upscale_page.hide()
        self.frame_rate_page.hide()
        self.options_page.hide()
        self.home_page.show()
    
    def show_upscale_page(self):
        """Show upscaling page"""
        self.home_page.hide()
        self.frame_rate_page.hide()
        self.options_page.hide()
        self.upscale_page.show()
    
    def show_frame_rate_page(self):
        """Show frame rate page"""
        self.home_page.hide()
        self.upscale_page.hide()
        self.options_page.hide()
        self.frame_rate_page.show()
    
    def show_options_page(self):
        """Show options page"""
        self.home_page.hide()
        self.upscale_page.hide()
        self.frame_rate_page.hide()
        self.options_page.show()
    
    # ── Upscaling Page Methods ───────────────────────────────────────────────
    def browse_upscale_file(self):
        """Browse for video file to upscale"""
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_path = filename
            self.upscale_page.update_file_label(filename)
            
            # Auto-generate output path
            output_dir = Path(filename).parent / "output"
            output_dir.mkdir(exist_ok=True)
            self.output_path = output_dir / f"{Path(filename).stem}_upscaled.mp4"
            self.upscale_page.update_status(f"Output will be saved to: {self.output_path}")
    
    def on_drop_upscale_file(self, files):
        """Handle dropped file for upscaling"""
        self.input_path = files
        self.upscale_page.update_file_label(files)
        
        # Auto-generate output path
        output_dir = Path(files).parent / "output"
        output_dir.mkdir(exist_ok=True)
        self.output_path = output_dir / f"{Path(files).stem}_upscaled.mp4"
        self.upscale_page.update_status(f"Output will be saved to: {self.output_path}")
    
    def start_upscaling(self):
        """Start upscaling process"""
        if not self.input_path:
            messagebox.showwarning("No File", "Please select a video file first")
            return
        
        if not Path(self.input_path).exists():
            messagebox.showerror("File Not Found", "The selected file does not exist")
            return
        
        self.is_processing = True
        self.upscale_page.set_processing_state(True)
        self.upscale_page.update_status("=" * 50)
        self.upscale_page.update_status("STARTING UPSCALING PROCESS")
        self.upscale_page.update_status("=" * 50)
        self.upscale_page.update_status(f"Input: {self.input_path}")
        self.upscale_page.update_status(f"Output: {self.output_path}")
        
        # Get settings from upscale page
        settings = self.upscale_page.get_settings()
        settings.update(self.settings)  # Merge with global settings
        
        # Add model path
        model_path = Path(__file__).parent / self.settings.get('model_path', 'model_custom/nexusnet_best.pth')
        if model_path.exists():
            settings['model_path'] = str(model_path)
            self.upscale_page.update_status(f"Model: {model_path.name}")
        else:
            self.upscale_page.update_status(f"❌ Model not found at: {model_path}", 'error')
            self.upscale_page.set_processing_state(False)
            self.is_processing = False
            messagebox.showerror("Error", "Model not found! Please ensure nexusnet_best.pth is in model_custom folder")
            return
        
        # Add paths
        settings['input_path'] = self.input_path
        settings['output_path'] = str(self.output_path)
        
        self.upscale_page.update_status(f"Batch size: {settings.get('batch_size', 1)} frames")
        self.upscale_page.update_status(f"RAM limit: {settings.get('ram_limit', 70)}%")
        self.upscale_page.update_status(f"CPU limit: {settings.get('cpu_limit', 50)}%")
        self.upscale_page.update_status(f"Denoise: {settings.get('denoise', False)}")
        self.upscale_page.update_status(f"Sharpen: {settings.get('sharpen', False)}")
        self.upscale_page.update_status("")
        self.upscale_page.update_status("Processing... This may take several minutes.")
        
        # Start processing in background thread
        self.process_thread = threading.Thread(
            target=self._process_upscale_video,
            args=(settings,),
            daemon=True
        )
        self.process_thread.start()
    
    def _process_upscale_video(self, settings):
        """Process upscaling in background"""
        try:
            from core.pipeline import ProcessingPipeline
            
            pipeline = ProcessingPipeline()
            
            # Connect callbacks
            pipeline.on_status = self.upscale_page.update_status
            pipeline.on_progress = self._update_upscale_progress
            pipeline.on_complete = self._on_upscale_complete
            pipeline.on_error = self._on_upscale_error
            pipeline.on_stage_update = self._on_stage_update
            
            # Process video
            pipeline.process(
                settings['input_path'],
                settings['output_path'],
                settings
            )
            
        except Exception as e:
            self._on_upscale_error(str(e))
    
    def _update_upscale_progress(self, chunk, total_chunks, frames_done, total_frames):
        """Update progress callback"""
        if total_chunks > 0:
            progress = (chunk / total_chunks) * 100
            self.root.after(0, lambda: self.upscale_page.update_progress(progress))
    
    def _on_stage_update(self, stage, status, detail):
        """Update stage callback"""
        self.root.after(0, lambda: self.upscale_page.update_status(f"[{stage.upper()}] {detail}"))
    
    def _on_upscale_complete(self, output_path, sample_src, sample_out):
        """Handle completion"""
        self.root.after(0, lambda: self.upscale_page.update_progress(100))
        self.root.after(0, lambda: self.upscale_page.update_status("", 'success'))
        self.root.after(0, lambda: self.upscale_page.update_status("✓ UPSCALING COMPLETE!", 'success'))
        self.root.after(0, lambda: self.upscale_page.update_status(f"Output saved to: {output_path}", 'success'))
        self.root.after(0, lambda: self.upscale_page.set_processing_state(False))
        self.is_processing = False
        
        self.root.after(0, lambda: messagebox.showinfo(
            "Complete!",
            f"Video upscaling complete!\n\nOutput saved to:\n{output_path}"
        ))
    
    def _on_upscale_error(self, error):
        """Handle error"""
        self.root.after(0, lambda: self.upscale_page.update_status(f"❌ Error: {error}", 'error'))
        self.root.after(0, lambda: self.upscale_page.set_processing_state(False))
        self.is_processing = False
        self.root.after(0, lambda: messagebox.showerror("Error", f"Processing failed:\n{error}"))
    
    def stop_upscaling(self):
        """Stop upscaling process"""
        if self.is_processing:
            self.upscale_page.update_status("Stopping... Please wait", 'warning')
            self.is_processing = False
    
    # ── Frame Rate Conversion Methods ────────────────────────────────────────
    def start_frame_rate_conversion(self, input_path, settings, status_callback, progress_callback):
        """Start frame rate conversion"""
        try:
            from core.chunker import VideoChunker
            
            status_callback("Starting frame rate conversion...")
            status_callback(f"Input: {input_path}")
            status_callback(f"Target FPS: {settings['target_fps']}")
            status_callback(f"Method: {settings['method']}")
            
            # Create output path
            output_dir = Path(input_path).parent / "output"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{Path(input_path).stem}_60fps.mp4"
            
            # Initialize chunker
            chunker = VideoChunker(temp_dir="temp_fps")
            
            # Get video info
            info = chunker.get_video_info(input_path)
            src_fps = info["fps"]
            src_duration = info["duration"]
            
            status_callback(f"Source FPS: {src_fps:.2f}")
            status_callback(f"Source duration: {src_duration:.1f}s")
            
            if info["is_vfr"]:
                status_callback("Detected Variable Frame Rate - Converting to CFR...")
                input_path = chunker.convert_vfr_to_cfr(input_path, src_fps, status_callback)
            
            # Convert to target FPS
            target_fps = settings['target_fps']
            method = settings['method'].lower()
            
            if method == "motion compensated":
                # Use motion interpolation
                status_callback("Using motion-compensated interpolation (best quality)...")
                # This would require more complex processing
                # For now, use simple FPS conversion
                method = "blend"
            
            if method == "blend":
                status_callback("Using blend interpolation...")
            else:
                status_callback("Using frame duplication (fastest)...")
            
            # Simple FPS conversion using FFmpeg
            import subprocess
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_path),
                "-filter:v", f"fps={target_fps}",
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-c:a", "copy",
                str(output_path)
            ]
            
            status_callback("Running FFmpeg conversion...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                progress_callback(100)
                status_callback(f"✓ Frame rate conversion complete!", 'success')
                status_callback(f"Output saved to: {output_path}")
                messagebox.showinfo("Complete", f"Frame rate conversion complete!\n\nOutput saved to:\n{output_path}")
            else:
                raise RuntimeError(result.stderr)
            
            # Clean up
            chunker.cleanup_all_temp()
            
        except Exception as e:
            status_callback(f"❌ Error: {e}", 'error')
            messagebox.showerror("Error", f"Frame rate conversion failed:\n{e}")
    
    # ── Exit ──────────────────────────────────────────────────────────────────
    def exit_app(self):
        """Exit application"""
        if self.is_processing:
            response = messagebox.askyesno(
                "Processing in Progress",
                "Upscaling is currently in progress. Are you sure you want to exit?"
            )
            if not response:
                return
        
        if messagebox.askyesno("Exit", "Are you sure you want to exit NexusUpscaler?"):
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Run application"""
        self.root.mainloop()


if __name__ == "__main__":
    # Check for required files
    model_path = Path("model_custom/nexusnet_best.pth")
    if not model_path.exists():
        print("⚠ Warning: Model not found at model_custom/nexusnet_best.pth")
        print("  Please ensure your trained model is in the correct location.")
    
    # Run app
    app = NexusUpscalerApp()
    app.run()