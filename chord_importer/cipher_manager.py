"""
Cipher Manager - Local Storage System for Musical Ciphers and Chord Progressions
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Any
import json
import os
from datetime import datetime

try:
    from .database import get_database
    from .settings import get_settings
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings


class CipherManagerWindow:
    """Main window for the Cipher Manager."""
    
    def __init__(self, parent=None):
        """Initialize the Cipher Manager window."""
        self.parent = parent
        self.db = get_database()
        self.settings = get_settings()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("Cipher Manager - Musical Tools Suite")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
        # Variables
        self.current_song_id = None
        self.search_results = []
        
        self.setup_ui()
        self.refresh_song_list()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create paned window for layout
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Song list and search
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Right panel - Song details and editor
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)
    
    def setup_left_panel(self, parent):
        """Setup the left panel with song list and search."""
        # Search frame
        search_frame = tk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="🔍 Buscar:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        search_controls = tk.Frame(search_frame)
        search_controls.pack(fill=tk.X, pady=(5, 0))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_controls, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self.on_search_change)
        
        tk.Button(search_controls, text="🔍", command=self.perform_search).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(search_controls, text="🔄", command=self.refresh_song_list).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Filter frame
        filter_frame = tk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(filter_frame, text="Filtros:", font=("Arial", 9)).pack(anchor="w")
        
        filter_controls = tk.Frame(filter_frame)
        filter_controls.pack(fill=tk.X)
        
        # Filter by type
        tk.Label(filter_controls, text="Tipo:").grid(row=0, column=0, sticky="w")
        self.filter_type = ttk.Combobox(filter_controls, values=["Todos", "Locais", "Importados", "Favoritos"], 
                                       state="readonly", width=10)
        self.filter_type.set("Todos")
        self.filter_type.grid(row=0, column=1, padx=(5, 10))
        self.filter_type.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        # Filter by key
        tk.Label(filter_controls, text="Tom:").grid(row=0, column=2, sticky="w")
        keys = ["Todos", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
                "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"]
        self.filter_key = ttk.Combobox(filter_controls, values=keys, state="readonly", width=8)
        self.filter_key.set("Todos")
        self.filter_key.grid(row=0, column=3, padx=(5, 10))
        self.filter_key.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        # Filter by difficulty
        tk.Label(filter_controls, text="Dificuldade:").grid(row=0, column=4, sticky="w")
        self.filter_difficulty = ttk.Combobox(filter_controls, values=["Todas", "1", "2", "3", "4", "5"], 
                                            state="readonly", width=8)
        self.filter_difficulty.set("Todas")
        self.filter_difficulty.grid(row=0, column=5, padx=(5, 0))
        self.filter_difficulty.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        # Song list
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(list_frame, text="📋 Lista de Músicas:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        # Treeview for song list
        columns = ("Title", "Artist", "Key", "Difficulty", "Type")
        self.song_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.song_tree.heading("Title", text="Título")
        self.song_tree.heading("Artist", text="Artista")
        self.song_tree.heading("Key", text="Tom")
        self.song_tree.heading("Difficulty", text="Dif.")
        self.song_tree.heading("Type", text="Tipo")
        
        self.song_tree.column("Title", width=200)
        self.song_tree.column("Artist", width=150)
        self.song_tree.column("Key", width=60)
        self.song_tree.column("Difficulty", width=50)
        self.song_tree.column("Type", width=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.song_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.song_tree.xview)
        self.song_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.song_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection event
        self.song_tree.bind("<<TreeviewSelect>>", self.on_song_select)
        
        # Buttons frame
        buttons_frame = tk.Frame(parent)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(buttons_frame, text="➕ Nova Música", command=self.new_song, 
                 font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="📥 Importar", command=self.import_songs).pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(buttons_frame, text="🗑️ Excluir", command=self.delete_song).pack(side=tk.RIGHT)
    
    def setup_right_panel(self, parent):
        """Setup the right panel with song details and editor."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Details tab
        self.setup_details_tab()
        
        # Content tab
        self.setup_content_tab()
        
        # Practice tab
        self.setup_practice_tab()
        
        # Setlists tab
        self.setup_setlists_tab()
    
    def setup_details_tab(self):
        """Setup the song details tab."""
        details_frame = ttk.Frame(self.notebook)
        self.notebook.add(details_frame, text="📝 Detalhes")
        
        # Create scrollable frame
        canvas = tk.Canvas(details_frame)
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Song details form
        self.setup_song_form(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_song_form(self, parent):
        """Setup the song details form."""
        # Basic info
        basic_frame = tk.LabelFrame(parent, text="Informações Básicas")
        basic_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title
        tk.Label(basic_frame, text="Título:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.title_var = tk.StringVar()
        tk.Entry(basic_frame, textvariable=self.title_var, width=40).grid(row=0, column=1, columnspan=2, 
                                                                         sticky="ew", padx=5, pady=5)
        
        # Artist
        tk.Label(basic_frame, text="Artista:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.artist_var = tk.StringVar()
        tk.Entry(basic_frame, textvariable=self.artist_var, width=40).grid(row=1, column=1, columnspan=2, 
                                                                          sticky="ew", padx=5, pady=5)
        
        # Key and Tempo
        tk.Label(basic_frame, text="Tom:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.key_var = tk.StringVar()
        key_combo = ttk.Combobox(basic_frame, textvariable=self.key_var, width=10,
                                values=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
                                       "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"])
        key_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(basic_frame, text="BPM:").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.tempo_var = tk.StringVar()
        tk.Entry(basic_frame, textvariable=self.tempo_var, width=10).grid(row=2, column=3, sticky="w", padx=5, pady=5)
        
        # Time signature and Genre
        tk.Label(basic_frame, text="Compasso:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.time_sig_var = tk.StringVar()
        time_combo = ttk.Combobox(basic_frame, textvariable=self.time_sig_var, width=10,
                                 values=["4/4", "3/4", "2/4", "6/8", "12/8"])
        time_combo.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(basic_frame, text="Gênero:").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.genre_var = tk.StringVar()
        genre_combo = ttk.Combobox(basic_frame, textvariable=self.genre_var, width=15,
                                  values=["Rock", "Pop", "Blues", "Jazz", "Country", "Folk", "Gospel", "MPB", "Sertanejo"])
        genre_combo.grid(row=3, column=3, sticky="w", padx=5, pady=5)
        
        basic_frame.columnconfigure(1, weight=1)
        basic_frame.columnconfigure(3, weight=1)
        
        # Guitar info
        guitar_frame = tk.LabelFrame(parent, text="Informações de Violão/Guitarra")
        guitar_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(guitar_frame, text="Capotraste:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.capo_var = tk.StringVar()
        capo_spin = tk.Spinbox(guitar_frame, textvariable=self.capo_var, from_=0, to=12, width=5)
        capo_spin.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(guitar_frame, text="Afinação:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.tuning_var = tk.StringVar()
        tuning_combo = ttk.Combobox(guitar_frame, textvariable=self.tuning_var, width=15,
                                   values=["standard", "drop_d", "open_g", "dadgad"])
        tuning_combo.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        tk.Label(guitar_frame, text="Dificuldade:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.difficulty_var = tk.StringVar()
        diff_spin = tk.Spinbox(guitar_frame, textvariable=self.difficulty_var, from_=1, to=5, width=5)
        diff_spin.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Tags and notes
        meta_frame = tk.LabelFrame(parent, text="Tags e Notas")
        meta_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(meta_frame, text="Tags (separadas por vírgula):").pack(anchor="w", padx=5, pady=5)
        self.tags_var = tk.StringVar()
        tk.Entry(meta_frame, textvariable=self.tags_var).pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(meta_frame, text="Notas:").pack(anchor="w", padx=5, pady=5)
        self.notes_text = tk.Text(meta_frame, height=4, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Save button
        save_frame = tk.Frame(parent)
        save_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(save_frame, text="💾 Salvar Alterações", command=self.save_song,
                 font=("Arial", 10, "bold"), bg="#4CAF50", fg="white").pack(side=tk.RIGHT)
        tk.Button(save_frame, text="🔄 Restaurar", command=self.load_song_details).pack(side=tk.RIGHT, padx=(0, 10))
    
    def setup_content_tab(self):
        """Setup the content tab for lyrics and chords."""
        content_frame = ttk.Frame(self.notebook)
        self.notebook.add(content_frame, text="🎵 Conteúdo")
        
        # Toolbar
        toolbar = tk.Frame(content_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="📋 Colar", command=self.paste_content).pack(side=tk.LEFT)
        tk.Button(toolbar, text="🔄 Limpar", command=self.clear_content).pack(side=tk.LEFT, padx=(5, 0))
        tk.Button(toolbar, text="📤 Exportar", command=self.export_content).pack(side=tk.RIGHT)
        
        # Content area with tabs
        content_notebook = ttk.Notebook(content_frame)
        content_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Lyrics tab
        lyrics_frame = ttk.Frame(content_notebook)
        content_notebook.add(lyrics_frame, text="Letra")
        
        self.lyrics_text = tk.Text(lyrics_frame, wrap=tk.WORD, font=("Courier", 11))
        lyrics_scroll = ttk.Scrollbar(lyrics_frame, orient="vertical", command=self.lyrics_text.yview)
        self.lyrics_text.configure(yscrollcommand=lyrics_scroll.set)
        
        self.lyrics_text.pack(side="left", fill="both", expand=True)
        lyrics_scroll.pack(side="right", fill="y")
        
        # Chords tab
        chords_frame = ttk.Frame(content_notebook)
        content_notebook.add(chords_frame, text="Cifra Completa")
        
        self.content_text = tk.Text(chords_frame, wrap=tk.WORD, font=("Courier", 11))
        content_scroll = ttk.Scrollbar(chords_frame, orient="vertical", command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scroll.set)
        
        self.content_text.pack(side="left", fill="both", expand=True)
        content_scroll.pack(side="right", fill="y")
        
        # Chord progression tab
        progression_frame = ttk.Frame(content_notebook)
        content_notebook.add(progression_frame, text="Progressão")
        
        tk.Label(progression_frame, text="Progressão de Acordes:").pack(anchor="w", padx=5, pady=5)
        self.progression_text = tk.Text(progression_frame, height=6, wrap=tk.WORD, font=("Courier", 11))
        self.progression_text.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(progression_frame, text="Estrutura da Música:").pack(anchor="w", padx=5, pady=5)
        self.structure_text = tk.Text(progression_frame, height=6, wrap=tk.WORD, font=("Courier", 11))
        self.structure_text.pack(fill=tk.X, padx=5, pady=5)
    
    def setup_practice_tab(self):
        """Setup the practice tracking tab."""
        practice_frame = ttk.Frame(self.notebook)
        self.notebook.add(practice_frame, text="🎯 Prática")
        
        # Practice notes
        notes_frame = tk.LabelFrame(practice_frame, text="Notas de Prática")
        notes_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.practice_notes_text = tk.Text(notes_frame, height=6, wrap=tk.WORD)
        practice_scroll = ttk.Scrollbar(notes_frame, orient="vertical", command=self.practice_notes_text.yview)
        self.practice_notes_text.configure(yscrollcommand=practice_scroll.set)
        
        self.practice_notes_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        practice_scroll.pack(side="right", fill="y", pady=5)
        
        # Practice session
        session_frame = tk.LabelFrame(practice_frame, text="Registrar Sessão de Prática")
        session_frame.pack(fill=tk.X, padx=10, pady=10)
        
        session_controls = tk.Frame(session_frame)
        session_controls.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(session_controls, text="Duração (min):").grid(row=0, column=0, sticky="w")
        self.session_duration = tk.StringVar()
        tk.Entry(session_controls, textvariable=self.session_duration, width=10).grid(row=0, column=1, padx=5)
        
        tk.Label(session_controls, text="BPM praticado:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.session_tempo = tk.StringVar()
        tk.Entry(session_controls, textvariable=self.session_tempo, width=10).grid(row=0, column=3, padx=5)
        
        tk.Button(session_controls, text="📝 Registrar Sessão", 
                 command=self.add_practice_session).grid(row=0, column=4, padx=(20, 0))
        
        # Practice statistics
        stats_frame = tk.LabelFrame(practice_frame, text="Estatísticas de Prática")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=10, state=tk.DISABLED)
        stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scroll.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        stats_scroll.pack(side="right", fill="y", pady=5)
    
    def setup_setlists_tab(self):
        """Setup the setlists management tab."""
        setlists_frame = ttk.Frame(self.notebook)
        self.notebook.add(setlists_frame, text="📋 Setlists")
        
        # Setlists list
        list_frame = tk.LabelFrame(setlists_frame, text="Minhas Setlists")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Setlist controls
        controls_frame = tk.Frame(list_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(controls_frame, text="➕ Nova Setlist", command=self.create_setlist).pack(side=tk.LEFT)
        tk.Button(controls_frame, text="➕ Adicionar à Setlist", command=self.add_to_setlist).pack(side=tk.LEFT, padx=(10, 0))
        
        # Setlists treeview
        setlist_columns = ("Name", "Songs", "Updated")
        self.setlist_tree = ttk.Treeview(list_frame, columns=setlist_columns, show="headings", height=8)
        
        self.setlist_tree.heading("Name", text="Nome")
        self.setlist_tree.heading("Songs", text="Músicas")
        self.setlist_tree.heading("Updated", text="Atualizada")
        
        self.setlist_tree.column("Name", width=200)
        self.setlist_tree.column("Songs", width=80)
        self.setlist_tree.column("Updated", width=120)
        
        setlist_v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.setlist_tree.yview)
        self.setlist_tree.configure(yscrollcommand=setlist_v_scroll.set)
        
        self.setlist_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        setlist_v_scroll.pack(side="right", fill="y", pady=5)
        
        self.refresh_setlists()
    
    # Event handlers and utility methods
    
    def on_search_change(self, event=None):
        """Handle search text change."""
        # Implement real-time search with a small delay
        self.window.after(500, self.perform_search)
    
    def perform_search(self):
        """Perform search based on current search term."""
        search_term = self.search_var.get().strip()
        
        if search_term:
            try:
                # Use full-text search
                results = self.db.search_songs_full_text(search_term)
                self.search_results = results
                self.populate_song_list(results)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na busca: {str(e)}")
        else:
            self.refresh_song_list()
    
    def on_filter_change(self, event=None):
        """Handle filter change."""
        self.apply_filters()
    
    def apply_filters(self):
        """Apply current filters to song list."""
        try:
            # Get base results
            if self.search_var.get().strip():
                songs = self.search_results
            else:
                songs = self.db.get_songs(limit=1000)
            
            # Apply filters
            filter_type = self.filter_type.get()
            filter_key = self.filter_key.get()
            filter_difficulty = self.filter_difficulty.get()
            
            filtered_songs = []
            for song in songs:
                # Type filter
                if filter_type == "Locais" and not song.get('is_local'):
                    continue
                elif filter_type == "Importados" and song.get('is_local'):
                    continue
                elif filter_type == "Favoritos" and not song.get('is_favorite'):
                    continue
                
                # Key filter
                if filter_key != "Todos" and song.get('key_signature') != filter_key:
                    continue
                
                # Difficulty filter
                if filter_difficulty != "Todas" and str(song.get('difficulty_rating', 1)) != filter_difficulty:
                    continue
                
                filtered_songs.append(song)
            
            self.populate_song_list(filtered_songs)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aplicar filtros: {str(e)}")
    
    def populate_song_list(self, songs):
        """Populate the song list with given songs."""
        # Clear existing items
        for item in self.song_tree.get_children():
            self.song_tree.delete(item)
        
        # Add songs
        for song in songs:
            song_type = "Local" if song.get('is_local') else "Web"
            if song.get('is_favorite'):
                song_type += " ⭐"
            
            values = (
                song.get('title', ''),
                song.get('artist', ''),
                song.get('key_signature', ''),
                song.get('difficulty_rating', 1),
                song_type
            )
            
            item = self.song_tree.insert("", tk.END, values=values, tags=(str(song['id']),))
    
    def refresh_song_list(self):
        """Refresh the song list."""
        try:
            songs = self.db.get_songs(limit=1000)
            self.search_results = songs
            self.populate_song_list(songs)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar músicas: {str(e)}")
    
    def on_song_select(self, event=None):
        """Handle song selection."""
        selection = self.song_tree.selection()
        if selection:
            item = selection[0]
            # Get the song ID from the item tags
            tags = self.song_tree.item(item, "tags")
            if tags:
                song_id = int(tags[0])
                self.current_song_id = song_id
                self.load_song_details()
                self.load_practice_stats()
    
    def load_song_details(self):
        """Load song details into the form."""
        if not self.current_song_id:
            return
        
        try:
            song = self.db.get_song_by_id(self.current_song_id)
            if not song:
                return
            
            # Load basic info
            self.title_var.set(song.get('title', ''))
            self.artist_var.set(song.get('artist', ''))
            self.key_var.set(song.get('key_signature', ''))
            self.tempo_var.set(str(song.get('tempo', '')) if song.get('tempo') else '')
            self.time_sig_var.set(song.get('time_signature', '4/4'))
            self.genre_var.set(song.get('genre', ''))
            self.capo_var.set(str(song.get('capo_position', 0)))
            self.tuning_var.set(song.get('tuning', 'standard'))
            self.difficulty_var.set(str(song.get('difficulty_rating', 1)))
            
            # Load tags
            tags = song.get('tags', [])
            if isinstance(tags, list):
                self.tags_var.set(', '.join(tags))
            else:
                self.tags_var.set('')
            
            # Load notes
            try:
                if hasattr(self, 'notes_text') and self.notes_text.winfo_exists():
                    self.notes_text.delete(1.0, tk.END)
                    notes = song.get('notes', '')
                    if notes:
                        self.notes_text.insert(1.0, notes)
            except tk.TclError:
                pass
            
            # Load content
            try:
                if hasattr(self, 'lyrics_text') and self.lyrics_text.winfo_exists():
                    self.lyrics_text.delete(1.0, tk.END)
                    lyrics = song.get('lyrics', '')
                    if lyrics:
                        self.lyrics_text.insert(1.0, lyrics)
            except tk.TclError:
                pass
            
            try:
                if hasattr(self, 'content_text') and self.content_text.winfo_exists():
                    self.content_text.delete(1.0, tk.END)
                    content = song.get('content', '')
                    if content:
                        self.content_text.insert(1.0, content)
            except tk.TclError:
                pass
            
            try:
                if hasattr(self, 'progression_text') and self.progression_text.winfo_exists():
                    self.progression_text.delete(1.0, tk.END)
                    progression = song.get('chord_progression', '')
                    if progression:
                        self.progression_text.insert(1.0, progression)
            except tk.TclError:
                pass
            
            try:
                if hasattr(self, 'structure_text') and self.structure_text.winfo_exists():
                    self.structure_text.delete(1.0, tk.END)
                    structure = song.get('structure', '')
                    if structure:
                        self.structure_text.insert(1.0, structure)
            except tk.TclError:
                pass
            
            # Load practice notes
            try:
                if hasattr(self, 'practice_notes_text') and self.practice_notes_text.winfo_exists():
                    self.practice_notes_text.delete(1.0, tk.END)
                    practice_notes = song.get('practice_notes', '')
                    if practice_notes:
                        self.practice_notes_text.insert(1.0, practice_notes)
            except tk.TclError:
                pass  # Widget may have been destroyed
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar detalhes: {str(e)}")
    
    def save_song(self):
        """Save current song details."""
        if not self.current_song_id:
            # Create new song
            self.new_song()
            return
        
        try:
            # Parse tags
            tags_text = self.tags_var.get().strip()
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
            
            # Parse tempo
            tempo_text = self.tempo_var.get().strip()
            tempo = int(tempo_text) if tempo_text.isdigit() else None
            
            # Update song
            self.db.save_song(
                title=self.title_var.get().strip(),
                artist=self.artist_var.get().strip(),
                key_signature=self.key_var.get().strip() or None,
                tempo=tempo,
                time_signature=self.time_sig_var.get().strip() or "4/4",
                genre=self.genre_var.get().strip() or None,
                difficulty_rating=int(self.difficulty_var.get() or 1),
                content=self.content_text.get(1.0, tk.END).strip(),
                lyrics=self.lyrics_text.get(1.0, tk.END).strip(),
                chord_progression=self.progression_text.get(1.0, tk.END).strip(),
                structure=self.structure_text.get(1.0, tk.END).strip(),
                capo_position=int(self.capo_var.get() or 0),
                tuning=self.tuning_var.get().strip() or 'standard',
                tags=tags,
                notes=self.notes_text.get(1.0, tk.END).strip(),
                practice_notes=self.practice_notes_text.get(1.0, tk.END).strip(),
                is_local=True
            )
            
            messagebox.showinfo("Sucesso", "Música salva com sucesso!")
            self.refresh_song_list()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar música: {str(e)}")
    
    def new_song(self):
        """Create a new song."""
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Aviso", "Digite um título para a música!")
            return
        
        try:
            # Parse tags
            tags_text = self.tags_var.get().strip()
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
            
            # Parse tempo
            tempo_text = self.tempo_var.get().strip()
            tempo = int(tempo_text) if tempo_text.isdigit() else None
            
            # Create new song
            song_id = self.db.create_local_song(
                title=title,
                artist=self.artist_var.get().strip() or None,
                key_signature=self.key_var.get().strip() or None,
                tempo=tempo,
                time_signature=self.time_sig_var.get().strip() or "4/4",
                genre=self.genre_var.get().strip() or None,
                difficulty_rating=int(self.difficulty_var.get() or 1),
                content=self.content_text.get(1.0, tk.END).strip(),
                lyrics=self.lyrics_text.get(1.0, tk.END).strip(),
                chord_progression=self.progression_text.get(1.0, tk.END).strip(),
                structure=self.structure_text.get(1.0, tk.END).strip(),
                capo_position=int(self.capo_var.get() or 0),
                tuning=self.tuning_var.get().strip() or 'standard',
                tags=tags,
                notes=self.notes_text.get(1.0, tk.END).strip()
            )
            
            self.current_song_id = song_id
            messagebox.showinfo("Sucesso", "Nova música criada com sucesso!")
            self.refresh_song_list()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar música: {str(e)}")
    
    def delete_song(self):
        """Delete selected song."""
        if not self.current_song_id:
            messagebox.showwarning("Aviso", "Selecione uma música para excluir!")
            return
        
        song = self.db.get_song_by_id(self.current_song_id)
        if not song:
            return
        
        if messagebox.askyesno("Confirmar", f"Excluir a música '{song['title']}'?\n\nEsta ação não pode ser desfeita."):
            try:
                if self.db.delete_song(self.current_song_id):
                    messagebox.showinfo("Sucesso", "Música excluída com sucesso!")
                    self.current_song_id = None
                    self.clear_form()
                    self.refresh_song_list()
                else:
                    messagebox.showerror("Erro", "Música não encontrada!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao excluir música: {str(e)}")
    
    def clear_form(self):
        """Clear all form fields."""
        self.title_var.set('')
        self.artist_var.set('')
        self.key_var.set('')
        self.tempo_var.set('')
        self.time_sig_var.set('4/4')
        self.genre_var.set('')
        self.capo_var.set('0')
        self.tuning_var.set('standard')
        self.difficulty_var.set('1')
        self.tags_var.set('')
        
        self.notes_text.delete(1.0, tk.END)
        self.lyrics_text.delete(1.0, tk.END)
        self.content_text.delete(1.0, tk.END)
        self.progression_text.delete(1.0, tk.END)
        self.structure_text.delete(1.0, tk.END)
        self.practice_notes_text.delete(1.0, tk.END)
    
    def paste_content(self):
        """Paste content from clipboard."""
        try:
            content = self.window.clipboard_get()
            if hasattr(self, 'content_text') and self.content_text.winfo_exists():
                self.content_text.delete(1.0, tk.END)
                self.content_text.insert(1.0, content)
        except tk.TclError:
            pass  # Widget may have been destroyed
        except Exception:
            messagebox.showwarning("Aviso", "Nada para colar na área de transferência!")
    
    def clear_content(self):
        """Clear content area."""
        if messagebox.askyesno("Confirmar", "Limpar todo o conteúdo?"):
            self.content_text.delete(1.0, tk.END)
            self.lyrics_text.delete(1.0, tk.END)
            self.progression_text.delete(1.0, tk.END)
            self.structure_text.delete(1.0, tk.END)
    
    def export_content(self):
        """Export song content to file."""
        if not self.current_song_id:
            messagebox.showwarning("Aviso", "Selecione uma música para exportar!")
            return
        
        song = self.db.get_song_by_id(self.current_song_id)
        if not song:
            return
        
        # Ask for file format
        formats = [
            ("Texto simples", "*.txt"),
            ("ChordPro", "*.cho"),
            ("Todos os arquivos", "*.*")
        ]
        
        filename = f"{song['artist']} - {song['title']}" if song['artist'] else song['title']
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        filepath = filedialog.asksaveasfilename(
            title="Exportar Música",
            initialvalue=filename,
            filetypes=formats
        )
        
        if filepath:
            try:
                content = self.content_text.get(1.0, tk.END).strip()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Sucesso", f"Música exportada para:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    def import_songs(self):
        """Import songs from file."""
        filetypes = [
            ("Arquivos de texto", "*.txt"),
            ("ChordPro", "*.cho"),
            ("Todos os arquivos", "*.*")
        ]
        
        filepaths = filedialog.askopenfilenames(
            title="Importar Músicas",
            filetypes=filetypes
        )
        
        if filepaths:
            imported_count = 0
            for filepath in filepaths:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract filename as title
                    filename = os.path.basename(filepath)
                    title = os.path.splitext(filename)[0]
                    
                    # Create song
                    self.db.create_local_song(
                        title=title,
                        content=content,
                        tags=["Importado"]
                    )
                    imported_count += 1
                    
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao importar {filepath}: {str(e)}")
            
            if imported_count > 0:
                messagebox.showinfo("Sucesso", f"{imported_count} música(s) importada(s) com sucesso!")
                self.refresh_song_list()
    
    def load_practice_stats(self):
        """Load practice statistics for current song."""
        if not self.current_song_id:
            return
        
        try:
            stats = self.db.get_practice_stats(self.current_song_id)
            
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            
            stats_text = f"""Estatísticas de Prática:

📊 Sessões realizadas: {stats['session_count']}
⏱️ Tempo total praticado: {stats['total_minutes']} minutos
📈 Duração média por sessão: {stats['avg_duration']:.1f} minutos
📅 Última prática: {stats['last_practice'] or 'Nunca'}

"""
            
            self.stats_text.insert(1.0, stats_text)
            self.stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Erro ao carregar estatísticas: {e}")
    
    def add_practice_session(self):
        """Add a practice session."""
        if not self.current_song_id:
            messagebox.showwarning("Aviso", "Selecione uma música!")
            return
        
        duration_text = self.session_duration.get().strip()
        if not duration_text.isdigit():
            messagebox.showwarning("Aviso", "Digite uma duração válida em minutos!")
            return
        
        duration = int(duration_text)
        tempo_text = self.session_tempo.get().strip()
        tempo = int(tempo_text) if tempo_text.isdigit() else None
        
        try:
            self.db.add_practice_session(
                song_id=self.current_song_id,
                duration_minutes=duration,
                tempo_practiced=tempo
            )
            
            messagebox.showinfo("Sucesso", "Sessão de prática registrada!")
            self.session_duration.set('')
            self.session_tempo.set('')
            self.load_practice_stats()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao registrar sessão: {str(e)}")
    
    def refresh_setlists(self):
        """Refresh the setlists list."""
        try:
            # Clear existing items
            for item in self.setlist_tree.get_children():
                self.setlist_tree.delete(item)
            
            # Load setlists
            setlists = self.db.get_setlists()
            for setlist in setlists:
                values = (
                    setlist['name'],
                    setlist['song_count'],
                    setlist['updated_at'][:16] if setlist['updated_at'] else ''
                )
                item = self.setlist_tree.insert("", tk.END, values=values, tags=(str(setlist['id']),))
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar setlists: {str(e)}")
    
    def create_setlist(self):
        """Create a new setlist."""
        dialog = tk.Toplevel(self.window)
        dialog.title("Nova Setlist")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text="Nome da Setlist:").pack(pady=10)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, width=40).pack(pady=5)
        
        tk.Label(dialog, text="Descrição (opcional):").pack(pady=(10, 0))
        desc_text = tk.Text(dialog, height=4, width=40)
        desc_text.pack(pady=5)
        
        def save_setlist():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Aviso", "Digite um nome para a setlist!")
                return
            
            description = desc_text.get(1.0, tk.END).strip()
            
            try:
                self.db.create_setlist(name, description or None)
                messagebox.showinfo("Sucesso", "Setlist criada com sucesso!")
                dialog.destroy()
                self.refresh_setlists()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar setlist: {str(e)}")
        
        buttons_frame = tk.Frame(dialog)
        buttons_frame.pack(pady=10)
        
        tk.Button(buttons_frame, text="Salvar", command=save_setlist).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def add_to_setlist(self):
        """Add current song to a setlist."""
        if not self.current_song_id:
            messagebox.showwarning("Aviso", "Selecione uma música!")
            return
        
        try:
            setlists = self.db.get_setlists()
            if not setlists:
                messagebox.showinfo("Info", "Crie uma setlist primeiro!")
                return
            
            # Create selection dialog
            dialog = tk.Toplevel(self.window)
            dialog.title("Adicionar à Setlist")
            dialog.geometry("300x200")
            dialog.resizable(False, False)
            dialog.transient(self.window)
            dialog.grab_set()
            
            tk.Label(dialog, text="Escolha uma setlist:").pack(pady=10)
            
            setlist_var = tk.StringVar()
            setlist_combo = ttk.Combobox(dialog, textvariable=setlist_var, state="readonly", width=30)
            setlist_combo['values'] = [f"{s['name']} ({s['song_count']} músicas)" for s in setlists]
            setlist_combo.pack(pady=5)
            
            def add_song():
                selection = setlist_combo.current()
                if selection < 0:
                    messagebox.showwarning("Aviso", "Selecione uma setlist!")
                    return
                
                setlist_id = setlists[selection]['id']
                
                try:
                    if self.db.add_song_to_setlist(setlist_id, self.current_song_id):
                        messagebox.showinfo("Sucesso", "Música adicionada à setlist!")
                        dialog.destroy()
                        self.refresh_setlists()
                    else:
                        messagebox.showerror("Erro", "Erro ao adicionar música!")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro: {str(e)}")
            
            buttons_frame = tk.Frame(dialog)
            buttons_frame.pack(pady=10)
            
            tk.Button(buttons_frame, text="Adicionar", command=add_song).pack(side=tk.LEFT, padx=5)
            tk.Button(buttons_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar setlists: {str(e)}")


def show_cipher_manager(parent=None):
    """Show the Cipher Manager window."""
    cipher_manager = CipherManagerWindow(parent)
    return cipher_manager


if __name__ == "__main__":
    # Test the cipher manager
    root = tk.Tk()
    root.withdraw()
    
    cipher_manager = show_cipher_manager()
    cipher_manager.window.mainloop()
