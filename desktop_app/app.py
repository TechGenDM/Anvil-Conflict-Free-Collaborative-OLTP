import customtkinter as ctk
from theme import *
from components.sidebar import Sidebar
from views.demo_view import DemoView
from views.benchmark_view import BenchmarkView
from views.about_view import AboutView
from engine_bridge import EngineBridge

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window Setup
        self.title("Anvil — Conflict-Free Collaborative OLTP")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.configure(fg_color=BG_PRIMARY)
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Grid Layout (1 row, 2 columns)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # Sidebar is fixed
        self.grid_columnconfigure(1, weight=1)  # Main content expands
        
        # Engine Bridge initialization
        self.bridge = EngineBridge()
        self.bridge.create_peer("A")
        self.bridge.create_peer("B")
        self.bridge.create_peer("C")
        
        # Create Sidebar
        self.sidebar = Sidebar(self, navigate_callback=self.navigate_to)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Main Content Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Initialize Views
        self.views = {
            "demo": DemoView(self.main_container, self.bridge),
            "benchmark": BenchmarkView(self.main_container, self.bridge),
            "about": AboutView(self.main_container, self.bridge)
        }
        
        self.current_view = None
        self.navigate_to("demo")

    def navigate_to(self, view_name):
        """Switch the main content view."""
        if self.current_view:
            self.current_view.grid_forget()
            
        view = self.views.get(view_name)
        if view:
            view.grid(row=0, column=0, sticky="nsew")
            self.current_view = view
            
            # If switching to demo, refresh it to catch any background engine changes
            if view_name == "demo":
                view.refresh()
