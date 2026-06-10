import customtkinter as ctk
from theme import *
from components.peer_card import PeerCard
from components.sql_input import SqlInput
from components.sync_controls import SyncControls

class DemoView(ctk.CTkFrame):
    def __init__(self, master, bridge, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.bridge = bridge
        
        # Grid config: 0=Header, 1=Controls, 2=Cards, 3=Log
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=3) # Cards area expands
        self.grid_rowconfigure(3, weight=1) # Log area expands
        
        self._build_header()
        self._build_controls()
        self._build_cards_area()
        self._build_log_area()
        
        # Initial refresh
        self.refresh()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_XL, pady=(PAD_XL, PAD_MD))
        
        title = ctk.CTkLabel(
            header,
            text="Interactive Playground",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_TITLE, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        title.pack(side="left")
        
        reset_btn = ctk.CTkButton(
            header,
            text="Reset All",
            fg_color="transparent",
            border_width=1,
            border_color=DANGER,
            text_color=DANGER,
            hover_color=DANGER_DIM,
            width=80,
            command=self._on_reset
        )
        reset_btn.pack(side="right")

    def _build_controls(self):
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=1, column=0, sticky="ew", padx=PAD_XL, pady=(0, PAD_LG))
        ctrl_frame.grid_columnconfigure(0, weight=2)
        ctrl_frame.grid_columnconfigure(1, weight=1)
        
        self.sql_input = SqlInput(
            ctrl_frame,
            peers=self.bridge.get_peer_ids(),
            execute_callback=self._on_execute,
            preset_callback=self._on_preset
        )
        self.sql_input.grid(row=0, column=0, sticky="nsew", padx=(0, PAD_MD))
        
        self.sync_ctrls = SyncControls(
            ctrl_frame,
            peers=self.bridge.get_peer_ids(),
            sync_callback=self._on_sync,
            sync_all_callback=self._on_sync_all
        )
        self.sync_ctrls.grid(row=0, column=1, sticky="nsew")

    def _build_cards_area(self):
        self.cards_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            orientation="horizontal"
        )
        self.cards_scroll.grid(row=2, column=0, sticky="nsew", padx=PAD_XL)
        # We will add cards to this dynamically in refresh()

    def _build_log_area(self):
        log_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=CORNER_RADIUS)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_XL)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        lbl = ctk.CTkLabel(
            log_frame,
            text="Event Log",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H3, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        lbl.grid(row=0, column=0, sticky="w", padx=PAD_LG, pady=(PAD_SM, 0))
        
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
            fg_color="transparent",
            text_color=TEXT_MUTED,
            state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=PAD_SM, pady=PAD_SM)

    # ── Actions ──────────────────────────────────────────────────

    def refresh(self):
        """Update the entire view from the bridge state."""
        peers = self.bridge.get_peer_ids()
        
        # 1. Update SQL Input choices
        self.sql_input.update_peers(peers)
        
        # 2. Update Sync Controls
        self.sync_ctrls.update_state(peers, self.bridge.are_all_synced())
        
        # 3. Rebuild Peer Cards
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()
            
        for peer_id in peers:
            data = self.bridge.get_peer_detail(peer_id)
            card = PeerCard(self.cards_scroll, peer_id, data, width=380)
            card.pack(side="left", fill="y", padx=(0, PAD_LG))
            
        # 4. Update Log
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        
        for entry in self.bridge.event_log:
            time = entry["time"]
            act = entry["action"]
            det = entry["detail"]
            line = f"[{time}] {act.ljust(12)} {det}\n"
            self.log_textbox.insert("end", line)
            
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def _on_execute(self, peer_id, sql):
        self.bridge.execute_sql(peer_id, sql)
        self.refresh()

    def _on_sync(self, peer_a, peer_b):
        self.bridge.sync_peers(peer_a, peer_b)
        self.refresh()

    def _on_sync_all(self):
        self.bridge.sync_all()
        self.refresh()

    def _on_preset(self, preset_name):
        scenarios = self.bridge.get_preset_scenarios()
        if preset_name not in scenarios:
            return
            
        self._on_reset()
        
        # Ensure peers exist for the scenario (A, B, C)
        self.bridge.create_peer("A")
        self.bridge.create_peer("B")
        self.bridge.create_peer("C")
        
        steps = scenarios[preset_name]
        
        # Execute steps automatically (we could do this with animation/delay, 
        # but for now we'll execute them all at once and update the log)
        for step in steps:
            if step["type"] in ("schema", "execute"):
                peer = step.get("peer", "A") # Default to A for schema
                sql = step["sql"]
                params = step.get("params", ())
                self.bridge.execute_sql(peer, sql, params)
            elif step["type"] == "sync":
                ps = step["peers"]
                self.bridge.sync_peers(ps[0], ps[1])
            elif step["type"] == "sync_all":
                self.bridge.sync_all()
                
            if "note" in step:
                self.bridge._log("NOTE", step["note"])
                
        self.refresh()

    def _on_reset(self):
        self.bridge.reset()
        self.bridge.create_peer("A")
        self.bridge.create_peer("B")
        self.bridge.create_peer("C")
        self.refresh()
