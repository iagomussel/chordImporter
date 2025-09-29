"""
Smart Guitar Tuner that automatically selects the best available implementation.
Tries modern tuner first, falls back to basic tuner if dependencies are missing.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional

def show_tuner_window(parent=None):
    """Show the best available tuner window."""
    
    # Try to use the modern tuner first
    try:
        from .tuner_new import TunerWindow as ModernTunerWindow
        print("Using modern tuner with sounddevice")
        return ModernTunerWindow(parent)
    except ImportError as e:
        print(f"Modern tuner not available: {e}")
        
        # Fall back to the advanced tuner
        try:
            from .tuner_advanced import TunerWindow as AdvancedTunerWindow
            print("Using advanced tuner with PyAudio")
            return AdvancedTunerWindow(parent)
        except ImportError as e:
            print(f"Advanced tuner not available: {e}")
            
            # Fall back to the basic fallback tuner
            try:
                from .tuner_fallback import TunerWindow as FallbackTunerWindow
                print("Using fallback tuner (visual only)")
                return FallbackTunerWindow(parent)
            except ImportError as e:
                print(f"Fallback tuner not available: {e}")
                
                # If all else fails, show an error
                if parent:
                    messagebox.showerror(
                        "Tuner Error",
                        "No tuner implementation is available.\n\n"
                        "This may be due to missing audio libraries.\n"
                        "Please check your installation."
                    )
                else:
                    print("ERROR: No tuner implementation available!")
                
                return None


class TunerWindow:
    """Smart tuner window that uses the best available implementation."""
    
    def __init__(self, parent: Optional[tk.Widget] = None):
        self.actual_tuner = show_tuner_window(parent)
        
        if self.actual_tuner:
            # Delegate all attributes to the actual tuner
            self.window = self.actual_tuner.window
            self.tuner = getattr(self.actual_tuner, 'tuner', None)
        else:
            # Create a minimal error window
            if parent:
                self.window = tk.Toplevel(parent)
                self.window.transient(parent)
            else:
                self.window = tk.Tk()
            
            self.window.title("🎸 Tuner Error")
            self.window.geometry("400x200")
            self.window.configure(bg="#f0f0f0")
            
            error_label = tk.Label(
                self.window,
                text="Tuner Not Available\n\nAudio libraries are missing.\nPlease install sounddevice or pyaudio.",
                font=("Arial", 12),
                bg="#f0f0f0",
                fg="#f44336",
                justify=tk.CENTER
            )
            error_label.pack(expand=True)
            
            self.tuner = None
    
    def on_close(self):
        """Handle window close event."""
        if self.actual_tuner and hasattr(self.actual_tuner, 'on_close'):
            self.actual_tuner.on_close()
        else:
            self.window.destroy()
    
    def show(self):
        """Show the tuner window."""
        if self.actual_tuner and hasattr(self.actual_tuner, 'show'):
            self.actual_tuner.show()
        else:
            self.window.lift()
            self.window.focus_force()


if __name__ == "__main__":
    # Test the smart tuner
    root = tk.Tk()
    root.withdraw()  # Hide root window
    tuner_window = TunerWindow()
    if tuner_window.window:
        root.mainloop()
