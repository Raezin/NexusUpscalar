# ui/widgets.py - Fixed StatusText class

import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from .styles import Colors, Fonts


class DragDropArea(tk.Text):
    """Custom drag and drop area for video files"""
    
    def __init__(self, parent, on_drop_callback, **kwargs):
        super().__init__(
            parent,
            height=3,
            bg=Colors.BG_LIGHT,
            fg=Colors.TEXT_SECONDARY,
            font=Fonts.NORMAL,
            insertbackground=Colors.TEXT_PRIMARY,
            **kwargs
        )
        self.on_drop_callback = on_drop_callback
        self.config(state='normal')
        self.delete('1.0', tk.END)
        self.insert('1.0', "📁 Drag & Drop video file here\nor click 'Browse' to select")
        self.config(state='disabled')
        
        # Register drag & drop
        try:
            self.drop_target_register('*')
            self.dnd_bind('<<Drop>>', self._handle_drop)
        except AttributeError:
            pass
    
    def _handle_drop(self, event):
        """Handle dropped file"""
        files = event.data
        if files.startswith('{') and files.endswith('}'):
            files = files[1:-1]
        if files:
            self.on_drop_callback(files)
    
    def set_file(self, filename):
        """Update display with selected file"""
        self.config(state='normal')
        self.delete('1.0', tk.END)
        self.insert('1.0', f"✓ {Path(filename).name}")
        self.config(state='disabled')


class StatusText(scrolledtext.ScrolledText):
    """Scrollable text area for status updates"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            height=8,
            bg=Colors.BG_DARK,
            fg=Colors.ACCENT_SUCCESS,  # Changed from TEXT_SUCCESS to ACCENT_SUCCESS
            font=Fonts.MONO,
            **kwargs
        )
        
        # Configure tags
        self.tag_config('timestamp', foreground=Colors.TEXT_MUTED)
        self.tag_config('info', foreground=Colors.TEXT_PRIMARY)
        self.tag_config('success', foreground=Colors.ACCENT_SUCCESS)
        self.tag_config('warning', foreground=Colors.ACCENT_WARNING)
        self.tag_config('error', foreground=Colors.ACCENT_DANGER)
    
    def add_message(self, message, msg_type='info'):
        """Add message with timestamp and color"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.insert(tk.END, f"{message}\n", msg_type)
        
        self.see(tk.END)
        self.update()


class GradientButton(tk.Canvas):
    """Custom button with gradient effect"""
    
    def __init__(self, parent, text, command, bg_color=Colors.ACCENT_PRIMARY, width=200, **kwargs):
        super().__init__(
            parent,
            height=40,
            width=width,
            bg=parent.cget('bg'),
            highlightthickness=0,
            **kwargs
        )
        self.command = command
        self.bg_color = bg_color
        
        # Create button rectangle
        self.rect = self.create_rectangle(
            0, 0, width, 40,
            fill=bg_color,
            outline='',
            width=0
        )
        
        # Add text
        self.text_id = self.create_text(
            width//2, 20,
            text=text,
            fill='white',
            font=Fonts.BUTTON,
            anchor='center'
        )
        
        # Bind events
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.on_click)
    
    def on_enter(self, event):
        self.itemconfig(self.rect, fill=self._lighten_color(self.bg_color))
    
    def on_leave(self, event):
        self.itemconfig(self.rect, fill=self.bg_color)
    
    def on_click(self, event):
        if self.command:
            self.command()
    
    def _lighten_color(self, color):
        # Simple color lightening
        if color == Colors.ACCENT_PRIMARY:
            return '#7d6ef0'
        elif color == Colors.ACCENT_SECONDARY:
            return '#1ae6e0'
        elif color == Colors.ACCENT_SUCCESS:
            return '#1acf9e'
        elif color == Colors.ACCENT_DANGER:
            return '#e74c4c'
        elif color == Colors.ACCENT_INFO:
            return '#2a9dff'
        return color


class CollapsibleFrame(tk.LabelFrame):
    """Collapsible frame for advanced settings"""
    
    def __init__(self, parent, title, **kwargs):
        super().__init__(parent, text=title, **kwargs)
        self.content = None
        self.is_visible = False
        self.original_title = title
        
        # Bind click to toggle
        self.bind('<Button-1>', self.toggle)
    
    def toggle(self, event=None):
        """Toggle content visibility"""
        if self.is_visible:
            if self.content:
                self.content.destroy()
                self.content = None
            self.config(text=self.original_title)
            self.is_visible = False
        else:
            self.content = tk.Frame(self, bg=self.cget('bg'))
            self.content.pack(fill='x', pady=10)
            self.config(text=self.original_title + ' ▼')
            self.is_visible = True