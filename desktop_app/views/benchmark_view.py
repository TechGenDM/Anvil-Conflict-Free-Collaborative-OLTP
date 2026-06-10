import customtkinter as ctk
import os
from theme import *
from components.score_card import ScoreCard
from components.scenario_row import ScenarioRow

class BenchmarkView(ctk.CTkFrame):
    def __init__(self, master, bridge, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.bridge = bridge
        self.report_data = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Table area expands
        
        self._build_header()
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=PAD_XL, pady=PAD_LG)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self._load_report()
        
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_XL, pady=(PAD_XL, 0))
        
        title = ctk.CTkLabel(
            header,
            text="L3 Benchmark Results",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_TITLE, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        title.pack(side="left")

    def _load_report(self):
        reports = self.bridge.find_benchmark_reports()
        if not reports:
            self._render_empty("No benchmark reports found in bench-p01-crdt/")
            return
            
        # Load the latest one
        self.report_data = self.bridge.load_benchmark_report(reports[-1])
        if not self.report_data:
            self._render_empty("Failed to parse benchmark report.")
            return
            
        self._render_dashboard()

    def _render_empty(self, msg):
        lbl = ctk.CTkLabel(
            self.content_frame,
            text=msg,
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_H2),
            text_color=TEXT_MUTED
        )
        lbl.pack(pady=PAD_XXL)

    def _render_dashboard(self):
        # Clear existing
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        scores = self.report_data.get("scores", {})
        total_score = scores.get("total", 0.0)
        core_score = scores.get("core_score", 0.0)
        stretch_score = scores.get("stretch_score", 0.0)
        
        # ── Score Cards Row ──
        scores_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        scores_frame.pack(fill="x", pady=(0, PAD_XL))
        scores_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ScoreCard(scores_frame, "FINAL SCORE", total_score, color=ACCENT).grid(row=0, column=0, sticky="ew", padx=(0, PAD_MD))
        ScoreCard(scores_frame, "CORE AXES", core_score, color=SUCCESS).grid(row=0, column=1, sticky="ew", padx=PAD_MD)
        ScoreCard(scores_frame, "STRETCH AXES", stretch_score, color=WARNING).grid(row=0, column=2, sticky="ew", padx=(PAD_MD, 0))
        
        # ── Meta Info ──
        meta = self.report_data.get("metadata", {})
        meta_frame = ctk.CTkFrame(self.content_frame, fg_color=BG_SECONDARY, corner_radius=CORNER_RADIUS)
        meta_frame.pack(fill="x", pady=(0, PAD_XL))
        
        meta_text = f"Adapter: {meta.get('adapter', 'N/A')}  |  Timestamp: {meta.get('timestamp', 'N/A')}  |  Track: {meta.get('track', 'N/A')}"
        ctk.CTkLabel(
            meta_frame,
            text=meta_text,
            font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
            text_color=TEXT_MUTED
        ).pack(pady=PAD_SM)
        
        # ── Scenarios Table ──
        scenarios = self.report_data.get("scenarios", {})
        if not scenarios:
            return
            
        table_frame = ctk.CTkFrame(self.content_frame, fg_color=BG_CARD, border_width=1, border_color=BORDER)
        table_frame.pack(fill="both", expand=True)
        
        # Table Header
        th = ctk.CTkFrame(table_frame, fg_color=BG_TERTIARY, corner_radius=0)
        th.pack(fill="x")
        th.grid_columnconfigure(0, weight=3)
        th.grid_columnconfigure(1, weight=1)
        th.grid_columnconfigure(2, weight=1)
        th.grid_columnconfigure(3, weight=1)
        
        cols = ["Scenario", "Duration", "Hash Match", "Result"]
        for i, col in enumerate(cols):
            anchor = "w" if i == 0 else "e"
            pad = PAD_LG if i in (0, 3) else PAD_MD
            lbl = ctk.CTkLabel(
                th, text=col.upper(),
                font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY, weight="bold"),
                text_color=TEXT_MUTED
            )
            lbl.grid(row=0, column=i, sticky=anchor, padx=pad, pady=PAD_SM)
            
        # Rows
        scroll = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        for i, scenario_data in enumerate(scenarios):
            name = scenario_data.get("scenario", f"Scenario {i}")
            # Determine overall pass
            passed = all(a.get("passed", False) for a in scenario_data.get("assertions", []))
            scenario_data["pass"] = passed
            
            # Extract hash match (it's implicit in convergence assertion, or we check snapshot_hashes)
            hashes = list(scenario_data.get("snapshot_hashes", {}).values())
            scenario_data["hash_match"] = len(set(hashes)) == 1 if hashes else False
            
            row = ScenarioRow(scroll, name, scenario_data, is_odd=(i%2 != 0))
            row.pack(fill="x")
