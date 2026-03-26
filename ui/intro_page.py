# ui/intro_page.py - Intro/Welcome Page

import tkinter as tk
from tkinter import ttk, messagebox
from .styles import Colors, Fonts, Theme
from .widgets import GradientButton


class IntroPage:
    """Intro/Welcome page with title and start button"""
    
    def __init__(self, parent, on_start, on_system_info):
        self.parent = parent
        self.on_start = on_start
        self.on_system_info = on_system_info
        self.frame = None
        self.create_page()
    
    def create_page(self):
        """Create intro page layout"""
        self.frame = tk.Frame(self.parent, bg=Colors.BG_DARK)
        self.frame.pack(expand=True, fill='both')
        
        # Container for centered content
        container = tk.Frame(self.frame, bg=Colors.BG_DARK)
        container.pack(expand=True, fill='both', padx=40, pady=40)
        
        # Logo/Title
        title = tk.Label(
            container,
            text="NEXUS UPSCALER",
            font=Fonts.TITLE,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_BLUE
        )
        title.pack(pady=30)
        
        # Subtitle
        subtitle = tk.Label(
            container,
            text="AI-Powered Video Upscaler\n720p → 1080p | Game-Optimized",
            font=Fonts.SUBTITLE,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_GREEN
        )
        subtitle.pack(pady=10)
        
        # System Info Button
        sys_btn = tk.Button(
            container,
            text="📊 System Information",
            font=Fonts.NORMAL,
            bg=Colors.BG_MEDIUM,
            fg=Colors.TEXT_PRIMARY,
            padx=20,
            pady=8,
            command=self.on_system_info,
            relief='flat',
            cursor='hand2'
        )
        sys_btn.pack(pady=10)
        
        # Start Button
        start_btn = GradientButton(
            container,
            text="START UPSCALING",
            command=self.on_start,
            bg_color=Colors.ACCENT_BLUE
        )
        start_btn.pack(pady=20)
        
        # Exit Button
        exit_btn = tk.Button(
            container,
            text="EXIT",
            font=Fonts.NORMAL,
            bg=Colors.ACCENT_RED,
            fg=Colors.TEXT_PRIMARY,
            padx=30,
            pady=8,
            command=self.parent.quit,
            relief='flat',
            cursor='hand2'
        )
        exit_btn.pack(pady=10)
        
        # Footer
        footer = tk.Label(
            container,
            text="© 2024 NexusUpscaler | Optimized for Intel Iris Xe",
            font=Fonts.SMALL,
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_SECONDARY
        )
        footer.pack(side='bottom', pady=20)
    
    def show(self):
        """Show the page"""
        if self.frame:
            self.frame.lift()
            self.frame.pack(expand=True, fill='both')
    
    def hide(self):
        """Hide the page"""
        if self.frame:
            self.frame.pack_forget()