import customtkinter as ctk
from theme import *

class ScoreCard(ctk.CTkFrame):
    def __init__(self, master, title, score_frac, color=ACCENT, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=CORNER_RADIUS,
            **kwargs
        )
        
        # Main label
        self.title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H3, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.title_lbl.pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_XS))
        
        # Score Value
        pct = int(score_frac * 100)
        self.val_lbl = ctk.CTkLabel(
            self,
            text=f"{pct}%",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_TITLE, weight="bold"),
            text_color=color
        )
        self.val_lbl.pack(anchor="w", padx=PAD_LG)
        
        # Progress Bar
        self.pbar = ctk.CTkProgressBar(
            self,
            progress_color=color,
            fg_color=BG_TERTIARY,
            height=6
        )
        self.pbar.pack(fill="x", padx=PAD_LG, pady=(PAD_SM, PAD_LG))
        self.pbar.set(score_frac)
