# ui/options_page.py - Settings/Options Page with Centered Layout

import tkinter as tk
from tkinter import ttk
import psutil
from .styles import Colors, Fonts


class OptionsPage:
    """Settings and configuration page with centered layout"""
    
    def __init__(self, parent, on_back, on_save, current_settings):
        self.parent = parent
        self.on_back = on_back
        self.on_save = on_save
        self.current_settings = current_settings
        self.frame = None
        self.batch_var = None
        self.ram_var = None
        self.cpu_var = None
        self.denoise_var = None
        self.sharpen_var = None
        self.create_page()
    
    def create_page(self):
        """Create options page layout"""
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
        
        # Center container - everything will be centered
        center_container = tk.Frame(scrollable_frame, bg=Colors.BG_DARK)
        center_container.pack(expand=True, fill='both')
        
        # Main content with fixed width for centering
        main_container = tk.Frame(center_container, bg=Colors.BG_DARK)
        main_container.pack(expand=True, padx=40, pady=30)
        
        # Header
        header = tk.Frame(main_container, bg=Colors.BG_DARK)
        header.pack(fill='x', pady=(0, 30))
        
        back_btn = tk.Button(
            header,
            text="← Back to Home",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=20,
            pady=8,
            command=self.on_back,
            relief='flat',
            cursor='hand2'
        )
        back_btn.pack(side='left')
        
        title = tk.Label(
            header,
            text="Settings",
            font=Fonts.HEADING,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_PRIMARY
        )
        title.pack(side='right', padx=30)
        
        # ── System Information Card ─────────────────────────────────────────
        sys_card = tk.Frame(
            main_container,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        sys_card.pack(fill='x', pady=(0, 20))
        
        # Card header
        sys_header = tk.Frame(sys_card, bg=Colors.BG_MEDIUM)
        sys_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            sys_header,
            text="💻 System Information",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # System info content in two columns
        info_frame = tk.Frame(sys_card, bg=Colors.BG_MEDIUM)
        info_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        # Get system info
        cpu_count = psutil.cpu_count()
        ram_total = psutil.virtual_memory().total / (1024**3)
        ram_available = psutil.virtual_memory().available / (1024**3)
        ram_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Center the info columns
        info_center = tk.Frame(info_frame, bg=Colors.BG_MEDIUM)
        info_center.pack(anchor='center')
        
        # Left column
        left_col = tk.Frame(info_center, bg=Colors.BG_MEDIUM)
        left_col.pack(side='left', padx=(0, 40))
        
        sys_info_left = [
            ("CPU Cores:", f"{cpu_count}"),
            ("CPU Usage:", f"{cpu_percent}%"),
            ("RAM Total:", f"{ram_total:.1f} GB"),
        ]
        
        for label, value in sys_info_left:
            row = tk.Frame(left_col, bg=Colors.BG_MEDIUM)
            row.pack(fill='x', pady=4)
            tk.Label(
                row, text=label, width=15, anchor='w',
                bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY,
                font=Fonts.NORMAL
            ).pack(side='left')
            tk.Label(
                row, text=value, anchor='w',
                bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY,
                font=Fonts.NORMAL
            ).pack(side='left', padx=(10, 0))
        
        # Right column
        right_col = tk.Frame(info_center, bg=Colors.BG_MEDIUM)
        right_col.pack(side='left')
        
        sys_info_right = [
            ("RAM Available:", f"{ram_available:.1f} GB ({ram_percent}% used)"),
            ("GPU:", "Intel Iris Xe"),
            ("GPU Memory:", "Shared (System RAM)"),
        ]
        
        for label, value in sys_info_right:
            row = tk.Frame(right_col, bg=Colors.BG_MEDIUM)
            row.pack(fill='x', pady=4)
            tk.Label(
                row, text=label, width=15, anchor='w',
                bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY,
                font=Fonts.NORMAL
            ).pack(side='left')
            tk.Label(
                row, text=value, anchor='w',
                bg=Colors.BG_MEDIUM, fg=Colors.ACCENT_SUCCESS,
                font=Fonts.NORMAL
            ).pack(side='left', padx=(10, 0))
        
        # ── Performance Settings (Double Column Layout) ─────────────────────
        perf_card = tk.Frame(
            main_container,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        perf_card.pack(fill='x', pady=(0, 20))
        
        # Card header
        perf_header = tk.Frame(perf_card, bg=Colors.BG_MEDIUM)
        perf_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            perf_header,
            text="⚡ Performance Settings",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_SECONDARY
        ).pack()
        
        # Settings content - Centered double column
        perf_content = tk.Frame(perf_card, bg=Colors.BG_MEDIUM)
        perf_content.pack(fill='x', padx=20, pady=(0, 15))
        
        # Center the performance settings
        perf_center = tk.Frame(perf_content, bg=Colors.BG_MEDIUM)
        perf_center.pack(anchor='center')
        
        # Left column - Batch Size
        left_perf = tk.Frame(perf_center, bg=Colors.BG_MEDIUM)
        left_perf.pack(side='left', padx=(0, 40))
        
        # Batch Size
        batch_frame = tk.Frame(left_perf, bg=Colors.BG_MEDIUM)
        batch_frame.pack(fill='x', pady=10)
        tk.Label(
            batch_frame, text="Batch Size:", width=18, anchor='w',
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        self.batch_var = tk.StringVar(value=str(self.current_settings.get('batch_size', 1)))
        batch_entry = tk.Entry(
            batch_frame, textvariable=self.batch_var, width=8,
            bg=Colors.BG_LIGHT, fg=Colors.TEXT_PRIMARY,
            insertbackground=Colors.TEXT_PRIMARY,
            font=Fonts.NORMAL
        )
        batch_entry.pack(side='left', padx=10)
        tk.Label(
            batch_frame, text="frames (1 = safest)",
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL
        ).pack(side='left')
        
        # RAM Limit
        ram_frame = tk.Frame(left_perf, bg=Colors.BG_MEDIUM)
        ram_frame.pack(fill='x', pady=10)
        tk.Label(
            ram_frame, text="Max RAM Usage:", width=18, anchor='w',
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        self.ram_var = tk.StringVar(value=str(self.current_settings.get('ram_limit', 70)))
        ram_scale = tk.Scale(
            ram_frame, from_=20, to=90, orient='horizontal',
            variable=self.ram_var, bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY, length=150,
            troughcolor=Colors.BG_LIGHT, highlightthickness=0
        )
        ram_scale.pack(side='left', padx=10)
        tk.Label(
            ram_frame, text="%",
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        
        # Right column - CPU Limit
        right_perf = tk.Frame(perf_center, bg=Colors.BG_MEDIUM)
        right_perf.pack(side='left')
        
        # CPU Limit
        cpu_frame = tk.Frame(right_perf, bg=Colors.BG_MEDIUM)
        cpu_frame.pack(fill='x', pady=10)
        tk.Label(
            cpu_frame, text="Max CPU Usage:", width=18, anchor='w',
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        self.cpu_var = tk.StringVar(value=str(self.current_settings.get('cpu_limit', 50)))
        cpu_scale = tk.Scale(
            cpu_frame, from_=10, to=80, orient='horizontal',
            variable=self.cpu_var, bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY, length=150,
            troughcolor=Colors.BG_LIGHT, highlightthickness=0
        )
        cpu_scale.pack(side='left', padx=10)
        tk.Label(
            cpu_frame, text="%",
            bg=Colors.BG_MEDIUM, fg=Colors.TEXT_PRIMARY,
            font=Fonts.NORMAL
        ).pack(side='left')
        
        # Info note (centered)
        info_note = tk.Label(
            left_perf,
            text="💡 Lower batch size = less memory usage\n   Higher batch size = faster processing",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify='center'
        )
        info_note.pack(anchor='center', pady=(10, 0))
        
        # ── Recommendation Card ──────────────────────────────────────────────
        rec_card = tk.Frame(
            main_container,
            bg=Colors.BG_MEDIUM,
            relief='flat',
            bd=0
        )
        rec_card.pack(fill='x', pady=(0, 20))
        
        rec_header = tk.Frame(rec_card, bg=Colors.BG_MEDIUM)
        rec_header.pack(fill='x', padx=20, pady=(15, 10))
        
        tk.Label(
            rec_header,
            text="💡 Recommended Settings",
            font=Fonts.SECTION_HEADER,
            bg=Colors.BG_MEDIUM,
            fg=Colors.ACCENT_WARNING
        ).pack()
        
        rec_text = tk.Label(
            rec_card,
            text="• Batch Size: 1 (safest for shared GPU memory)\n"
                 "• RAM Limit: 70% (prevents system slowdown)\n"
                 "• CPU Limit: 50% (leaves resources for system)",
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.SMALL,
            justify='center',
            padx=20,
            pady=15
        )
        rec_text.pack(anchor='center')
        
        # ── Action Buttons ───────────────────────────────────────────────────
        btn_frame = tk.Frame(main_container, bg=Colors.BG_DARK)
        btn_frame.pack(pady=20)
        
        save_btn = tk.Button(
            btn_frame,
            text="💾 SAVE SETTINGS",
            font=Fonts.BUTTON,
            bg=Colors.ACCENT_SUCCESS,
            fg=Colors.TEXT_PRIMARY,
            padx=40,
            pady=12,
            command=self._save_settings,
            relief='flat',
            cursor='hand2'
        )
        save_btn.pack(side='left', padx=10)
        
        reset_btn = tk.Button(
            btn_frame,
            text="⟳ RESET TO DEFAULTS",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=30,
            pady=12,
            command=self._reset_defaults,
            relief='flat',
            cursor='hand2'
        )
        reset_btn.pack(side='left', padx=10)
        
        # Footer note
        footer = tk.Label(
            main_container,
            text="Changes apply to next upscaling job",
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_MUTED,
            font=Fonts.SMALL
        )
        footer.pack(pady=(20, 0))
    
    def _save_settings(self):
        """Save settings"""
        settings = {
            'batch_size': int(self.batch_var.get()),
            'ram_limit': int(self.ram_var.get()),
            'cpu_limit': int(self.cpu_var.get()),
            'denoise': self.denoise_var.get(),
            'sharpen': self.sharpen_var.get()
        }
        self.on_save(settings)
    
    def _reset_defaults(self):
        """Reset to default settings"""
        self.batch_var.set("1")
        self.ram_var.set("70")
        self.cpu_var.set("50")
        self.denoise_var.set(False)
        self.sharpen_var.set(False)
    
    def show(self):
        """Show the page"""
        if self.frame:
            self.frame.pack(expand=True, fill='both')
    
    def hide(self):
        """Hide the page"""
        if self.frame:
            self.frame.pack_forget()