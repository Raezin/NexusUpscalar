# ui/frame_rate_page.py - Frame Rate Conversion Page with 2-Column Layout

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from .styles import Colors, Fonts
from .widgets import DragDropArea, StatusText


class FrameRatePage:
    """Frame rate conversion and constant frame rate page with 2-column layout"""
    
    def __init__(self, parent, on_back, on_process):
        self.parent = parent
        self.on_back = on_back
        self.on_process = on_process
        self.frame = None
        self.drop_area = None
        self.file_label = None
        self.fps_var = None
        self.method_var = None
        self.status_text = None
        self.progress_bar = None
        self.process_btn = None
        self.input_path = None
        self.output_path_var = None
        self.output_path = None
        self.fps_info_label = None
        self.vfr_info_label = None
        self.create_page()
    
    def create_page(self):
        """Create frame rate page layout with 2-column design"""
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
        header.pack(fill='x', pady=(0, 30))
        
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
            text="Frame Rate Conversion",
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
            on_drop_callback=self._on_drop
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
            command=self._browse_file,
            relief='flat',
            cursor='hand2'
        )
        browse_btn.pack(pady=10)
        
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
        
        # ── RIGHT COLUMN: Settings ───────────────────────────────────────────
        settings_card = tk.Frame(
            right_column,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        settings_card.pack(fill='both', expand=True)
        
        # Card header
        settings_header = tk.Frame(settings_card, bg=Colors.BG_MEDIUM)
        settings_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            settings_header,
            text="⚙️ Conversion Settings",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Settings content
        settings_content = tk.Frame(settings_card, bg=Colors.BG_MEDIUM)
        settings_content.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Target FPS
        fps_frame = tk.Frame(settings_content, bg=Colors.BG_MEDIUM)
        fps_frame.pack(fill='x', pady=15)
        
        tk.Label(
            fps_frame, 
            text="Target FPS:", 
            width=15, anchor='w',
            bg=Colors.BG_MEDIUM, 
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        
        self.fps_var = tk.StringVar(value="60")
        fps_options = [30, 60, 120, 144, 240]
        fps_menu = ttk.Combobox(
            fps_frame, 
            textvariable=self.fps_var, 
            values=fps_options, 
            width=10, 
            state='readonly'
        )
        fps_menu.pack(side='left', padx=10)
        
        tk.Label(
            fps_frame,
            text="frames per second",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL
        ).pack(side='left')
        
        # Interpolation method
        method_frame = tk.Frame(settings_content, bg=Colors.BG_MEDIUM)
        method_frame.pack(fill='x', pady=15)
        
        tk.Label(
            method_frame, 
            text="Method:", 
            width=15, anchor='w',
            bg=Colors.BG_MEDIUM, 
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        
        self.method_var = tk.StringVar(value="Motion Compensated")
        method_options = ["Motion Compensated", "Blend", "Duplicate"]
        method_menu = ttk.Combobox(
            method_frame, 
            textvariable=self.method_var, 
            values=method_options, 
            width=18, 
            state='readonly'
        )
        method_menu.pack(side='left', padx=10)
        
        # Method descriptions
        method_desc = tk.Label(
            settings_content,
            text="• Motion Compensated: Best quality, smooth motion\n"
                 "• Blend: Medium quality, blends frames\n"
                 "• Duplicate: Fastest, repeats frames",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify='left',
            anchor='w'
        )
        method_desc.pack(fill='x', pady=(15, 10), padx=25)
        
        # VFR notice
        vfr_notice = tk.Label(
            settings_content,
            text="ℹ️ Also fixes Variable Frame Rate (VFR) to Constant Frame Rate (CFR)",
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_WARNING,
            font=Fonts.SMALL,
            justify='center'
        )
        vfr_notice.pack(pady=(20, 10))
        
        # ── Progress Section (Full Width) ────────────────────────────────────
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
            text="📊 Progress",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        self.progress_bar = ttk.Progressbar(
            progress_card,
            mode='determinate',
            length=400,
            style="Modern.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(pady=10, padx=20)
        
        self.status_text = StatusText(progress_card)
        self.status_text.pack(fill='x', padx=20, pady=(0, 15))
        
        # ── Action Buttons ───────────────────────────────────────────────────
        btn_frame = tk.Frame(main_container, bg=Colors.BG_DARK)
        btn_frame.pack(pady=20)
        
        self.process_btn = tk.Button(
            btn_frame,
            text="🚀 PROCESS VIDEO",
            font=Fonts.BUTTON,
            bg=Colors.ACCENT_SUCCESS,
            fg=Colors.TEXT_PRIMARY,
            padx=50,
            pady=12,
            command=self._start_processing,
            relief='flat',
            cursor='hand2'
        )
        self.process_btn.pack(side='left', padx=10)
        
        back_btn_main = tk.Button(
            btn_frame,
            text="← Back to Home",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=25,
            pady=12,
            command=self.on_back,
            relief='flat',
            cursor='hand2'
        )
        back_btn_main.pack(side='left', padx=10)
    
    def _browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if filename:
            self.input_path = filename
            self.file_label.config(text=f"Selected: {Path(filename).name}")
            self.drop_area.set_file(filename)
            
            # Auto-generate output path if not set
            if not self.output_path_var.get():
                output_dir = Path(filename).parent / "output"
                output_dir.mkdir(exist_ok=True)
                default_output = output_dir / f"{Path(filename).stem}_60fps.mp4"
                self.output_path_var.set(str(default_output))
                self.output_path = str(default_output)
    
    def _on_drop(self, files):
        self.input_path = files
        self.file_label.config(text=f"Selected: {Path(files).name}")
        self.drop_area.set_file(files)
        
        # Auto-generate output path if not set
        if not self.output_path_var.get():
            output_dir = Path(files).parent / "output"
            output_dir.mkdir(exist_ok=True)
            default_output = output_dir / f"{Path(files).stem}_60fps.mp4"
            self.output_path_var.set(str(default_output))
            self.output_path = str(default_output)
    
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
    
    def _start_processing(self):
        if not self.input_path:
            self.status_text.add_message("❌ Please select a video file first", 'error')
            return
        
        if not self.output_path_var.get():
            self.status_text.add_message("❌ Please select an output location", 'error')
            return
        
        settings = {
            'target_fps': int(self.fps_var.get()),
            'method': self.method_var.get(),
            'output_path': self.output_path_var.get()
        }
        
        self.process_btn.config(state='disabled')
        self.on_process(self.input_path, settings, self.update_status, self.update_progress)
    
    def update_status(self, message, msg_type='info'):
        self.status_text.add_message(message, msg_type)
    
    def update_progress(self, value):
        self.progress_bar['value'] = value
    
    def show(self):
        if self.frame:
            self.frame.pack(expand=True, fill='both')
    
    def hide(self):
        if self.frame:
            self.frame.pack_forget()