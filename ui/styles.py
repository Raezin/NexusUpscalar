# ui/styles.py - Add missing color aliases
import tkinter as tk
from tkinter import ttk

class Colors:
    """Modern color scheme"""
    # Dark theme
    BG_DARK = '#0a0e27'      # Deep dark blue
    BG_MEDIUM = '#141b33'    # Medium dark blue
    BG_LIGHT = '#1e2a3e'     # Lighter blue-gray
    BG_CARD = '#1a1f35'      # Card background
    
    # Accent colors
    ACCENT_PRIMARY = '#6c5ce7'      # Vibrant purple
    ACCENT_SECONDARY = '#00cec9'    # Turquoise
    ACCENT_SUCCESS = '#00b894'      # Green
    ACCENT_WARNING = '#fdcb6e'      # Yellow
    ACCENT_DANGER = '#d63031'       # Red
    ACCENT_INFO = '#0984e3'         # Blue
    
    # Legacy color aliases for compatibility
    ACCENT_BLUE = ACCENT_PRIMARY
    ACCENT_RED = ACCENT_DANGER
    ACCENT_GREEN = ACCENT_SUCCESS
    ACCENT_YELLOW = ACCENT_WARNING
    
    # Text color aliases
    TEXT_SUCCESS = ACCENT_SUCCESS
    TEXT_WARNING = ACCENT_WARNING
    TEXT_ERROR = ACCENT_DANGER
    TEXT_INFO = ACCENT_INFO
    
    # Gradient colors
    GRADIENT_START = '#6c5ce7'
    GRADIENT_END = '#00cec9'
    
    # Text colors
    TEXT_PRIMARY = '#ffffff'
    TEXT_SECONDARY = '#b2bec3'
    TEXT_MUTED = '#636e72'
    
    # Status colors
    SUCCESS = '#00b894'
    WARNING = '#fdcb6e'
    ERROR = '#d63031'
    INFO = '#0984e3'


class Fonts:
    """Font configurations"""
    TITLE = ('Segoe UI', 48, 'bold')
    SUBTITLE = ('Segoe UI', 14)
    HEADING = ('Segoe UI', 24, 'bold')
    SECTION_HEADER = ('Segoe UI', 12, 'bold')
    NORMAL = ('Segoe UI', 10)
    SMALL = ('Segoe UI', 9)
    BUTTON = ('Segoe UI', 11, 'bold')
    MONO = ('Consolas', 9)


class Theme:
    """Modern theme configuration"""
    
    @staticmethod
    def apply_theme(root):
        """Apply modern theme"""
        style = ttk.Style()
        
        # Configure progress bar
        style.configure(
            "Modern.Horizontal.TProgressbar",
            background=Colors.ACCENT_PRIMARY,
            troughcolor=Colors.BG_LIGHT,
            bordercolor=Colors.BG_MEDIUM,
            lightcolor=Colors.ACCENT_PRIMARY,
            darkcolor=Colors.ACCENT_PRIMARY,
            thickness=8
        )
        
        # Configure combobox
        style.configure(
            "Modern.TCombobox",
            fieldbackground=Colors.BG_LIGHT,
            background=Colors.BG_LIGHT,
            foreground=Colors.TEXT_PRIMARY,
            arrowcolor=Colors.TEXT_PRIMARY,
            borderwidth=1,
            relief="flat"
        )
        
        # Configure scrollbar
        style.configure(
            "Modern.Vertical.TScrollbar",
            background=Colors.BG_LIGHT,
            troughcolor=Colors.BG_DARK,
            arrowcolor=Colors.TEXT_PRIMARY,
            bordercolor=Colors.BG_MEDIUM,
            relief="flat"
        )
        
        # Configure label frame
        style.configure(
            "Modern.TLabelframe",
            background=Colors.BG_MEDIUM,
            foreground=Colors.TEXT_PRIMARY,
            borderwidth=1,
            relief="solid"
        )
        
        style.configure(
            "Modern.TLabelframe.Label",
            background=Colors.BG_MEDIUM,
            foreground=Colors.ACCENT_PRIMARY,
            font=Fonts.SECTION_HEADER
        )