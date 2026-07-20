"""
Ω OMEGA Design System (§384)

Design tokens, spacing, color, typography, radius constants.
Theme definitions for both CLI and web.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


# ── Design Tokens ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DesignTokens:
    """Global design tokens shared across all Omega surfaces."""
    # Fonts
    font_display: str = "Hanken Grotesk"
    font_body: str = "Inter"
    font_code: str = "JetBrains Mono"

    # Core colors
    color_bg: str = "#0c0c11"
    color_surface: str = "#1a1a24"
    color_border: str = "#2a2a3a"
    color_text: str = "#e8e8ed"
    color_text_muted: str = "#888899"
    color_accent_primary: str = "#33e8b0"  # Emerald
    color_accent_secondary: str = "#4285F4"  # Blue

    # Spacing scale (in px)
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 24
    space_6: int = 32
    space_8: int = 48
    space_10: int = 64

    # Radius
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_xl: int = 16

    # Sidebar
    sidebar_width: int = 280
    chat_max_width: int = 800

    # Typography scale
    text_xs: str = "0.75rem"
    text_sm: str = "0.875rem"
    text_base: str = "1rem"
    text_lg: str = "1.125rem"
    text_xl: str = "1.25rem"
    text_2xl: str = "1.5rem"
    text_3xl: str = "1.875rem"


TOKENS = DesignTokens()


# ── Theme Definitions ──────────────────────────────────────────────────────

@dataclass
class ThemeDef:
    """A complete theme definition."""
    name: str
    colors: Dict[str, str]
    is_dark: bool = True


THEMES: Dict[str, ThemeDef] = {
    "default-dark": ThemeDef(
        name="default-dark",
        is_dark=True,
        colors={
            "bg": "#0c0c11",
            "surface": "#1a1a24",
            "border": "#2a2a3a",
            "text": "#e8e8ed",
            "text_muted": "#888899",
            "accent": "#33e8b0",
            "accent_secondary": "#4285F4",
            "error": "#ef4444",
            "warning": "#f59e0b",
            "success": "#22c55e",
        },
    ),
    "default-light": ThemeDef(
        name="default-light",
        is_dark=False,
        colors={
            "bg": "#ffffff",
            "surface": "#f5f5f7",
            "border": "#e0e0e6",
            "text": "#111111",
            "text_muted": "#666677",
            "accent": "#059669",
            "accent_secondary": "#2563eb",
            "error": "#dc2626",
            "warning": "#d97706",
            "success": "#16a34a",
        },
    ),
}


def get_theme(name: str = "default-dark") -> ThemeDef:
    """Get a theme by name."""
    return THEMES.get(name, THEMES["default-dark"])


def list_themes() -> list[str]:
    """List available theme names."""
    return list(THEMES.keys())
