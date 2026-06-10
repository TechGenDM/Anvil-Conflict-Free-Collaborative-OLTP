"""
Anvil CRDT Desktop App — Design Tokens & Theme Configuration
All colors, fonts, and spacing constants used across the app.
"""

# ── Color Palette ─────────────────────────────────────────────
# Dark mode first, inspired by the Anvil hackathon aesthetic

BG_PRIMARY = "#0d0d14"       # Deepest background
BG_SECONDARY = "#14141f"     # Card/panel backgrounds
BG_TERTIARY = "#1c1c2e"      # Input fields, hover states
BG_CARD = "#181828"           # Peer cards, elevated surfaces
BG_HOVER = "#22223a"          # Button hover

ACCENT = "#7c6cf0"            # Primary purple accent
ACCENT_LIGHT = "#a29bfe"      # Active/glow states
ACCENT_DIM = "#5a4fcf"        # Pressed states
ACCENT_BG = "#1a1830"         # Subtle accent background

SUCCESS = "#00d2b4"           # Pass, synced, committed
SUCCESS_DIM = "#004d40"       # Success background
DANGER = "#ff5252"            # Fail, rejected, tombstoned
DANGER_DIM = "#4a1515"        # Danger background
WARNING = "#ffb74d"           # Pending, orphaned
WARNING_DIM = "#4a3515"       # Warning background

TEXT_PRIMARY = "#e8e8f4"      # Main text
TEXT_SECONDARY = "#b0b0cc"    # Subtitles, secondary text
TEXT_MUTED = "#5c5c7a"        # Labels, captions
TEXT_CODE = "#c4b5fd"         # Code/SQL text

BORDER = "#2a2a40"            # Card borders
BORDER_LIGHT = "#3a3a55"      # Lighter borders

# ── Typography ────────────────────────────────────────────────

FONT_HEADING = "JetBrains Mono"
FONT_BODY = "Segoe UI"        # Falls back to system default
FONT_MONO = "JetBrains Mono"

# Font sizes
SIZE_TITLE = 28
SIZE_H1 = 22
SIZE_H2 = 18
SIZE_H3 = 14
SIZE_BODY = 13
SIZE_SMALL = 11
SIZE_TINY = 9

# ── Spacing ───────────────────────────────────────────────────

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24
PAD_XXL = 32

CORNER_RADIUS = 8
CORNER_RADIUS_SM = 4
CORNER_RADIUS_LG = 12

# ── Window ────────────────────────────────────────────────────

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
SIDEBAR_WIDTH = 200

# ── Status Colors ─────────────────────────────────────────────

STATUS_COLORS = {
    "committed": SUCCESS,
    "pending": WARNING,
    "rejected": DANGER,
    "ok": SUCCESS,
    "orphaned": WARNING,
}

STATUS_BG_COLORS = {
    "committed": SUCCESS_DIM,
    "pending": WARNING_DIM,
    "rejected": DANGER_DIM,
    "ok": SUCCESS_DIM,
    "orphaned": WARNING_DIM,
}
