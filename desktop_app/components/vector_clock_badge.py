import customtkinter as ctk
from theme import *

class VectorClockBadge(ctk.CTkFrame):
    def __init__(self, master, clock_dict, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_TERTIARY,
            border_width=1,
            border_color=BORDER,
            corner_radius=CORNER_RADIUS_SM,
            **kwargs
        )
        
        # Display as {A:1, B:2}
        if not clock_dict:
            text = "{}"
        else:
            parts = [f"{k}:{v}" for k, v in sorted(clock_dict.items())]
            text = "{" + ", ".join(parts) + "}"
            
        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY),
            text_color=TEXT_CODE,
            padx=4,
            pady=2
        )
        self.label.pack()
