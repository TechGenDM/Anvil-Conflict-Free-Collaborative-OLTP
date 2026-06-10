import sys
import os
import customtkinter as ctk

# Ensure we can import the engine and our own modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import App
from theme import BG_PRIMARY

def main():
    # Configure CustomTkinter appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")  # Using built-in blue, but overriding with our theme.py
    
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
