import customtkinter as ctk
from theme import *

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, navigate_callback, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_SECONDARY, 
            corner_radius=0, 
            width=SIDEBAR_WIDTH,
            **kwargs
        )
        self.navigate_callback = navigate_callback
        
        # Grid layout for the sidebar
        self.grid_rowconfigure(4, weight=1)  # Spacer
        
        # App Title / Logo
        self.logo_label = ctk.CTkLabel(
            self, 
            text="ANVIL", 
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_TITLE, weight="bold", slant="italic"),
            text_color=TEXT_PRIMARY
        )
        self.logo_label.grid(row=0, column=0, padx=PAD_XL, pady=(PAD_XXL, PAD_XS), sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self, 
            text="CRDT-Native OLTP", 
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY),
            text_color=ACCENT_LIGHT
        )
        self.subtitle_label.grid(row=1, column=0, padx=PAD_XL, pady=(0, PAD_XL), sticky="w")
        
        # Navigation Buttons
        self.nav_buttons = []
        
        self.btn_demo = self._create_nav_button("Interactive Demo", "demo", 2)
        self.btn_bench = self._create_nav_button("Benchmark Dashboard", "benchmark", 3)
        self.btn_about = self._create_nav_button("About / Architecture", "about", 5)
        
        # Version info at bottom
        self.version_label = ctk.CTkLabel(
            self, 
            text="Team Phi Continuum\nL3 Final: 100%", 
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY),
            text_color=TEXT_MUTED,
            justify="left"
        )
        self.version_label.grid(row=6, column=0, padx=PAD_XL, pady=PAD_XL, sticky="w")

        # Set initial active tab
        self.set_active("demo")

    def _create_nav_button(self, text, view_name, row):
        btn = ctk.CTkButton(
            self,
            text=text,
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_BODY, weight="bold"),
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            hover_color=BG_HOVER,
            anchor="w",
            height=40,
            command=lambda v=view_name: self._on_nav_click(v)
        )
        btn.grid(row=row, column=0, padx=PAD_SM, pady=PAD_XS, sticky="ew")
        btn.view_name = view_name
        self.nav_buttons.append(btn)
        return btn

    def _on_nav_click(self, view_name):
        self.set_active(view_name)
        self.navigate_callback(view_name)

    def set_active(self, view_name):
        for btn in self.nav_buttons:
            if btn.view_name == view_name:
                btn.configure(
                    fg_color=BG_TERTIARY,
                    text_color=TEXT_PRIMARY,
                    border_width=2,
                    border_color=ACCENT_DIM
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_SECONDARY,
                    border_width=0
                )
