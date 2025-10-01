"""
Musical Tools Suite - Main Dashboard
Modern UI/UX interface for the Musical Tools Suite
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from typing import Dict, List, Optional, Any
import os
from datetime import datetime

try:
    from .database import get_database
    from .settings import get_settings
    from .tuner import TunerWindow
    from .cipher_manager import show_cipher_manager
    from .settings_window import show_settings_window
    from .chord_identifier import show_chord_identifier
    from .music_visualizer import show_music_visualizer
    from .melody_analyzer import show_melody_analyzer
    from .advanced_melody_analyzer import show_advanced_melody_analyzer
    from .karaoke_analyzer import show_karaoke_analyzer
    from .serper import SearchResult, search_cifraclub, search_filetype, search_query, search_chord_sequence, search_chord_sequence_dynamic, search_all_sources_with_dorks
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings
    from chord_importer.tuner import TunerWindow
    from chord_importer.cipher_manager import show_cipher_manager
    from chord_importer.settings_window import show_settings_window
    from chord_importer.chord_identifier import show_chord_identifier
    from chord_importer.music_visualizer import show_music_visualizer
    from chord_importer.melody_analyzer import show_melody_analyzer
    from chord_importer.advanced_melody_analyzer import show_advanced_melody_analyzer
    from chord_importer.karaoke_analyzer import show_karaoke_analyzer
    from chord_importer.serper import SearchResult, search_cifraclub, search_filetype, search_query, search_chord_sequence, search_chord_sequence_dynamic, search_all_sources_with_dorks


class ToolCard(tk.Frame):
    """A modern card widget for tool buttons."""
    
    def __init__(self, parent, title, description, icon, command, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = command
        
        # Configure card styling
        self.configure(
            relief="raised",
            borderwidth=1,
            bg="#ffffff",
            padx=15,
            pady=15
        )
        
        # Icon and title frame
        header_frame = tk.Frame(self, bg="#ffffff")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Icon
        icon_label = tk.Label(
            header_frame,
            text=icon,
            font=("Arial", 24),
            bg="#ffffff",
            fg="#2196F3"
        )
        icon_label.pack(side=tk.LEFT)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text=title,
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Description
        desc_label = tk.Label(
            self,
            text=description,
            font=("Arial", 10),
            bg="#ffffff",
            fg="#666666",
            wraplength=200,
            justify=tk.LEFT
        )
        desc_label.pack(fill=tk.X, pady=(0, 10))
        
        # Action button with better styling
        button_frame = tk.Frame(self, bg="#ffffff")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.action_btn = tk.Button(
            button_frame,
            text="Abrir",
            command=self.on_click,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            activebackground="#1976D2",
            activeforeground="white",
            highlightthickness=0,
            disabledforeground="white"
        )
        
        # Force the button to use our colors (Windows compatibility)
        self.action_btn.configure(state="normal")
        self.action_btn.pack(anchor=tk.W)
        
        # Add button hover effects
        self.bind_button_hover_effects()
        
        # Hover effects
        self.bind_hover_effects()
    
    def bind_button_hover_effects(self):
        """Add hover effects specifically for the action button."""
        def on_button_enter(event):
            self.action_btn.configure(bg="#1976D2", relief="raised", bd=1, fg="white")
            # Force update
            self.action_btn.update()
        
        def on_button_leave(event):
            self.action_btn.configure(bg="#2196F3", relief="flat", bd=0, fg="white")
            self.action_btn.update()
        
        def on_button_press(event):
            self.action_btn.configure(bg="#0D47A1", relief="sunken", bd=1, fg="white")
            self.action_btn.update()
        
        def on_button_release(event):
            self.action_btn.configure(bg="#1976D2", relief="raised", bd=1, fg="white")
            self.action_btn.update()
        
        self.action_btn.bind("<Enter>", on_button_enter)
        self.action_btn.bind("<Leave>", on_button_leave)
        self.action_btn.bind("<Button-1>", on_button_press)
        self.action_btn.bind("<ButtonRelease-1>", on_button_release)
    
    def bind_hover_effects(self):
        """Add hover effects to the card."""
        def on_enter(event):
            self.configure(bg="#f8f9fa", relief="raised", borderwidth=2)
            for child in self.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg="#f8f9fa")
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.configure(bg="#f8f9fa")
                elif isinstance(child, tk.Label):
                    child.configure(bg="#f8f9fa")
        
        def on_leave(event):
            self.configure(bg="#ffffff", relief="raised", borderwidth=1)
            for child in self.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg="#ffffff")
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.configure(bg="#ffffff")
                elif isinstance(child, tk.Label):
                    child.configure(bg="#ffffff")
        
        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)
        
        # Bind to all children as well
        for child in self.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            if isinstance(child, tk.Frame):
                for subchild in child.winfo_children():
                    subchild.bind("<Enter>", on_enter)
                    subchild.bind("<Leave>", on_leave)
    
    def on_click(self):
        """Handle card click."""
        if self.command:
            self.command()


class StatusBar(tk.Frame):
    """Modern status bar with indicators."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg="#f5f5f5", relief="sunken", borderwidth=1)
        
        # Status text
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            self,
            textvariable=self.status_var,
            bg="#f5f5f5",
            fg="#333333",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Separator
        separator = tk.Frame(self, width=1, bg="#cccccc")
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Audio status
        self.audio_var = tk.StringVar(value="Audio: Ready")
        self.audio_label = tk.Label(
            self,
            textvariable=self.audio_var,
            bg="#f5f5f5",
            fg="#666666",
            font=("Arial", 9)
        )
        self.audio_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Database status
        self.db_var = tk.StringVar(value="Database: Connected")
        self.db_label = tk.Label(
            self,
            textvariable=self.db_var,
            bg="#f5f5f5",
            fg="#666666",
            font=("Arial", 9)
        )
        self.db_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Time
        self.time_var = tk.StringVar()
        self.time_label = tk.Label(
            self,
            textvariable=self.time_var,
            bg="#f5f5f5",
            fg="#666666",
            font=("Arial", 9)
        )
        self.time_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.update_time()
    
    def update_time(self):
        """Update the time display."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_var.set(current_time)
        self.after(1000, self.update_time)
    
    def set_status(self, message: str):
        """Set the status message."""
        self.status_var.set(message)
    
    def set_audio_status(self, status: str):
        """Set the audio status."""
        self.audio_var.set(f"Audio: {status}")
    
    def set_db_status(self, status: str):
        """Set the database status."""
        self.db_var.set(f"Database: {status}")


class QuickSearchFrame(tk.Frame):
    """Modern quick search interface."""
    
    def __init__(self, parent, search_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.search_callback = search_callback
        self.configure(bg="#ffffff", relief="raised", borderwidth=1)
        
        # Title
        title_label = tk.Label(
            self,
            text="Quick Search",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        title_label.pack(pady=(15, 10))
        
        # Search frame
        search_frame = tk.Frame(self, bg="#ffffff")
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("Arial", 11),
            relief="solid",
            borderwidth=1,
            bg="#f8f9fa"
        )
        self.search_entry.pack(fill=tk.X, pady=(0, 10))
        self.search_entry.bind("<Return>", self.on_search)
        self.search_entry.bind("<KeyRelease>", self.on_key_release)
        
        # Source selection
        source_frame = tk.Frame(search_frame, bg="#ffffff")
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(source_frame, text="Fonte:", font=("Arial", 9), bg="#ffffff").pack(side=tk.LEFT)
        
        self.source_var = tk.StringVar(value="Todas as Fontes")
        self.source_combo = ttk.Combobox(
            source_frame,
            textvariable=self.source_var,
            state="readonly",
            font=("Arial", 9),
            width=20
        )
        self.source_combo.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Load sources
        self.load_sources()
        
        # Bind source selection to show dorks
        self.source_combo.bind('<<ComboboxSelected>>', self.on_source_changed)
        
        # Dorks info frame
        self.dorks_frame = tk.LabelFrame(
            search_frame,
            text="Dorks Disponíveis",
            bg="#ffffff",
            fg="#666666",
            font=("Arial", 8)
        )
        self.dorks_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.dorks_label = tk.Label(
            self.dorks_frame,
            text="Selecione uma fonte para ver os dorks disponíveis",
            font=("Arial", 8),
            bg="#ffffff",
            fg="#888888",
            wraplength=250,
            justify=tk.LEFT
        )
        self.dorks_label.pack(padx=5, pady=3)
        
        # Search button
        self.search_btn = tk.Button(
            search_frame,
            text="Search",
            command=self.on_search,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        self.search_btn.pack(fill=tk.X)
        
        # Recent searches
        recent_frame = tk.LabelFrame(
            self,
            text="Recent Searches",
            bg="#ffffff",
            fg="#666666",
            font=("Arial", 9)
        )
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.recent_listbox = tk.Listbox(
            recent_frame,
            height=4,
            font=("Arial", 9),
            bg="#f8f9fa",
            relief="flat",
            borderwidth=0
        )
        self.recent_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.recent_listbox.bind("<Double-Button-1>", self.on_recent_select)
        
        self.load_recent_searches()
    
    def load_sources(self):
        """Load available sources for selection."""
        try:
            from .source_configs import get_source_manager
        except ImportError:
            from chord_importer.source_configs import get_source_manager
        
        try:
            source_manager = get_source_manager()
            sources = source_manager.list_sources()
            
            # Create source options
            source_options = ["Todas as Fontes"]
            self.source_mapping = {"Todas as Fontes": None}
            
            for source_id, source_name in sources.items():
                display_name = f"{source_name}"
                source_options.append(display_name)
                self.source_mapping[display_name] = source_id
            
            self.source_combo['values'] = source_options
            
        except Exception as e:
            print(f"Error loading sources: {e}")
            self.source_combo['values'] = ["Todas as Fontes"]
            self.source_mapping = {"Todas as Fontes": None}
    
    def on_source_changed(self, event=None):
        """Handle source selection change."""
        selected_source = self.source_var.get()
        source_id = self.source_mapping.get(selected_source)
        
        if not source_id:
            self.dorks_label.config(text="Usando dorks de todas as fontes disponíveis")
            return
        
        try:
            from .source_configs import get_source_manager
        except ImportError:
            from chord_importer.source_configs import get_source_manager
        
        try:
            source_manager = get_source_manager()
            config = source_manager.get_source(source_id)
            
            if config and config.search_dorks:
                enabled_dorks = config.get_enabled_dorks()
                if enabled_dorks:
                    dork_info = f"Dorks ativos ({len(enabled_dorks)}):\n"
                    for i, dork in enumerate(enabled_dorks[:3], 1):  # Show first 3
                        dork_info += f"{i}. {dork.name} (prioridade: {dork.priority})\n"
                    
                    if len(enabled_dorks) > 3:
                        dork_info += f"... e mais {len(enabled_dorks) - 3} dorks"
                    
                    self.dorks_label.config(text=dork_info.strip())
                else:
                    self.dorks_label.config(text="Nenhum dork ativo para esta fonte")
            else:
                self.dorks_label.config(text="Nenhum dork configurado para esta fonte")
                
        except Exception as e:
            self.dorks_label.config(text=f"Erro ao carregar dorks: {str(e)}")
    
    def on_search(self, event=None):
        """Handle search."""
        query = self.search_var.get().strip()
        if query:
            # Get selected source
            selected_source = self.source_var.get()
            source_id = self.source_mapping.get(selected_source)
            
            # Pass both query and source_id to callback
            self.search_callback(query, source_id)
            self.add_to_recent(query)
    
    def on_key_release(self, event):
        """Handle key release for real-time search suggestions."""
        # Could implement auto-complete here
        pass
    
    def on_recent_select(self, event):
        """Handle recent search selection."""
        selection = self.recent_listbox.curselection()
        if selection:
            query = self.recent_listbox.get(selection[0])
            self.search_var.set(query)
            self.on_search()
    
    def load_recent_searches(self):
        """Load recent searches from database."""
        try:
            db = get_database()
            history = db.get_search_history(limit=100)
            for item in history:
                self.recent_listbox.insert(tk.END, item['query'])
        except Exception:
            pass
    
    def add_to_recent(self, query: str):
        """Add query to recent searches."""
        # Add to top of list
        self.recent_listbox.insert(0, query)
        # Remove duplicates
        items = list(self.recent_listbox.get(0, tk.END))
        unique_items = []
        for item in items:
            if item not in unique_items:
                unique_items.append(item)
        
        self.recent_listbox.delete(0, tk.END)
        for item in unique_items[:50]:  # Keep only 50 recent
            self.recent_listbox.insert(tk.END, item)


class MusicalToolsDashboard(tk.Tk):
    """Main dashboard for the Musical Tools Suite."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize
        self.db = get_database()
        self.settings = get_settings()
        
        # Configure main window
        self.title("Musical Tools Suite")
        self.geometry("1200x800")
        self.minsize(1000, 600)
        self.configure(bg="#f0f0f0")
        
        # Set window icon (if available)
        try:
            # You can add an icon file here
            pass
        except Exception:
            pass
        
        # Initialize components
        self.setup_styles()
        self.create_header()
        self.create_main_content()
        self.create_status_bar()
        
        # Initialize data
        self.load_dashboard_data()
        
        # Center window
        self.center_window()
    
    def setup_styles(self):
        """Setup custom styles for ttk widgets."""
        style = ttk.Style()
        
        # Configure notebook style
        style.configure(
            "Dashboard.TNotebook",
            background="#f0f0f0",
            borderwidth=0
        )
        style.configure(
            "Dashboard.TNotebook.Tab",
            padding=[20, 10],
            font=("Arial", 11)
        )
    
    def center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _add_button_hover_effects(self, button, primary_color="#2196F3", hover_color="#1976D2", pressed_color="#0D47A1"):
        """Add hover effects to a button."""
        def on_enter(event):
            button.configure(bg=hover_color, relief="raised", bd=1, fg="white")
            button.update()
        
        def on_leave(event):
            button.configure(bg=primary_color, relief="flat", bd=0, fg="white")
            button.update()
        
        def on_press(event):
            button.configure(bg=pressed_color, relief="sunken", bd=1, fg="white")
            button.update()
        
        def on_release(event):
            button.configure(bg=hover_color, relief="raised", bd=1, fg="white")
            button.update()
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        button.bind("<Button-1>", on_press)
        button.bind("<ButtonRelease-1>", on_release)
    
    def create_header(self):
        """Create the header section."""
        header_frame = tk.Frame(self, bg="#2196F3", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title and subtitle
        title_frame = tk.Frame(header_frame, bg="#2196F3")
        title_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        title_label = tk.Label(
            title_frame,
            text="Musical Tools Suite",
            font=("Arial", 20, "bold"),
            bg="#2196F3",
            fg="white"
        )
        title_label.pack(anchor=tk.W, pady=(15, 0))
        
        subtitle_label = tk.Label(
            title_frame,
            text="Your complete musical workstation",
            font=("Arial", 11),
            bg="#2196F3",
            fg="#E3F2FD"
        )
        subtitle_label.pack(anchor=tk.W)
        
        # Header buttons
        header_buttons = tk.Frame(header_frame, bg="#2196F3")
        header_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=20)
        
        # Settings button
        settings_btn = tk.Button(
            header_buttons,
            text="Settings",
            command=self.open_settings,
            bg="#1976D2",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        )
        settings_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=20)
        
        # Help button
        help_btn = tk.Button(
            header_buttons,
            text="Help",
            command=self.show_help,
            bg="#1976D2",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        )
        help_btn.pack(side=tk.RIGHT, pady=20)
    
    def create_main_content(self):
        """Create the main content area."""
        # Main container
        main_container = tk.Frame(self, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(main_container, style="Dashboard.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Dashboard tab
        self.create_dashboard_tab()
        
        # Search tab
        self.create_search_tab()
        
        # Statistics tab
        self.create_statistics_tab()
    
    def create_dashboard_tab(self):
        """Create the main dashboard tab."""
        dashboard_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(dashboard_frame, text="Dashboard")
        
        # Create scrollable frame
        canvas = tk.Canvas(dashboard_frame, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(dashboard_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Welcome section
        welcome_frame = tk.Frame(scrollable_frame, bg="#ffffff", relief="raised", borderwidth=1)
        welcome_frame.pack(fill=tk.X, pady=(0, 20))
        
        welcome_label = tk.Label(
            welcome_frame,
            text="Welcome to Musical Tools Suite",
            font=("Arial", 16, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        welcome_label.pack(pady=15)
        
        welcome_desc = tk.Label(
            welcome_frame,
            text="Choose a tool below to get started with your musical journey",
            font=("Arial", 11),
            bg="#ffffff",
            fg="#666666"
        )
        welcome_desc.pack(pady=(0, 15))
        
        # Tools grid
        tools_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        tools_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define tools
        tools = [
            {
                "title": "Cipher Manager",
                "description": "Manage your song collection, create setlists, and track practice sessions",
                "icon": "📚",
                "command": self.open_cipher_manager
            },
            {
                "title": "Advanced Tuner",
                "description": "Professional tuning tool with multiple instrument support",
                "icon": "🎸",
                "command": self.open_tuner
            },
            {
                "title": "Quick Search",
                "description": "Search for chords and songs across the web instantly",
                "icon": "🔍",
                "command": self.focus_search_tab
            },
            {
                "title": "Chord Identifier",
                "description": "Identify chords from audio input in real-time",
                "icon": "🎵",
                "command": self.open_chord_identifier
            },
            {
                "title": "Music Visualizer",
                "description": "Visualize music theory concepts and chord progressions",
                "icon": "🎨",
                "command": self.open_music_visualizer
            },
            {
                "title": "Source Configuration",
                "description": "Configure extraction rules for different music sites",
                "icon": "🌐",
                "command": self.open_source_config
            },
            {
                "title": "Melody Analyzer",
                "description": "Analyze melodies from audio files and compare with real-time singing",
                "icon": "🎼",
                "command": self.open_melody_analyzer
            },
            {
                "title": "Advanced Melody Analyzer",
                "description": "AI-powered vocal separation and precise melody extraction with piano roll",
                "icon": "🎹",
                "command": self.open_advanced_melody_analyzer
            },
            {
                "title": "Karaoke Analyzer",
                "description": "Complete karaoke system with Spleeter vocal isolation and real-time pitch tracking",
                "icon": "🎤",
                "command": self.open_karaoke_analyzer
            }
        ]
        
        # Create tool cards in grid
        for i, tool in enumerate(tools):
            row = i // 3
            col = i % 3
            
            card = ToolCard(
                tools_frame,
                title=tool["title"],
                description=tool["description"],
                icon=tool["icon"],
                command=tool["command"],
                width=250,
                height=180
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights
        for i in range(3):
            tools_frame.columnconfigure(i, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    def create_search_tab(self):
        """Create the search tab."""
        search_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(search_frame, text="Search")
        
        # Create two-panel layout
        paned = ttk.PanedWindow(search_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Search controls
        left_panel = tk.Frame(paned, bg="#f0f0f0")
        paned.add(left_panel, weight=1)
        
        # Quick search frame
        self.quick_search = QuickSearchFrame(left_panel, self.perform_search)
        self.quick_search.pack(fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Right panel - Results
        right_panel = tk.Frame(paned, bg="#f0f0f0")
        paned.add(right_panel, weight=2)
        
        # Results frame
        results_frame = tk.Frame(right_panel, bg="#ffffff", relief="raised", borderwidth=1)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results header
        results_header = tk.Frame(results_frame, bg="#ffffff")
        results_header.pack(fill=tk.X, padx=15, pady=(15, 0))
        
        results_title = tk.Label(
            results_header,
            text="Search Results",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        results_title.pack(side=tk.LEFT)
        
        self.results_count = tk.Label(
            results_header,
            text="",
            font=("Arial", 10),
            bg="#ffffff",
            fg="#666666"
        )
        self.results_count.pack(side=tk.RIGHT)
        
        # Results list
        results_list_frame = tk.Frame(results_frame, bg="#ffffff")
        results_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Treeview for results
        columns = ("Title", "Artist", "Source")
        self.results_tree = ttk.Treeview(results_list_frame, columns=columns, show="headings", height=15)
        
        self.results_tree.heading("Title", text="Title")
        self.results_tree.heading("Artist", text="Artist")
        self.results_tree.heading("Source", text="Source")
        
        self.results_tree.column("Title", width=300)
        self.results_tree.column("Artist", width=200)
        self.results_tree.column("Source", width=100)
        
        # Scrollbars for results
        results_v_scroll = ttk.Scrollbar(results_list_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        results_h_scroll = ttk.Scrollbar(results_list_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=results_v_scroll.set, xscrollcommand=results_h_scroll.set)
        
        self.results_tree.pack(side="left", fill="both", expand=True)
        results_v_scroll.pack(side="right", fill="y")
        results_h_scroll.pack(side="bottom", fill="x")
        
        # Bind double-click
        self.results_tree.bind("<Double-Button-1>", self.on_result_double_click)
        
        # Results actions
        actions_frame = tk.Frame(results_frame, bg="#ffffff")
        actions_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        open_btn = tk.Button(
            actions_frame,
            text="Open in Browser",
            command=self.open_selected_result,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground="#1976D2",
            activeforeground="white",
            highlightthickness=0
        )
        open_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._add_button_hover_effects(open_btn)
        
        save_btn = tk.Button(
            actions_frame,
            text="Save to Library",
            command=self.save_selected_result,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10),
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground="#388E3C",
            activeforeground="white",
            highlightthickness=0
        )
        save_btn.pack(side=tk.LEFT, padx=(10, 0))
        self._add_button_hover_effects(save_btn, primary_color="#4CAF50", hover_color="#388E3C", pressed_color="#2E7D32")
        
        # Initialize empty results
        self.search_results = []
    
    def create_statistics_tab(self):
        """Create the statistics tab."""
        stats_frame = tk.Frame(self.notebook, bg="#f0f0f0")
        self.notebook.add(stats_frame, text="Statistics")
        
        # Statistics content
        stats_container = tk.Frame(stats_frame, bg="#f0f0f0")
        stats_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Statistics cards
        stats_cards_frame = tk.Frame(stats_container, bg="#f0f0f0")
        stats_cards_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Create statistics cards
        self.create_stat_card(stats_cards_frame, "Songs in Library", "0", "📚", 0, 0)
        self.create_stat_card(stats_cards_frame, "Practice Sessions", "0", "🎯", 0, 1)
        self.create_stat_card(stats_cards_frame, "Total Practice Time", "0 min", "⏱️", 0, 2)
        self.create_stat_card(stats_cards_frame, "Favorite Songs", "0", "⭐", 1, 0)
        self.create_stat_card(stats_cards_frame, "Setlists Created", "0", "📋", 1, 1)
        self.create_stat_card(stats_cards_frame, "Searches Performed", "0", "🔍", 1, 2)
        
        # Configure grid
        for i in range(3):
            stats_cards_frame.columnconfigure(i, weight=1)
        
        # Recent activity
        activity_frame = tk.Frame(stats_container, bg="#ffffff", relief="raised", borderwidth=1)
        activity_frame.pack(fill=tk.BOTH, expand=True)
        
        activity_title = tk.Label(
            activity_frame,
            text="Recent Activity",
            font=("Arial", 14, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        activity_title.pack(pady=15)
        
        self.activity_text = tk.Text(
            activity_frame,
            height=10,
            font=("Arial", 10),
            bg="#f8f9fa",
            relief="flat",
            borderwidth=0,
            state=tk.DISABLED
        )
        self.activity_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
    
    def create_stat_card(self, parent, title, value, icon, row, col):
        """Create a statistics card."""
        card = tk.Frame(parent, bg="#ffffff", relief="raised", borderwidth=1)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        # Icon
        icon_label = tk.Label(
            card,
            text=icon,
            font=("Arial", 20),
            bg="#ffffff",
            fg="#2196F3"
        )
        icon_label.pack(pady=(15, 5))
        
        # Value
        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 18, "bold"),
            bg="#ffffff",
            fg="#333333"
        )
        value_label.pack()
        
        # Title
        title_label = tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg="#ffffff",
            fg="#666666"
        )
        title_label.pack(pady=(0, 15))
        
        # Store reference for updates
        setattr(self, f"stat_{title.lower().replace(' ', '_')}_value", value_label)
    
    def create_status_bar(self):
        """Create the status bar."""
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_dashboard_data(self):
        """Load data for the dashboard."""
        try:
            # Load statistics
            stats = self.db.get_statistics()
            
            # Update stat cards
            if hasattr(self, 'stat_songs_in_library_value'):
                self.stat_songs_in_library_value.config(text=str(stats['total_songs']))
            if hasattr(self, 'stat_favorite_songs_value'):
                self.stat_favorite_songs_value.config(text=str(stats['favorite_songs']))
            if hasattr(self, 'stat_searches_performed_value'):
                self.stat_searches_performed_value.config(text=str(stats['total_searches']))
            
            # Load practice stats
            practice_stats = self.db.get_practice_stats()
            if hasattr(self, 'stat_practice_sessions_value'):
                self.stat_practice_sessions_value.config(text=str(practice_stats['session_count']))
            if hasattr(self, 'stat_total_practice_time_value'):
                self.stat_total_practice_time_value.config(text=f"{practice_stats['total_minutes']} min")
            
            # Load setlists count
            setlists = self.db.get_setlists()
            if hasattr(self, 'stat_setlists_created_value'):
                self.stat_setlists_created_value.config(text=str(len(setlists)))
            
            # Update activity
            self.update_recent_activity()
            
            # Update status
            self.status_bar.set_status("Dashboard loaded")
            self.status_bar.set_db_status("Connected")
            
        except Exception as e:
            self.status_bar.set_status(f"Error loading data: {str(e)}")
            self.status_bar.set_db_status("Error")
    
    def update_recent_activity(self):
        """Update the recent activity display."""
        try:
            self.activity_text.config(state=tk.NORMAL)
            self.activity_text.delete(1.0, tk.END)
            
            # Get recent searches
            history = self.db.get_search_history(limit=20)
            if history:
                self.activity_text.insert(tk.END, "Recent Searches:\\n")
                for item in history:
                    self.activity_text.insert(tk.END, f"• {item['query']} ({item['created_at'][:16]})\\n")
                self.activity_text.insert(tk.END, "\\n")
            
            # Get recent songs
            songs = self.db.get_songs(limit=20)
            if songs:
                self.activity_text.insert(tk.END, "Recently Added Songs:\\n")
                for song in songs:
                    self.activity_text.insert(tk.END, f"• {song['title']} by {song.get('artist', 'Unknown')}\\n")
            
            self.activity_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.activity_text.config(state=tk.NORMAL)
            self.activity_text.delete(1.0, tk.END)
            self.activity_text.insert(tk.END, f"Error loading activity: {str(e)}")
            self.activity_text.config(state=tk.DISABLED)
    
    # Tool opening methods
    
    def open_cipher_manager(self):
        """Open the Cipher Manager."""
        try:
            show_cipher_manager(self)
            self.status_bar.set_status("Cipher Manager opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Cipher Manager: {str(e)}")
    
    def open_tuner(self):
        """Open the Advanced Tuner."""
        try:
            tuner = TunerWindow(self)
            self.status_bar.set_status("Advanced Tuner opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening tuner: {str(e)}")
    
    def open_settings(self):
        """Open the settings window."""
        try:
            show_settings_window(self)
            self.status_bar.set_status("Settings opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening settings: {str(e)}")
    
    
    def open_chord_identifier(self):
        """Open the Chord Identifier window."""
        try:
            show_chord_identifier(self)
            self.status_bar.set_status("Chord Identifier opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Chord Identifier: {str(e)}")
    
    def open_music_visualizer(self):
        """Open the Music Visualizer window."""
        try:
            show_music_visualizer(self)
            self.status_bar.set_status("Music Visualizer opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Music Visualizer: {str(e)}")
    
    def open_source_config(self):
        """Open the Source Configuration window."""
        try:
            from .source_config_window import show_source_config_window
            show_source_config_window(self)
            self.status_bar.set_status("Source Configuration opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Source Configuration: {str(e)}")
    
    def open_melody_analyzer(self):
        """Open the Melody Analyzer window."""
        try:
            show_melody_analyzer(self)
            self.status_bar.set_status("Melody Analyzer opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Melody Analyzer: {str(e)}")
    
    def open_advanced_melody_analyzer(self):
        """Open the Advanced Melody Analyzer window."""
        try:
            show_advanced_melody_analyzer(self)
            self.status_bar.set_status("Advanced Melody Analyzer opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Advanced Melody Analyzer: {str(e)}")
    
    def open_karaoke_analyzer(self):
        """Open the Karaoke Analyzer window."""
        try:
            show_karaoke_analyzer(self)
            self.status_bar.set_status("Karaoke Analyzer opened")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening Karaoke Analyzer: {str(e)}")
    
    def focus_search_tab(self):
        """Focus on the search tab."""
        self.notebook.select(1)  # Select search tab
        self.quick_search.search_entry.focus()
    
    def show_coming_soon(self):
        """Show coming soon message."""
        messagebox.showinfo(
            "Coming Soon",
            "This feature is coming soon in a future update!\\n\\n"
            "Stay tuned for more musical tools."
        )
    
    def show_help(self):
        """Show help information."""
        help_text = """Musical Tools Suite Help

Available Tools:
• Cipher Manager - Manage your song collection
• Advanced Tuner - Professional instrument tuning
• Quick Search - Find chords and songs online
• Settings - Configure the application

Coming Soon:
• Song Utilities - Transpose and analyze songs
• Chord Identifier - Real-time chord recognition
• Music Visualizer - Visual music theory

For more information, visit our documentation."""
        
        messagebox.showinfo("Help", help_text)
    
    # Search functionality
    
    def perform_search(self, query: str, source_id: str = None):
        """Perform a search."""
        try:
            if source_id:
                self.status_bar.set_status(f"Searching for: {query} (Source: {source_id})")
            else:
                self.status_bar.set_status(f"Searching for: {query} (All sources)")
            
            # Clear previous results
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Perform search using source dorks
            if source_id:
                # Import the specific search function
                try:
                    from .serper import search_with_source_dorks
                except ImportError:
                    from chord_importer.serper import search_with_source_dorks
                
                results = search_with_source_dorks(query, source_id)
            else:
                results = search_all_sources_with_dorks(query)
            self.search_results = results
            
            # Populate results
            for result in results:
                # Extract artist and title
                title_parts = result.title.split(" - ", 1)
                if len(title_parts) == 2:
                    artist, title = title_parts
                else:
                    artist = "Unknown"
                    title = result.title
                
                source = "CifraClub" if "cifraclub.com.br" in result.url else "Web"
                
                self.results_tree.insert("", tk.END, values=(title, artist, source))
            
            # Update results count
            self.results_count.config(text=f"{len(results)} results")
            self.status_bar.set_status(f"Found {len(results)} results")
            
            # Save search to history
            try:
                self.db.save_search_history(query, results_count=len(results))
            except Exception:
                pass
            
        except Exception as e:
            messagebox.showerror("Search Error", f"Error performing search: {str(e)}")
            self.status_bar.set_status("Search failed")
    
    def on_result_double_click(self, event):
        """Handle double-click on search result."""
        self.open_selected_result()
    
    def open_selected_result(self):
        """Open the selected search result in browser."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a result to open.")
            return
        
        try:
            index = self.results_tree.index(selection[0])
            result = self.search_results[index]
            webbrowser.open(result.url)
            self.status_bar.set_status("Opened result in browser")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening result: {str(e)}")
    
    def save_selected_result(self):
        """Save the selected search result to library."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a result to save.")
            return
        
        try:
            index = self.results_tree.index(selection[0])
            result = self.search_results[index]
            
            self.status_bar.set_status("Extracting song content...")
            
            # Extract full song content using source configurations
            try:
                from .core import fetch_song
                extracted_title, extracted_artist, extracted_content = fetch_song(result.url)
                
                # Use extracted data if available, otherwise fallback to search result data
                title = extracted_title if extracted_title else result.title
                artist = extracted_artist if extracted_artist else "Unknown"
                content = extracted_content if extracted_content else result.snippet
                
                # If we still don't have proper title/artist, try to parse from result title
                if not extracted_title or not extracted_artist:
                    title_parts = result.title.split(" - ", 1)
                    if len(title_parts) == 2:
                        fallback_artist, fallback_title = title_parts
                        if not title:
                            title = fallback_title
                        if not artist or artist == "Unknown":
                            artist = fallback_artist
                
            except Exception as e:
                print(f"Error extracting song content: {e}")
                # Fallback to basic search result data
                title_parts = result.title.split(" - ", 1)
                if len(title_parts) == 2:
                    artist, title = title_parts
                else:
                    artist = "Unknown"
                    title = result.title
                content = result.snippet
            
            # Save to database
            song_id = self.db.save_song(
                title=title,
                artist=artist,
                url=result.url,
                source="Web Search",
                content=content,
                tags=["Web Search"]
            )
            
            messagebox.showinfo("Saved", f"Song saved to library with ID: {song_id}")
            self.status_bar.set_status("Result saved to library")
            
            # Refresh statistics
            self.load_dashboard_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error saving result: {str(e)}")


def run_dashboard():
    """Run the Musical Tools Suite dashboard."""
    app = MusicalToolsDashboard()
    app.mainloop()


if __name__ == "__main__":
    run_dashboard()
