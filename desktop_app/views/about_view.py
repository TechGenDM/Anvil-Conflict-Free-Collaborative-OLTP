import customtkinter as ctk
from theme import *

class AboutView(ctk.CTkFrame):
    def __init__(self, master, bridge, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_XL, pady=(PAD_XL, PAD_MD))
        
        title = ctk.CTkLabel(
            header,
            text="Architecture & Design",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_TITLE, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        title.pack(side="left")
        
        # Content Scrollable
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=PAD_XL, pady=(0, PAD_XL))
        self.grid_rowconfigure(1, weight=1)
        
        self._build_card(
            scroll,
            "1. The CRDT Lattice",
            "The engine is built on a layered CRDT architecture:\n\n"
            "• Peer: The facade. Holds a store and coordinates sync.\n"
            "• CRDTStore: The state. Maps table names to rows.\n"
            "• CRDTRow: Represents a single primary key. Holds cells and a tombstone flag.\n"
            "• CRDTCell: A Multi-Value Register. Resolves concurrent column edits.\n"
            "• VectorClock: Tracks causality across peers."
        )
        
        self._build_card(
            scroll,
            "2. The 6-Step Sync Protocol",
            "When Peer A and Peer B sync, they perform a symmetric bidirectional exchange:\n\n"
            "1. Both compute their state snapshots (Hashes).\n"
            "2. They exchange rows using Vector Clock dominance.\n"
            "3. Merged rows perform cell-level Multi-Value Register resolution.\n"
            "4. The Escrow Protocol resolves Uniqueness constraint violations.\n"
            "5. A fixed-point calculation computes visibility (Foreign Key cascades).\n"
            "6. Both peers reach a deterministic identical state."
        )
        
        self._build_card(
            scroll,
            "3. Escrow Uniqueness",
            "Standard CRDTs cannot enforce global uniqueness without coordination. "
            "This engine uses an 'Escrow-First' protocol. When two peers claim the same UNIQUE "
            "value offline, both inserts are marked 'pending'. Upon sync, a deterministic tie-breaker "
            "(min peer_id) commits one and rejects the other, preserving the invariant."
        )
        
        self._build_card(
            scroll,
            "4. Foreign Key Visibility",
            "Instead of cascading deletes destructively (which breaks commutativity), "
            "FKs are enforced dynamically. A parent delete sets a tombstone. A fixed-point "
            "algorithm then sweeps the store: any row referencing a tombstoned parent is marked "
            "invisible (orphaned), cascading down the hierarchy. If the parent is ever resurrected "
            "by a concurrent edit, the children instantly reappear."
        )

    def _build_card(self, parent, title, text):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=CORNER_RADIUS, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, PAD_LG))
        
        lbl_title = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H2, weight="bold"),
            text_color=ACCENT_LIGHT
        )
        lbl_title.pack(anchor="w", padx=PAD_XL, pady=(PAD_XL, PAD_SM))
        
        lbl_text = ctk.CTkLabel(
            card,
            text=text,
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_BODY),
            text_color=TEXT_PRIMARY,
            justify="left",
            wraplength=800
        )
        lbl_text.pack(anchor="w", padx=PAD_XL, pady=(0, PAD_XL))
