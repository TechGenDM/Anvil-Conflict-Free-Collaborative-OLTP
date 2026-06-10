import customtkinter as ctk
from theme import *
from components.vector_clock_badge import VectorClockBadge

class StateTable(ctk.CTkFrame):
    def __init__(self, master, table_name, table_data, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Table Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, PAD_XS))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=f"Table: {table_name}",
            font=ctk.CTkFont(family=FONT_HEADING, size=SIZE_H3, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.title_label.pack(side="left")
        
        # Schema info (if available)
        schema = table_data.get("schema", {})
        if schema:
            unique = schema.get("unique_cols", [])
            fks = list(schema.get("fk_cols", {}).keys())
            meta_text = []
            if unique: meta_text.append(f"UNIQUE({','.join(unique)})")
            if fks: meta_text.append(f"FK({','.join(fks)})")
            
            if meta_text:
                self.meta_label = ctk.CTkLabel(
                    self.header_frame,
                    text=" | ".join(meta_text),
                    font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY),
                    text_color=TEXT_MUTED
                )
                self.meta_label.pack(side="right")

        # Container for rows
        self.rows_frame = ctk.CTkFrame(
            self, 
            fg_color=BG_TERTIARY,
            corner_radius=CORNER_RADIUS_SM,
            border_width=1,
            border_color=BORDER
        )
        self.rows_frame.pack(fill="x")
        
        rows = table_data.get("rows", [])
        if not rows:
            self._add_empty_message()
            return
            
        # Determine columns from the first row's cells + PK
        if rows:
            cols = ["PK"] + list(rows[0]["cells"].keys())
            self._add_row_headers(cols)
            
            for i, row in enumerate(rows):
                self._add_data_row(row, cols, is_last=(i == len(rows)-1))

    def _add_empty_message(self):
        msg = ctk.CTkLabel(
            self.rows_frame,
            text="(empty)",
            font=ctk.CTkFont(family=FONT_BODY, size=SIZE_SMALL, slant="italic"),
            text_color=TEXT_MUTED,
            pady=PAD_SM
        )
        msg.pack()

    def _add_row_headers(self, cols):
        header = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
        header.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, PAD_XS))
        
        for i, col in enumerate(cols):
            weight = 1 if i == 0 else 2  # PK gets less space
            header.grid_columnconfigure(i, weight=weight)
            
            lbl = ctk.CTkLabel(
                header,
                text=col.upper(),
                font=ctk.CTkFont(family=FONT_MONO, size=SIZE_TINY, weight="bold"),
                text_color=TEXT_MUTED,
                anchor="w"
            )
            lbl.grid(row=0, column=i, sticky="w")
            
        # Separator line
        sep = ctk.CTkFrame(self.rows_frame, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=PAD_XS)

    def _add_data_row(self, row, cols, is_last=False):
        row_frame = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=PAD_SM, pady=PAD_XS)
        
        # Determine row status coloring
        fg_color = "transparent"
        text_color = TEXT_PRIMARY
        status_text = ""
        
        if row["tombstone"]:
            fg_color = DANGER_DIM
            text_color = DANGER
            status_text = "[DEL]"
        elif not row["visible"]:
            if row["fk_status"] == "orphaned":
                fg_color = WARNING_DIM
                text_color = WARNING
                status_text = "[ORPHAN]"
            elif row["unique_status"] == "rejected":
                fg_color = DANGER_DIM
                text_color = DANGER
                status_text = "[DUP_REJ]"
                
        if fg_color != "transparent":
            row_frame.configure(fg_color=fg_color, corner_radius=CORNER_RADIUS_SM)

        for i, col in enumerate(cols):
            weight = 1 if i == 0 else 2
            row_frame.grid_columnconfigure(i, weight=weight)
            
            if col == "PK":
                val = str(row["pk"])
                if status_text:
                    val = f"{status_text} {val}"
            else:
                cell = row["cells"].get(col, {})
                val = str(cell.get("value", "NULL"))
                
            lbl = ctk.CTkLabel(
                row_frame,
                text=val,
                font=ctk.CTkFont(family=FONT_MONO, size=SIZE_SMALL),
                text_color=text_color,
                anchor="w"
            )
            lbl.grid(row=0, column=i, sticky="w", pady=2)
            
        if not is_last:
            sep = ctk.CTkFrame(self.rows_frame, fg_color=BORDER, height=1)
            sep.pack(fill="x", padx=PAD_XS)
