# ui/__init__.py - Updated imports

from .styles import Colors, Fonts, Theme
from .widgets import DragDropArea, StatusText, GradientButton, CollapsibleFrame
from .home_page import HomePage
from .main_page import MainPage
from .frame_rate_page import FrameRatePage
from .options_page import OptionsPage

__all__ = [
    'Colors', 'Fonts', 'Theme',
    'DragDropArea', 'StatusText', 'GradientButton', 'CollapsibleFrame',
    'HomePage', 'MainPage', 'FrameRatePage', 'OptionsPage'
]