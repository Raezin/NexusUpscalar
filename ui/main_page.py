# ui/main_page.py - Redesigned with 2-Column Layout and Enhanced Features

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from .styles import Colors, Fonts
from .widgets import DragDropArea, StatusText, CollapsibleFrame


class MainPage:
    """Main upscaling interface with 2-column layout"""
    
    def __init__(self, parent, on_back, on_start, on_stop, on_browse, on_drop):
        self.parent = parent
        self.on_back = on_back
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_browse = on_browse
        self.on_drop = on_drop
        
        self.frame = None
        self.drop_area = None
        self.file_label = None
        self.output_path_var = None
        self.enhance_var = None
        self.batch_var = None
        self.ram_var = None
        self.cpu_var = None
        self.progress_bar = None
        self.status_text = None
        self.start_btn = None
        self.stop_btn = None
        self.adv_frame = None
        self.adv_content = None
        self._adv_content_added = False
        self.input_path = None
        self.output_path = None
        self.fps_info_label = None
        self.vfr_info_label = None
        
        self.create_page()
    
    def create_page(self):
        """Create main page layout with 2 columns"""
        self.frame = tk.Frame(self.parent, bg=Colors.BG_DARK)
        
        # Main container with scrollbar
        canvas = tk.Canvas(self.frame, bg=Colors.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Colors.BG_DARK)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Main container
        main_container = tk.Frame(scrollable_frame, bg=Colors.BG_DARK)
        main_container.pack(expand=True, fill='both', padx=40, pady=30)
        
        # Header
        header = tk.Frame(main_container, bg=Colors.BG_DARK)
        header.pack(fill='x', pady=(0, 20))
        
        back_btn = tk.Button(
            header,
            text="← Back",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=15,
            pady=5,
            command=self.on_back,
            relief='flat',
            cursor='hand2'
        )
        back_btn.pack(side='left')
        
        title = tk.Label(
            header,
            text="AI Video Upscaler",
            font=Fonts.HEADING,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_PRIMARY
        )
        title.pack(side='left', padx=20)
        
        # ── 2-Column Layout ─────────────────────────────────────────────────
        columns_container = tk.Frame(main_container, bg=Colors.BG_DARK)
        columns_container.pack(expand=True, fill='both')
        
        # Left Column - Video Selection
        left_column = tk.Frame(columns_container, bg=Colors.BG_DARK)
        left_column.pack(side='left', expand=True, fill='both', padx=(0, 10))
        
        # Right Column - Settings
        right_column = tk.Frame(columns_container, bg=Colors.BG_DARK)
        right_column.pack(side='left', expand=True, fill='both', padx=(10, 0))
        
        # ── LEFT COLUMN: Video Selection ─────────────────────────────────────
        input_card = tk.Frame(
            left_column,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        input_card.pack(fill='both', expand=True, pady=(0, 10))
        
        # Card header
        input_header = tk.Frame(input_card, bg=Colors.BG_MEDIUM)
        input_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            input_header,
            text="📁 Input Video",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Drag & drop area
        self.drop_area = DragDropArea(
            input_card,
            on_drop_callback=self.on_drop
        )
        self.drop_area.pack(fill='x', padx=20, pady=10)
        
        # Browse button
        browse_btn = tk.Button(
            input_card,
            text="Browse Video",
            font=Fonts.NORMAL,
            bg=Colors.ACCENT_PRIMARY,
            fg=Colors.TEXT_PRIMARY,
            padx=20,
            pady=8,
            command=self.on_browse,
            relief='flat',
            cursor='hand2'
        )
        browse_btn.pack(pady=5)
        
        # Selected file label
        self.file_label = tk.Label(
            input_card,
            text="No file selected",
            bg=Colors.BG_MEDIUM,
            fg=Colors.SUCCESS,
            font=Fonts.SMALL,
            wraplength=300
        )
        self.file_label.pack(pady=10, padx=20)
        
        # ── Output Location ─────────────────────────────────────────────────
        output_card = tk.Frame(
            left_column,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        output_card.pack(fill='both', expand=True, pady=(10, 0))
        
        output_header = tk.Frame(output_card, bg=Colors.BG_MEDIUM)
        output_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            output_header,
            text="💾 Output Location",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Output path entry
        output_entry_frame = tk.Frame(output_card, bg=Colors.BG_MEDIUM)
        output_entry_frame.pack(fill='x', padx=20, pady=10)
        
        self.output_path_var = tk.StringVar(value="")
        output_entry = tk.Entry(
            output_entry_frame,
            textvariable=self.output_path_var,
            bg=Colors.BG_LIGHT,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.NORMAL,
            insertbackground=Colors.TEXT_PRIMARY
        )
        output_entry.pack(side='left', expand=True, fill='x', padx=(0, 10))
        
        output_browse_btn = tk.Button(
            output_entry_frame,
            text="Browse",
            font=Fonts.SMALL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            command=self._browse_output,
            relief='flat',
            cursor='hand2'
        )
        output_browse_btn.pack(side='right')
        
        # ── RIGHT COLUMN: Settings ──────────────────────────────────────────
        # Frame Rate Card
        fps_card = tk.Frame(
            right_column,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        fps_card.pack(fill='both', expand=True, pady=(0, 10))
        
        fps_header = tk.Frame(fps_card, bg=Colors.BG_MEDIUM)
        fps_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            fps_header,
            text="🎬 Frame Rate",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Frame rate info display
        info_frame = tk.Frame(fps_card, bg=Colors.BG_MEDIUM)
        info_frame.pack(fill='x', padx=20, pady=10)
        
        # FPS value display
        fps_value_frame = tk.Frame(info_frame, bg=Colors.BG_MEDIUM)
        fps_value_frame.pack(fill='x', pady=5)
        
        tk.Label(
            fps_value_frame,
            text="Detected FPS:",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL,
            width=15,
            anchor='w'
        ).pack(side='left')
        
        self.fps_info_label = tk.Label(
            fps_value_frame,
            text="--",
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SUCCESS,
            font=Fonts.NORMAL,
            anchor='w'
        )
        self.fps_info_label.pack(side='left', padx=10)
        
        # VFR/CFR display
        vfr_value_frame = tk.Frame(info_frame, bg=Colors.BG_MEDIUM)
        vfr_value_frame.pack(fill='x', pady=5)
        
        tk.Label(
            vfr_value_frame,
            text="Frame Rate Type:",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL,
            width=15,
            anchor='w'
        ).pack(side='left')
        
        self.vfr_info_label = tk.Label(
            vfr_value_frame,
            text="--",
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_WARNING,
            font=Fonts.NORMAL,
            anchor='w'
        )
        self.vfr_info_label.pack(side='left', padx=10)
        
        # VFR to CFR note
        vfr_note = tk.Label(
            fps_card,
            text="✓ Will convert VFR to CFR (Constant Frame Rate)\n  Preserves original FPS (30fps or 60fps only)",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify='center'
        )
        vfr_note.pack(pady=10, padx=20)
        
        # ── Image Enhancement Card ──────────────────────────────────────────
        enhance_card = tk.Frame(
            right_column,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        enhance_card.pack(fill='both', expand=True, pady=(0, 10))
        
        enhance_header = tk.Frame(enhance_card, bg=Colors.BG_MEDIUM)
        enhance_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            enhance_header,
            text="🎨 Image Enhancement",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        self.enhance_var = tk.BooleanVar(value=False)
        enhance_check = tk.Checkbutton(
            enhance_card,
            text="Enable Image Enhancement",
            variable=self.enhance_var,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            selectcolor=Colors.BG_MEDIUM,
            activebackground=Colors.BG_MEDIUM,
            font=Fonts.NORMAL
        )
        enhance_check.pack(pady=15)
        
        # Enhancement description (optional, can be hidden if you want)
        enhance_desc = tk.Label(
            enhance_card,
            text="• Brightness: -5%\n• Sharpness: +30%\n• Contrast: +15%\n• Saturation: +5-15%",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify='left'
        )
        enhance_desc.pack(pady=10, padx=20)
        
        # ── Progress Section ────────────────────────────────────────────────
        progress_card = tk.Frame(
            main_container,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        progress_card.pack(fill='x', pady=(20, 0))
        
        progress_header = tk.Frame(progress_card, bg=Colors.BG_MEDIUM)
        progress_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            progress_header,
            text="📊 Progress Details",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_card,
            mode='determinate',
            length=400,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(pady=10, padx=20)
        
        # Detailed status text
        self.status_text = StatusText(progress_card)
        self.status_text.pack(fill='x', padx=20, pady=(0, 15))
        
        # ── Advanced Settings (Collapsible) ─────────────────────────────────
        self.adv_frame = CollapsibleFrame(
            main_container,
            title="🔧 Advanced Settings",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            font=Fonts.SECTION_HEADER,
            padx=20,
            pady=15
        )
        self.adv_frame.pack(fill='x', pady=(10, 0))
        
        # ── Action Buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(main_container, bg=Colors.BG_DARK)
        btn_frame.pack(pady=20)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="🚀 START UPSCALING",
            font=Fonts.BUTTON,
            bg=Colors.ACCENT_SUCCESS,
            fg=Colors.TEXT_PRIMARY,
            padx=40,
            pady=12,
            command=self.on_start,
            relief='flat',
            cursor='hand2'
        )
        self.start_btn.pack(side='left', padx=10)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ STOP",
            font=Fonts.BUTTON,
            bg=Colors.ACCENT_DANGER,
            fg=Colors.TEXT_PRIMARY,
            padx=30,
            pady=12,
            command=self.on_stop,
            state='disabled',
            relief='flat',
            cursor='hand2'
        )
        self.stop_btn.pack(side='left', padx=10)
        
        back_btn_main = tk.Button(
            btn_frame,
            text="← Back to Home",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=20,
            pady=12,
            command=self.on_back,
            relief='flat',
            cursor='hand2'
        )
        back_btn_main.pack(side='left', padx=10)
    
    def _browse_output(self):
        """Browse for output location"""
        filename = filedialog.asksaveasfilename(
            title="Save Output Video",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        if filename:
            self.output_path_var.set(filename)
            self.output_path = filename
    
    def update_video_info(self, fps, is_vfr):
        """Update video information display"""
        if fps:
            self.fps_info_label.config(text=f"{fps:.2f} fps")
        
        if is_vfr:
            self.vfr_info_label.config(text="Variable Frame Rate (VFR)", fg=Colors.ACCENT_WARNING)
        else:
            self.vfr_info_label.config(text="Constant Frame Rate (CFR)", fg=Colors.ACCENT_SUCCESS)
    
    def add_advanced_content(self, default_batch, default_ram, default_cpu):
        """Add advanced settings content"""
        if self._adv_content_added:
            return
        
        self.adv_content = tk.Frame(self.adv_frame, bg=Colors.BG_MEDIUM)
        
        # Batch size
        batch_frame = tk.Frame(self.adv_content, bg=Colors.BG_MEDIUM)
        batch_frame.pack(fill='x', pady=5)
        tk.Label(batch_frame, text="Batch Size:", bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY, width=15, anchor='w').pack(side='left')
        self.batch_var = tk.StringVar(value=str(default_batch))
        batch_entry = tk.Entry(batch_frame, textvariable=self.batch_var, width=10, bg=Colors.BG_LIGHT, fg=Colors.TEXT_PRIMARY, insertbackground=Colors.TEXT_PRIMARY)
        batch_entry.pack(side='left', padx=10)
        tk.Label(batch_frame, text="frames (1 = safest for shared memory)", 
                 bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED, font=Fonts.SMALL).pack(side='left')
        
        # RAM limit
        ram_frame = tk.Frame(self.adv_content, bg=Colors.BG_MEDIUM)
        ram_frame.pack(fill='x', pady=5)
        tk.Label(ram_frame, text="Max RAM Usage:", bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY, width=15, anchor='w').pack(side='left')
        self.ram_var = tk.StringVar(value=str(default_ram))
        ram_entry = tk.Entry(ram_frame, textvariable=self.ram_var, width=10, bg=Colors.BG_LIGHT, fg=Colors.TEXT_PRIMARY, insertbackground=Colors.TEXT_PRIMARY)
        ram_entry.pack(side='left', padx=10)
        tk.Label(ram_frame, text="%", bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY).pack(side='left')
        
        # CPU limit
        cpu_frame = tk.Frame(self.adv_content, bg=Colors.BG_MEDIUM)
        cpu_frame.pack(fill='x', pady=5)
        tk.Label(cpu_frame, text="Max CPU Usage:", bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY, width=15, anchor='w').pack(side='left')
        self.cpu_var = tk.StringVar(value=str(default_cpu))
        cpu_entry = tk.Entry(cpu_frame, textvariable=self.cpu_var, width=10, bg=Colors.BG_LIGHT, fg=Colors.TEXT_PRIMARY, insertbackground=Colors.TEXT_PRIMARY)
        cpu_entry.pack(side='left', padx=10)
        tk.Label(cpu_frame, text="%", bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY).pack(side='left')
        
        # Store reference to content
        self.adv_frame.content = self.adv_content
        self._adv_content_added = True
    
    def update_file_label(self, filename):
        """Update file selection display"""
        if filename:
            self.input_path = filename
            self.file_label.config(text=f"Selected: {Path(filename).name}")
            self.drop_area.set_file(filename)
            
            # Auto-generate output path if not set
            if not self.output_path_var.get():
                output_dir = Path(filename).parent / "output"
                output_dir.mkdir(exist_ok=True)
                default_output = output_dir / f"{Path(filename).stem}_upscaled.mp4"
                self.output_path_var.set(str(default_output))
                self.output_path = str(default_output)
    
    def update_status(self, message, msg_type='info'):
        """Update status text"""
        self.status_text.add_message(message, msg_type)
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar['value'] = value
    
    def set_processing_state(self, is_processing):
        """Update UI state during processing"""
        if is_processing:
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.progress_bar['value'] = 0
        else:
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
    
    def get_settings(self):
        """Get all current settings"""
        settings = {
            "enhance": self.enhance_var.get(),
            "output_path": self.output_path_var.get()
        }
        
        # Add advanced settings if available
        if hasattr(self, 'batch_var'):
            settings["batch_size"] = int(self.batch_var.get())
            settings["ram_limit"] = int(self.ram_var.get())
            settings["cpu_limit"] = int(self.cpu_var.get())
        
        return settings
    
    def get_video_info(self):
        """Get current video info (for use in main app)"""
        return {
            'fps': self.fps_info_label.cget('text') if self.fps_info_label else '--',
            'is_vfr': 'VFR' in self.vfr_info_label.cget('text') if self.vfr_info_label else False
        }
    
    def show(self):
        """Show the page"""
        if self.frame:
            self.frame.pack(expand=True, fill='both')
    
    def hide(self):
        """Hide the page"""
        if self.frame:
            self.frame.pack_forget()