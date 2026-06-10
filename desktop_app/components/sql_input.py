import customtkinter as ctk
from theme import *

class SqlInput(ctk.CTkFrame):
    def __init__(self, master, peers, execute_callback, preset_callback, **kwargs):
        super().__init__(
            master, 
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER,
            corner_radius=CORNER_RADIUS,
            **kwargs
        )
        
        self.execute_callback = execute_callback
        self.preset_callback = preset_callback
        
        self.grid_columnconfigure(0, weight=1)
        
        # Header Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=(PAD_LG, PAD_SM))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.lbl = ctk.CTkLabel(
            self.header_frame,
            text="Execute SQL",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H3, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl.grid(row=0, column=0, sticky="w")
        
        # Presets Menu
        self.preset_menu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["Load Preset...", "Reference Scenario", "Cell-Level Conflict", "Uniqueness Conflict", "FK Cascade"],
            command=self._on_preset_select,
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
            fg_color=BG_TERTIARY,
            button_color=BORDER,
            button_hover_color=BORDER_LIGHT,
            dropdown_fg_color=BG_SECONDARY,
            width=160
        )
        self.preset_menu.grid(row=0, column=2, sticky="e")
        
        # Controls Area
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_SM))
        
        self.peer_lbl = ctk.CTkLabel(
            self.controls_frame,
            text="Peer:",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
            text_color=TEXT_MUTED
        )
        self.peer_lbl.pack(side="left", padx=(0, PAD_SM))
        
        self.peer_var = ctk.StringVar(value=peers[0] if peers else "")
        self.peer_menu = ctk.CTkOptionMenu(
            self.controls_frame,
            variable=self.peer_var,
            values=peers if peers else ["A", "B", "C"],
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL),
            width=80
        )
        self.peer_menu.pack(side="left")
        
        # Text Box
        self.textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_BODY),
            fg_color=BG_TERTIARY,
            text_color=TEXT_CODE,
            border_width=1,
            border_color=BORDER,
            height=120
        )
        self.textbox.grid(row=2, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))
        self.textbox.insert("0.0", "CREATE TABLE users (id VARCHAR PRIMARY KEY, name VARCHAR);\nINSERT INTO users (id, name) VALUES ('u1', 'Alice');")
        
        # Action Area
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, sticky="ew", padx=PAD_LG, pady=(0, PAD_LG))
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        self.exec_btn = ctk.CTkButton(
            self.action_frame,
            text="Execute (Cmd+Enter)",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_BODY, weight="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_LIGHT,
            command=self._on_execute
        )
        self.exec_btn.grid(row=0, column=1, sticky="e")
        
        # Keyboard shortcut
        self.textbox.bind("<Command-Return>", lambda e: self._on_execute())
        self.textbox.bind("<Control-Return>", lambda e: self._on_execute())

    def update_peers(self, peers):
        self.peer_menu.configure(values=peers)
        if peers and self.peer_var.get() not in peers:
            self.peer_var.set(peers[0])

    def _on_execute(self):
        sql = self.textbox.get("0.0", "end").strip()
        peer_id = self.peer_var.get()
        if sql and peer_id:
            # Handle multiple statements separated by semicolon (naively)
            stmts = [s.strip() for s in sql.split(";") if s.strip()]
            for stmt in stmts:
                self.execute_callback(peer_id, stmt)

    def _on_preset_select(self, choice):
        if choice != "Load Preset...":
            self.preset_callback(choice)
            self.preset_menu.set("Load Preset...")
