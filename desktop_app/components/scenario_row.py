import customtkinter as ctk
from theme import *

class ScenarioRow(ctk.CTkFrame):
    def __init__(self, master, scenario_name, data, is_odd=False, **kwargs):
        bg = BG_TERTIARY if is_odd else "transparent"
        super().__init__(master, fg_color=bg, **kwargs)
        
        self.grid_columnconfigure(0, weight=3) # Name
        self.grid_columnconfigure(1, weight=1) # Duration
        self.grid_columnconfigure(2, weight=1) # Hash match
        self.grid_columnconfigure(3, weight=1) # Pass
        
        # Name
        self.name_lbl = ctk.CTkLabel(
            self,
            text=scenario_name,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_BODY, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        )
        self.name_lbl.grid(row=0, column=0, sticky="w", padx=PAD_LG, pady=PAD_SM)
        
        # Duration
        dur = data.get("duration", 0)
        dur_text = f"{dur*1000:.2f} ms" if dur < 0.1 else f"{dur:.2f} s"
        self.dur_lbl = ctk.CTkLabel(
            self,
            text=dur_text,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
            text_color=TEXT_MUTED
        )
        self.dur_lbl.grid(row=0, column=1, sticky="e", padx=PAD_MD)
        
        # Hash match
        match = data.get("hash_match", False)
        self.hash_lbl = ctk.CTkLabel(
            self,
            text="✅ MATCH" if match else "❌ FAIL",
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
            text_color=SUCCESS if match else DANGER
        )
        self.hash_lbl.grid(row=0, column=2, sticky="e", padx=PAD_MD)
        
        # Overall Pass
        passed = data.get("pass", False)
        badge_frame = ctk.CTkFrame(
            self,
            fg_color=SUCCESS_DIM if passed else DANGER_DIM,
            corner_radius=CORNER_RADIUS_SM
        )
        badge_frame.grid(row=0, column=3, sticky="e", padx=PAD_LG, pady=4)
        
        badge_lbl = ctk.CTkLabel(
            badge_frame,
            text="PASS" if passed else "FAIL",
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY, weight="bold"),
            text_color=SUCCESS if passed else DANGER
        )
        badge_lbl.pack(padx=8, pady=2)
