import customtkinter as ctk
from theme import *

class SyncControls(ctk.CTkFrame):
    def __init__(self, master, peers, sync_callback, sync_all_callback, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=CORNER_RADIUS,
            **kwargs
        )
        
        self.sync_callback = sync_callback
        self.sync_all_callback = sync_all_callback
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=PAD_LG, pady=(PAD_LG, PAD_MD))
        
        self.lbl = ctk.CTkLabel(
            self.header_frame,
            text="Network Sync",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H3, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl.pack(side="left")
        
        self.status_lbl = ctk.CTkLabel(
            self.header_frame,
            text="● In Sync" if True else "● Diverged",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL, weight="bold"),
            text_color=SUCCESS
        )
        self.status_lbl.pack(side="right")
        
        # Pairwise Grid
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))
        
        self._build_grid(peers)
        
        # Sync All Button
        self.sync_all_btn = ctk.CTkButton(
            self,
            text="🔄 Sync All",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_BODY, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color=ACCENT,
            text_color=ACCENT_LIGHT,
            hover_color=BG_HOVER,
            command=self.sync_all_callback
        )
        self.sync_all_btn.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))

    def _build_grid(self, peers):
        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        if not peers or len(peers) < 2:
            lbl = ctk.CTkLabel(
                self.grid_frame,
                text="Not enough peers.",
                font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
                text_color=TEXT_MUTED
            )
            lbl.pack()
            return
            
        # Create buttons for each pair (A↔B, B↔C, A↔C)
        col = 0
        row = 0
        for i in range(len(peers)):
            for j in range(i + 1, len(peers)):
                p1, p2 = peers[i], peers[j]
                
                btn = ctk.CTkButton(
                    self.grid_frame,
                    text=f"{p1} ↔ {p2}",
                    font=ctk.CTkFont(family=FONT_MONO, size=SIZE_BODY, weight="bold"),
                    fg_color=BG_TERTIARY,
                    hover_color=BG_HOVER,
                    text_color=TEXT_PRIMARY,
                    width=80,
                    command=lambda a=p1, b=p2: self.sync_callback(a, b)
                )
                btn.grid(row=row, column=col, padx=4, pady=4)
                
                col += 1
                if col > 1:  # 2 columns max
                    col = 0
                    row += 1

    def update_state(self, peers, all_synced: bool):
        self._build_grid(peers)
        if all_synced:
            self.status_lbl.configure(text="● In Sync", text_color=SUCCESS)
        else:
            self.status_lbl.configure(text="● Diverged", text_color=WARNING)
