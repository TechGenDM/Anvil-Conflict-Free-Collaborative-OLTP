import customtkinter as ctk
from theme import *
from components.vector_clock_badge import VectorClockBadge
from components.state_table import StateTable

class PeerCard(ctk.CTkFrame):
    def __init__(self, master, peer_id, peer_data, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=CORNER_RADIUS_LG,
            **kwargs
        )
        
        self.peer_id = peer_id
        
        # Header (Peer ID + Hash)
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=PAD_LG, pady=PAD_LG)
        
        self.title = ctk.CTkLabel(
            self.header,
            text=f"Peer {peer_id}",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H1, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.title.pack(side="left")
        
        self.hash_lbl = ctk.CTkLabel(
            self.header,
            text=f"Hash: {peer_data.get('hash', '---')[:8]}",
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
            text_color=ACCENT_LIGHT
        )
        self.hash_lbl.pack(side="right")
        
        # Meta Info (Clock)
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.pack(fill="x", padx=PAD_LG, pady=(0, PAD_MD))
        
        self.clock_lbl = ctk.CTkLabel(
            self.meta_frame,
            text="Vector Clock:",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
            text_color=TEXT_MUTED
        )
        self.clock_lbl.pack(side="left", padx=(0, PAD_XS))
        
        self.clock_badge = VectorClockBadge(self.meta_frame, peer_data.get("clock", {}))
        self.clock_badge.pack(side="left")

        # Tables Container (Scrollable if needed, but we'll use a normal frame 
        # and let the parent scroll view handle scrolling if multiple cards exist)
        self.tables_container = ctk.CTkFrame(self, fg_color="transparent")
        self.tables_container.pack(fill="both", expand=True, padx=PAD_LG, pady=(0, PAD_LG))
        
        tables = peer_data.get("tables", {})
        if not tables:
            self.empty_lbl = ctk.CTkLabel(
                self.tables_container,
                text="Store is empty. Run some SQL to see tables.",
                font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
                text_color=TEXT_MUTED
            )
            self.empty_lbl.pack(pady=PAD_XL)
        else:
            for i, (table_name, table_data) in enumerate(sorted(tables.items())):
                tbl = StateTable(self.tables_container, table_name, table_data)
                tbl.pack(fill="x", pady=(0, PAD_LG if i < len(tables)-1 else 0))
