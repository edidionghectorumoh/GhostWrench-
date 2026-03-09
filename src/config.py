"""
Theme configuration for Sturdivant AI Lab bioluminescent visual identity.
Provides centralized color palette and animation timings for consistent styling.
"""

from dataclasses import dataclass, asdict
from typing import Dict


# Application Constants
APP_NAME = "MoCo Lantern"
APP_SUBTITLE = "Community Resource Co-Pilot"


@dataclass
class ThemeColors:
    """Bioluminescent color palette inspired by deep-sea bioluminescence"""
    primary_glow: str = "#00d4ff"      # Cyan glow - primary accent
    secondary_glow: str = "#16c79a"    # Teal accent - success states
    urgent_pulse: str = "#e94560"      # Red - urgent cases
    background_dark: str = "#0f0f1e"   # Deep space background
    surface_dark: str = "#1a1a2e"      # Card/surface color
    trail_fade: str = "#533483"        # Purple - resource trails


@dataclass
class AnimationTimings:
    """Animation durations and easing functions"""
    glow_duration: str = "2s"
    pulse_duration: str = "1.5s"
    trail_fade_duration: str = "3s"
    ease_function: str = "cubic-bezier(0.4, 0, 0.2, 1)"


class ThemeConfig:
    """Central theme configuration for the application"""
    
    def __init__(self):
        self.colors = ThemeColors()
        self.animations = AnimationTimings()
    
    def to_css_variables(self) -> Dict[str, str]:
        """Convert theme config to CSS custom properties"""
        return {
            "--primary-glow": self.colors.primary_glow,
            "--secondary-glow": self.colors.secondary_glow,
            "--urgent-pulse": self.colors.urgent_pulse,
            "--background-dark": self.colors.background_dark,
            "--surface-dark": self.colors.surface_dark,
            "--trail-fade": self.colors.trail_fade,
            "--glow-duration": self.animations.glow_duration,
            "--pulse-duration": self.animations.pulse_duration,
            "--trail-fade-duration": self.animations.trail_fade_duration,
            "--ease-function": self.animations.ease_function,
        }
    
    def get_streamlit_config(self) -> Dict[str, any]:
        """Generate Streamlit theme configuration"""
        return {
            "primaryColor": self.colors.primary_glow,
            "backgroundColor": self.colors.background_dark,
            "secondaryBackgroundColor": self.colors.surface_dark,
            "textColor": "#ffffff",
            "font": "sans serif"
        }
