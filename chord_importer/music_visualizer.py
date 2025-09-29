"""
Simple Music Visualizer - Holirics Style
A clean, functional chord and lyrics viewer with transposition.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
from typing import Dict, List, Optional, Tuple, Any
import re
import threading
import time

try:
    from music21 import pitch, interval
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

try:
    from .database import get_database
    from .settings import get_settings
    from .song_utilities import MusicTheoryEngine
except ImportError:
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings
    from chord_importer.song_utilities import MusicTheoryEngine


class SimpleMusicVisualizer:
    """Simple, functional music visualizer for chords and lyrics."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.db = get_database()
        self.settings = get_settings()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("Music Visualizer - Musical Tools Suite")
        self.window.geometry("1200x800")
        self.window.resizable(True, True)
        
        # State variables
        self.current_song = None
        self.current_content = ""
        self.current_transpose = 0
        self.auto_scroll = False
        self.scroll_speed = 1.0
        self.font_size = 14
        self.chord_color = "#0066CC"
        self.lyrics_color = "#333333"
        self.highlight_color = "#FFFF99"
        
        # Auto-scroll variables
        self.scroll_thread = None
        self.scroll_running = False
        
        self.setup_ui()
        self.center_window()
        self.load_songs()
    
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
        
        # Top controls
        self.create_controls(main_frame)
        
        # Main display area
        self.create_display_area(main_frame)
        
        # Bottom controls
        self.create_bottom_controls(main_frame)
    
    def create_controls(self, parent):
        """Create top control panel."""
        controls_frame = tk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Song selection
        song_frame = tk.Frame(controls_frame)
        song_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(song_frame, text="Música:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.song_combo = ttk.Combobox(song_frame, state="readonly", width=50)
        self.song_combo.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.song_combo.bind("<<ComboboxSelected>>", self.on_song_selected)
        
        tk.Button(song_frame, text="Atualizar", command=self.load_songs,
                 bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(10, 0))
        
        # Transposition and display controls
        control_frame = tk.Frame(controls_frame)
        control_frame.pack(fill=tk.X)
        
        # Transposition
        transpose_frame = tk.Frame(control_frame)
        transpose_frame.pack(side=tk.LEFT)
        
        tk.Label(transpose_frame, text="Transposição:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        tk.Button(transpose_frame, text="-", command=lambda: self.transpose(-1),
                 width=3, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 0))
        
        self.transpose_label = tk.Label(transpose_frame, text="0", font=("Arial", 12, "bold"),
                                      width=3, relief=tk.SUNKEN, bg="white")
        self.transpose_label.pack(side=tk.LEFT, padx=(2, 2))
        
        tk.Button(transpose_frame, text="+", command=lambda: self.transpose(1),
                 width=3, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(transpose_frame, text="Reset", command=self.reset_transpose,
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Font size
        font_frame = tk.Frame(control_frame)
        font_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        tk.Label(font_frame, text="Tamanho:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        tk.Button(font_frame, text="A-", command=lambda: self.change_font_size(-2),
                 width=3, font=("Arial", 9)).pack(side=tk.LEFT, padx=(5, 0))
        
        tk.Button(font_frame, text="A+", command=lambda: self.change_font_size(2),
                 width=3, font=("Arial", 9)).pack(side=tk.LEFT, padx=(2, 0))
        
        # Auto-scroll
        scroll_frame = tk.Frame(control_frame)
        scroll_frame.pack(side=tk.RIGHT)
        
        self.scroll_btn = tk.Button(scroll_frame, text="▶ Auto Scroll", command=self.toggle_auto_scroll,
                                   bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        self.scroll_btn.pack(side=tk.RIGHT)
        
        tk.Label(scroll_frame, text="Velocidade:", font=("Arial", 10)).pack(side=tk.RIGHT, padx=(0, 5))
        
        self.speed_scale = tk.Scale(scroll_frame, from_=0.1, to=3.0, resolution=0.1,
                                   orient=tk.HORIZONTAL, length=100, command=self.on_speed_changed)
        self.speed_scale.set(1.0)
        self.speed_scale.pack(side=tk.RIGHT, padx=(0, 5))
    
    def create_display_area(self, parent):
        """Create main display area."""
        display_frame = tk.Frame(parent, relief=tk.SUNKEN, bd=2)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create text widget with scrollbar
        self.text_widget = tk.Text(display_frame, wrap=tk.WORD, font=("Consolas", self.font_size),
                                  bg="white", fg=self.lyrics_color, padx=20, pady=20,
                                  selectbackground=self.highlight_color)
        
        scrollbar = tk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for styling
        self.text_widget.tag_configure("chord", foreground=self.chord_color, font=("Consolas", self.font_size, "bold"))
        self.text_widget.tag_configure("lyrics", foreground=self.lyrics_color, font=("Consolas", self.font_size))
        self.text_widget.tag_configure("section", foreground="#666666", font=("Consolas", self.font_size, "bold"))
        
        # Bind mouse wheel
        self.text_widget.bind("<MouseWheel>", self.on_mouse_wheel)
    
    def create_bottom_controls(self, parent):
        """Create bottom control panel."""
        bottom_frame = tk.Frame(parent)
        bottom_frame.pack(fill=tk.X)
        
        # Import/Export buttons
        io_frame = tk.Frame(bottom_frame)
        io_frame.pack(side=tk.LEFT)
        
        tk.Button(io_frame, text="Importar Arquivo", command=self.import_file,
                 bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        tk.Button(io_frame, text="Exportar", command=self.export_content,
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        
        # Status info
        status_frame = tk.Frame(bottom_frame)
        status_frame.pack(side=tk.RIGHT)
        
        self.status_label = tk.Label(status_frame, text="Pronto", font=("Arial", 10))
        self.status_label.pack(side=tk.RIGHT)
    
    def load_songs(self):
        """Load songs from database."""
        try:
            songs = self.db.get_songs()
            song_names = []
            self.song_data = {}
            
            for song in songs:
                display_name = f"{song['title']} - {song.get('artist', 'Desconhecido')}"
                song_names.append(display_name)
                self.song_data[display_name] = song
            
            self.song_combo['values'] = song_names
            self.status_label.config(text=f"{len(songs)} músicas carregadas")
                
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar músicas: {str(e)}")
    
    def on_song_selected(self, event=None):
        """Handle song selection."""
        selection = self.song_combo.get()
        if not selection or selection not in self.song_data:
            return
        
        self.current_song = self.song_data[selection]
        self.current_content = self.current_song.get('content') or self.current_song.get('lyrics') or ""
        self.current_transpose = 0
        
        self.display_content()
        self.update_transpose_display()
        
        # Update status
        key_info = f" - Tom: {self.current_song.get('key_signature', 'N/A')}" if self.current_song.get('key_signature') else ""
        self.status_label.config(text=f"Carregado: {self.current_song['title']}{key_info}")
    
    def display_content(self):
        """Display the current song content with chord highlighting."""
        if not self.current_content:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, "Nenhuma música selecionada")
            return
        
        # Clear current content
        self.text_widget.delete(1.0, tk.END)
        
        # Process content line by line
        lines = self.current_content.split('\n')
        
        for line in lines:
            if self.is_chord_line(line):
                self.insert_chord_line(line)
            elif self.is_section_line(line):
                self.insert_section_line(line)
            else:
                self.insert_lyrics_line(line)
            
            self.text_widget.insert(tk.END, '\n')
        
        # Scroll to top
        self.text_widget.see(1.0)
    
    def is_chord_line(self, line: str) -> bool:
        """Check if a line contains primarily chords."""
        line = line.strip()
        if not line:
            return False
        
        # Skip metadata lines
        if ':' in line and any(keyword in line.lower() for keyword in ['tom', 'capo', 'artista', 'titulo']):
            return False
        
        # Use improved regex for chord detection
        chord_pattern = r'(?<!\w)[A-G](?:[#b]|##|bb)?(?:maj|min|m|dim|aug|sus|add|°|º|\+|M)?(?:\d+)?(?:M)?(?:\([^)]*\))?(?:sus[24]?|add\d+|no\d+)*(?:/[A-G](?:[#b]|##|bb)?(?:\d+)?)?(?:\d+)?(?!\w)'
        
        # Split line into tokens and check how many are chords
        tokens = [token for token in line.split() if token.strip()]
        if not tokens:
            return False
        
        # Count how many tokens are chords (ignoring non-musical tokens)
        chord_tokens = 0
        musical_tokens = 0
        
        for token in tokens:
            # Skip standalone parentheses
            if token.strip() in ['(', ')']:
                continue
            
            # Remove non-musical characters and check if token is meaningful
            clean_token = token.strip('()[]|.,-')
            
            # Skip common non-musical tokens
            if not clean_token or clean_token.lower() in ['intro', 'verso', 'refrão', 'ponte', 'final', 'coda', 'chorus', 'bridge', 'solo']:
                continue
            
            musical_tokens += 1
            
            # Check if clean token is a chord
            if re.match(chord_pattern, clean_token):
                chord_tokens += 1
        
        # If no valid musical tokens, return False
        if musical_tokens == 0:
            return False
        
        # If more than 70% of musical tokens are chords, consider it a chord line
        return chord_tokens / musical_tokens > 0.7
    
    def is_section_line(self, line: str) -> bool:
        """Check if a line is a section marker."""
        line = line.strip().lower()
        section_markers = ['verso', 'refrão', 'ponte', 'intro', 'solo', 'final', 'coda', 'chorus', 'bridge']
        return any(marker in line for marker in section_markers) or line.startswith('[') and line.endswith(']')
    
    def insert_chord_line(self, line: str):
        """Insert a chord line with proper formatting and transposition."""
        if self.current_transpose != 0:
            line = self.transpose_line(line)
        
        # Use regex for chord detection
        self._insert_chord_line_with_regex(line)
    
    def _insert_chord_line_with_regex(self, line: str):
        """Insert chord line using regex (fallback method)."""
        chord_pattern = r'(?<!\w)[A-G](?:[#b]|##|bb)?(?:maj|min|m|dim|aug|sus|add|°|º|\+|M)?(?:\d+)?(?:M)?(?:\([^)]*\))?(?:sus[24]?|add\d+|no\d+)*(?:/[A-G](?:[#b]|##|bb)?(?:\d+)?)?(?:\d+)?(?!\w)'
        
        last_end = 0
        for match in re.finditer(chord_pattern, line):
            # Insert text before chord
            if match.start() > last_end:
                self.text_widget.insert(tk.END, line[last_end:match.start()], "lyrics")
            
            # Insert chord with highlighting
            self.text_widget.insert(tk.END, match.group(), "chord")
            last_end = match.end()
        
        # Insert remaining text
        if last_end < len(line):
            self.text_widget.insert(tk.END, line[last_end:], "lyrics")
    
    def insert_section_line(self, line: str):
        """Insert a section line with special formatting."""
        self.text_widget.insert(tk.END, line, "section")
    
    def insert_lyrics_line(self, line: str):
        """Insert a regular lyrics line."""
        self.text_widget.insert(tk.END, line, "lyrics")
    
    def transpose_line(self, line: str) -> str:
        """Transpose all chords in a line."""
        if MUSIC21_AVAILABLE:
            return self._transpose_line_with_music21(line)
        else:
            return self._transpose_line_with_fallback(line)
    
    def _transpose_line_with_music21(self, line: str) -> str:
        """Transpose line using music21 for note transposition and MusicTheoryEngine for chord logic."""
        try:
            # Use regex substitution to preserve spacing like the fallback method
            chord_pattern = r'(?<!\w)[A-G](?:[#b]|##|bb)?(?:maj|min|m|dim|aug|sus|add|°|º|\+|M)?(?:\d+)?(?:M)?(?:\([^)]*\))?(?:sus[24]?|add\d+|no\d+)*(?:/[A-G](?:[#b]|##|bb)?(?:\d+)?)?(?:\d+)?(?!\w)'
            
            def transpose_match(match):
                chord = match.group()
                try:
                    # First try MusicTheoryEngine
                    return MusicTheoryEngine.transpose_chord(chord, self.current_transpose)
                except:
                    # If MusicTheoryEngine fails, try music21 for basic note transposition
                    try:
                        root_match = re.match(r'^([A-G][#b]?)', chord)
                        if root_match:
                            root_note = root_match.group(1)
                            note_obj = pitch.Pitch(root_note)
                            transposed_note = note_obj.transpose(interval.Interval(self.current_transpose))
                            return chord.replace(root_note, str(transposed_note), 1)
                    except:
                        pass
                    return chord  # Return original if all fails
            
            return re.sub(chord_pattern, transpose_match, line)
        except:
            # Fallback to original method
            return self._transpose_line_with_fallback(line)
    
    def _transpose_line_with_fallback(self, line: str) -> str:
        """Transpose line using fallback method."""
        chord_pattern = r'(?<!\w)[A-G](?:[#b]|##|bb)?(?:maj|min|m|dim|aug|sus|add|°|º|\+|M)?(?:\d+)?(?:M)?(?:\([^)]*\))?(?:sus[24]?|add\d+|no\d+)*(?:/[A-G](?:[#b]|##|bb)?(?:\d+)?)?(?:\d+)?(?!\w)'
        
        def transpose_match(match):
            chord = match.group()
            try:
                return MusicTheoryEngine.transpose_chord(chord, self.current_transpose)
            except:
                return chord  # Return original if transposition fails
        
        return re.sub(chord_pattern, transpose_match, line)
    
    def transpose(self, semitones: int):
        """Transpose the current song."""
        self.current_transpose += semitones
        self.current_transpose = max(-12, min(12, self.current_transpose))  # Limit range
        
        self.update_transpose_display()
        self.display_content()
    
    def reset_transpose(self):
        """Reset transposition to original key."""
        self.current_transpose = 0
        self.update_transpose_display()
        self.display_content()
    
    def update_transpose_display(self):
        """Update the transpose display."""
        if self.current_transpose == 0:
            self.transpose_label.config(text="0", bg="white")
        elif self.current_transpose > 0:
            self.transpose_label.config(text=f"+{self.current_transpose}", bg="#E8F5E8")
        else:
            self.transpose_label.config(text=str(self.current_transpose), bg="#FFE8E8")
    
    def change_font_size(self, delta: int):
        """Change the font size."""
        self.font_size += delta
        self.font_size = max(8, min(32, self.font_size))  # Limit range
        
        # Update font for all tags
        new_font = ("Consolas", self.font_size)
        chord_font = ("Consolas", self.font_size, "bold")
        section_font = ("Consolas", self.font_size, "bold")
        
        self.text_widget.configure(font=new_font)
        self.text_widget.tag_configure("chord", font=chord_font)
        self.text_widget.tag_configure("lyrics", font=new_font)
        self.text_widget.tag_configure("section", font=section_font)
    
    def toggle_auto_scroll(self):
        """Toggle auto-scroll functionality."""
        if self.auto_scroll:
            self.stop_auto_scroll()
        else:
            self.start_auto_scroll()
    
    def start_auto_scroll(self):
        """Start auto-scrolling."""
        self.auto_scroll = True
        self.scroll_running = True
        self.scroll_btn.config(text="⏸ Pausar", bg="#f44336")
        
        def scroll_worker():
            while self.scroll_running:
                try:
                    # Scroll down slowly
                    self.text_widget.yview_scroll(1, "units")
                    
                    # Check if we've reached the end
                    if self.text_widget.yview()[1] >= 1.0:
                        self.stop_auto_scroll()
                        break
                    
                    # Wait based on scroll speed
                    time.sleep(2.0 / self.scroll_speed)
                    
                except:
                    break
        
        self.scroll_thread = threading.Thread(target=scroll_worker, daemon=True)
        self.scroll_thread.start()
    
    def stop_auto_scroll(self):
        """Stop auto-scrolling."""
        self.auto_scroll = False
        self.scroll_running = False
        self.scroll_btn.config(text="▶ Auto Scroll", bg="#2196F3")
    
    def on_speed_changed(self, value):
        """Handle scroll speed change."""
        self.scroll_speed = float(value)
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling."""
        # Stop auto-scroll if user manually scrolls
        if self.auto_scroll:
            self.stop_auto_scroll()
        
        # Scroll the text widget
        self.text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def import_file(self):
        """Import a chord/lyrics file."""
        file_path = filedialog.askopenfilename(
            title="Importar Arquivo de Cifra",
            filetypes=[
                ("Arquivos de texto", "*.txt"),
                ("Arquivos ChordPro", "*.cho *.crd"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.current_content = content
                self.current_song = {
                    'title': 'Arquivo Importado',
                    'artist': 'Desconhecido',
                    'content': content
                }
                self.current_transpose = 0
                
                self.display_content()
                self.update_transpose_display()
                self.status_label.config(text=f"Importado: {file_path}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao importar arquivo: {str(e)}")
    
    def export_content(self):
        """Export current content."""
        if not self.current_content:
            messagebox.showwarning("Aviso", "Nenhum conteúdo para exportar.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Exportar Conteúdo",
            defaultextension=".txt",
            filetypes=[
                ("Arquivos de texto", "*.txt"),
                ("Arquivos ChordPro", "*.cho"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Get current displayed content (with transposition)
                export_content = self.current_content
                if self.current_transpose != 0:
                    lines = export_content.split('\n')
                    transposed_lines = []
                    for line in lines:
                        if self.is_chord_line(line):
                            transposed_lines.append(self.transpose_line(line))
                        else:
                            transposed_lines.append(line)
                    export_content = '\n'.join(transposed_lines)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
                
                messagebox.showinfo("Sucesso", f"Conteúdo exportado para: {file_path}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")


def show_music_visualizer(parent=None):
    """Show the Music Visualizer window."""
    return SimpleMusicVisualizer(parent)


if __name__ == "__main__":
    # Test the Music Visualizer
    app = SimpleMusicVisualizer()
    app.window.mainloop()
