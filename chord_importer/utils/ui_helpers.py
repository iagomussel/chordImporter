"""
UI helper utilities to eliminate duplicated UI code.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, Tuple
import threading


class UIHelpers:
    """Collection of UI helper methods to reduce code duplication."""
    
    @staticmethod
    def center_window(window: tk.Tk, width: int, height: int) -> None:
        """
        Center a window on the screen.
        
        Args:
            window: The window to center
            width: Window width
            height: Window height
        """
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    @staticmethod
    def create_styled_button(parent: tk.Widget, text: str, command: Callable, 
                           bg_color: str = "#4CAF50", hover_color: str = "#45a049",
                           text_color: str = "white", **kwargs) -> tk.Button:
        """
        Create a styled button with hover effects.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Button command
            bg_color: Background color
            hover_color: Hover color
            text_color: Text color
            **kwargs: Additional button options
            
        Returns:
            Configured button widget
        """
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=text_color,
            relief="flat",
            cursor="hand2",
            **kwargs
        )
        
        def on_enter(e):
            button.config(bg=hover_color)
            
        def on_leave(e):
            button.config(bg=bg_color)
            
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        return button
    
    @staticmethod
    def create_tool_card(parent: tk.Widget, title: str, description: str, 
                        command: Callable, icon: str = "🎵") -> tk.Frame:
        """
        Create a tool card widget.
        
        Args:
            parent: Parent widget
            title: Card title
            description: Card description
            command: Click command
            icon: Card icon
            
        Returns:
            Tool card frame
        """
        card = tk.Frame(parent, bg="white", relief="raised", bd=2)
        card.bind("<Button-1>", lambda e: command())
        
        # Icon
        icon_label = tk.Label(card, text=icon, font=("Arial", 24), bg="white")
        icon_label.pack(pady=(10, 5))
        icon_label.bind("<Button-1>", lambda e: command())
        
        # Title
        title_label = tk.Label(card, text=title, font=("Arial", 12, "bold"), bg="white")
        title_label.pack(pady=(0, 5))
        title_label.bind("<Button-1>", lambda e: command())
        
        # Description
        desc_label = tk.Label(card, text=description, font=("Arial", 9), 
                             bg="white", wraplength=150, justify="center")
        desc_label.pack(pady=(0, 10), padx=10)
        desc_label.bind("<Button-1>", lambda e: command())
        
        # Hover effects
        def on_enter(e):
            card.config(bg="#f0f0f0")
            for child in card.winfo_children():
                child.config(bg="#f0f0f0")
                
        def on_leave(e):
            card.config(bg="white")
            for child in card.winfo_children():
                child.config(bg="white")
                
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        for child in card.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
        
        return card
    
    @staticmethod
    def create_status_bar(parent: tk.Widget) -> tk.Label:
        """
        Create a status bar widget.
        
        Args:
            parent: Parent widget
            
        Returns:
            Status bar label
        """
        status_bar = tk.Label(
            parent,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#f0f0f0",
            font=("Arial", 9)
        )
        return status_bar
    
    @staticmethod
    def show_error(title: str, message: str) -> None:
        """Show error message dialog."""
        messagebox.showerror(title, message)
    
    @staticmethod
    def show_info(title: str, message: str) -> None:
        """Show info message dialog."""
        messagebox.showinfo(title, message)
    
    @staticmethod
    def show_warning(title: str, message: str) -> None:
        """Show warning message dialog."""
        messagebox.showwarning(title, message)
    
    @staticmethod
    def ask_yes_no(title: str, message: str) -> bool:
        """Ask yes/no question."""
        return messagebox.askyesno(title, message)
    
    @staticmethod
    def create_progress_dialog(parent: tk.Widget, title: str) -> Tuple[tk.Toplevel, ttk.Progressbar, tk.Label]:
        """
        Create a progress dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            
        Returns:
            Tuple of (dialog, progressbar, status_label)
        """
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()
        
        UIHelpers.center_window(dialog, 300, 100)
        
        # Progress bar
        progress = ttk.Progressbar(dialog, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill=tk.X)
        progress.start()
        
        # Status label
        status_label = tk.Label(dialog, text="Processing...")
        status_label.pack(pady=5)
        
        return dialog, progress, status_label
    
    @staticmethod
    def run_in_thread(func: Callable, callback: Optional[Callable] = None) -> threading.Thread:
        """
        Run a function in a separate thread.
        
        Args:
            func: Function to run
            callback: Optional callback when done
            
        Returns:
            Thread object
        """
        def wrapper():
            try:
                result = func()
                if callback:
                    callback(result)
            except Exception as e:
                if callback:
                    callback(None, str(e))
        
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread
    
    @staticmethod
    def create_scrollable_frame(parent: tk.Widget) -> Tuple[tk.Canvas, tk.Frame]:
        """
        Create a scrollable frame.
        
        Args:
            parent: Parent widget
            
        Returns:
            Tuple of (canvas, scrollable_frame)
        """
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        return canvas, scrollable_frame
    
    @staticmethod
    def bind_mousewheel(canvas: tk.Canvas) -> None:
        """Bind mousewheel scrolling to canvas."""
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    @staticmethod
    def create_labeled_entry(parent: tk.Widget, label_text: str, 
                           entry_width: int = 20, **kwargs) -> Tuple[tk.Label, tk.Entry]:
        """
        Create a labeled entry widget.
        
        Args:
            parent: Parent widget
            label_text: Label text
            entry_width: Entry width
            **kwargs: Additional entry options
            
        Returns:
            Tuple of (label, entry)
        """
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        label = tk.Label(frame, text=label_text)
        label.pack(side=tk.LEFT)
        
        entry = tk.Entry(frame, width=entry_width, **kwargs)
        entry.pack(side=tk.RIGHT)
        
        return label, entry
