# ui/home_page.py - Modern Home Page

import tkinter as tk
from tkinter import ttk
from .styles import Colors, Fonts


class HomePage:
    """Modern home page with feature buttons"""
    
    def __init__(self, parent, on_upscale, on_frame_rate, on_options, on_exit):
        self.parent = parent
        self.on_upscale = on_upscale
        self.on_frame_rate = on_frame_rate
        self.on_options = on_options
        self.on_exit = on_exit
        self.frame = None
        self.create_page()
    
    def create_page(self):
        """Create home page layout"""
        self.frame = tk.Frame(self.parent, bg=Colors.BG_DARK)
        
        # Main container
        container = tk.Frame(self.frame, bg=Colors.BG_DARK)
        container.pack(expand=True, fill='both', padx=60, pady=60)
        
        # Title Section
        title_frame = tk.Frame(container, bg=Colors.BG_DARK)
        title_frame.pack(pady=(0, 40))
        
        # Main Title
        title = tk.Label(
            title_frame,
            text="NEXUS",
            font=Fonts.TITLE,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_PRIMARY
        )
        title.pack()
        
        subtitle = tk.Label(
            title_frame,
            text="AI-Powered Video Enhancement Suite",
            font=Fonts.SUBTITLE,
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_SECONDARY
        )
        subtitle.pack()
        
        # Tagline
        tagline = tk.Label(
            title_frame,
            text="720p → 1080p | AI Upscaling | Smooth 60fps",
            font=Fonts.SMALL,
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_MUTED
        )
        tagline.pack(pady=(10, 0))
        
        # Buttons Section
        buttons_frame = tk.Frame(container, bg=Colors.BG_DARK)
        buttons_frame.pack(expand=True, pady=40)
        
        # Button configurations
        buttons = [
            {
                'text': '🎬 UPScale Video',
                'command': self.on_upscale,
                'color': Colors.ACCENT_PRIMARY,
                'description': 'Enhance video resolution from 720p to 1080p'
            },
            {
                'text': '🎯 Frame Rate Up',
                'command': self.on_frame_rate,
                'color': Colors.ACCENT_SECONDARY,
                'description': 'Convert to smooth 60fps with constant frame rate'
            },
            {
                'text': '⚙️ Options',
                'command': self.on_options,
                'color': Colors.ACCENT_INFO,
                'description': 'Configure batch size, memory limits, and more'
            },
            {
                'text': '🚪 Exit',
                'command': self.on_exit,
                'color': Colors.ACCENT_DANGER,
                'description': 'Close NexusUpscaler'
            }
        ]
        
        # Create each button
        for btn_config in buttons:
            btn_frame = tk.Frame(buttons_frame, bg=Colors.BG_DARK)
            btn_frame.pack(pady=15)
            
            button = tk.Button(
                btn_frame,
                text=btn_config['text'],
                font=Fonts.BUTTON,
                bg=btn_config['color'],
                fg=Colors.TEXT_PRIMARY,
                padx=50,
                pady=15,
                command=btn_config['command'],
                relief='flat',
                cursor='hand2',
                borderwidth=0
            )
            button.pack()
            
            # Hover effect
            def on_enter(e, btn=button, color=btn_config['color']):
                btn.config(bg=self._lighten_color(color))
            
            def on_leave(e, btn=button, color=btn_config['color']):
                btn.config(bg=color)
            
            button.bind('<Enter>', on_enter)
            button.bind('<Leave>', on_leave)
            
            # Description
            desc = tk.Label(
                btn_frame,
                text=btn_config['description'],
                font=Fonts.SMALL,
                bg=Colors.BG_DARK,
                fg=Colors.TEXT_MUTED
            )
            desc.pack(pady=(5, 0))
        
        # Footer
        footer = tk.Label(
            container,
            text="Powered by NexusNet AI | Optimized for Intel Iris Xe",
            font=Fonts.SMALL,
            bg=Colors.BG_DARK,
            fg=Colors.TEXT_MUTED
        )
        footer.pack(side='bottom', pady=20)
    
    def _lighten_color(self, color):
        """Lighten color for hover effect"""
        # Simple lightening - you can implement proper color lightening
        if color == Colors.ACCENT_PRIMARY:
            return '#7d6ef0'
        elif color == Colors.ACCENT_SECONDARY:
            return '#1ae6e0'
        elif color == Colors.ACCENT_INFO:
            return '#2a9dff'
        elif color == Colors.ACCENT_DANGER:
            return '#e74c4c'
        return color
    
    def show(self):
        if self.frame:
            self.frame.pack(expand=True, fill='both')
    
    def hide(self):
        if self.frame:
            self.frame.pack_forget()