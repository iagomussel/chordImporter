"""
Settings window for Chord Importer application.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any

try:
    from .settings import get_settings
    from .database import get_database
except ImportError:
    from chord_importer.settings import get_settings
    from chord_importer.database import get_database

class SettingsWindow:
    """Settings configuration window."""
    
    def __init__(self, parent=None):
        """Initialize settings window."""
        self.parent = parent
        self.settings = get_settings()
        self.db = get_database()
        
        # Create window
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
        
        self.window.title("⚙️ Configurações - Chord Importer")
        self.window.geometry("700x600")
        self.window.resizable(True, True)
        
        # Variables for settings
        self.setting_vars = {}
        
        self.setup_ui()
        self.load_current_settings()
        
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
        # Main frame with scrollbar
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_general_tab()
        self.create_api_tab()
        self.create_audio_tab()
        self.create_search_tab()
        self.create_export_tab()
        self.create_database_tab()
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        tk.Button(buttons_frame, text="Restaurar Padrões", 
                 command=self.reset_to_defaults).pack(side=tk.LEFT)
        
        tk.Button(buttons_frame, text="Exportar Config", 
                 command=self.export_config).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(buttons_frame, text="Importar Config", 
                 command=self.import_config).pack(side=tk.LEFT, padx=(10, 0))
        
        tk.Button(buttons_frame, text="Cancelar", 
                 command=self.window.destroy).pack(side=tk.RIGHT)
        
        tk.Button(buttons_frame, text="Aplicar", 
                 command=self.apply_settings).pack(side=tk.RIGHT, padx=(0, 10))
        
        tk.Button(buttons_frame, text="OK", 
                 command=self.save_and_close).pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_general_tab(self):
        """Create general settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Geral")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Language
        self.add_setting_row(scrollable_frame, "Idioma:", "General", "language", 
                           "combobox", values=["pt_BR", "en_US", "es_ES"])
        
        # Theme
        self.add_setting_row(scrollable_frame, "Tema:", "General", "theme",
                           "combobox", values=["default", "dark", "light"])
        
        # Auto save searches
        self.add_setting_row(scrollable_frame, "Salvar buscas automaticamente:", 
                           "General", "auto_save_searches", "checkbox")
        
        # Max search results
        self.add_setting_row(scrollable_frame, "Máximo de resultados:", 
                           "General", "max_search_results", "spinbox", 
                           from_=10, to=200)
        
        # Default export format
        self.add_setting_row(scrollable_frame, "Formato de exportação padrão:", 
                           "General", "default_export_format", "combobox",
                           values=["pdf", "xml"])
        
        # Export directory
        self.add_setting_row(scrollable_frame, "Diretório de exportação:", 
                           "General", "export_directory", "directory")
        
        # Auto detect chords
        self.add_setting_row(scrollable_frame, "Detectar acordes automaticamente:", 
                           "General", "auto_detect_chords", "checkbox")
        
        # Show advanced options
        self.add_setting_row(scrollable_frame, "Mostrar opções avançadas:", 
                           "General", "show_advanced_options", "checkbox")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_api_tab(self):
        """Create API settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="API")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # API Key section
        api_frame = tk.LabelFrame(scrollable_frame, text="Configuração da API Serper")
        api_frame.pack(fill=tk.X, pady=10)
        
        # Instructions
        instructions = tk.Label(api_frame, 
                               text="Para usar a busca avançada, você precisa de uma chave API do Serper.\n"
                                    "1. Acesse https://serper.dev/\n"
                                    "2. Crie uma conta gratuita\n"
                                    "3. Copie sua API Key e cole abaixo:",
                               justify=tk.LEFT, wraplength=500)
        instructions.pack(anchor="w", padx=10, pady=5)
        
        # Serper API Key
        self.add_setting_row(api_frame, "Serper API Key:", "API", "serper_api_key", "password")
        
        # Test API button
        test_frame = tk.Frame(api_frame)
        test_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(test_frame, text="Testar API Key", 
                 command=self.test_api_key).pack(side=tk.LEFT)
        
        self.api_status_label = tk.Label(test_frame, text="", fg="gray")
        self.api_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Other API settings
        self.add_setting_row(scrollable_frame, "Habilitar busca alternativa:", 
                           "API", "enable_fallback_search", "checkbox")
        
        self.add_setting_row(scrollable_frame, "Timeout da API (segundos):", 
                           "API", "api_timeout", "spinbox", from_=10, to=120)
        
        self.add_setting_row(scrollable_frame, "Máximo de tentativas:", 
                           "API", "max_retries", "spinbox", from_=1, to=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_audio_tab(self):
        """Create audio settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Áudio")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Sample rate
        self.add_setting_row(scrollable_frame, "Taxa de amostragem:", "Audio", "sample_rate",
                           "combobox", values=["22050", "44100", "48000", "96000"])
        
        # Buffer size
        self.add_setting_row(scrollable_frame, "Tamanho do buffer:", "Audio", "buffer_size",
                           "combobox", values=["1024", "2048", "4096", "8192"])
        
        # Noise floor
        self.add_setting_row(scrollable_frame, "Piso de ruído:", "Audio", "noise_floor",
                           "entry", validate="float")
        
        # Stability threshold
        self.add_setting_row(scrollable_frame, "Limiar de estabilidade (Hz):", 
                           "Audio", "stability_threshold", "entry", validate="float")
        
        # HPS harmonics
        self.add_setting_row(scrollable_frame, "Harmônicos HPS:", "Audio", "hps_harmonics",
                           "spinbox", from_=3, to=10)
        
        # Auto detect strings
        self.add_setting_row(scrollable_frame, "Detectar cordas automaticamente:", 
                           "Audio", "auto_detect_strings", "checkbox")
        
        # Tuner precision
        self.add_setting_row(scrollable_frame, "Precisão do afinador (cents):", 
                           "Audio", "tuner_precision", "entry", validate="float")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_search_tab(self):
        """Create search settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Busca")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Results per key
        self.add_setting_row(scrollable_frame, "Resultados por tom:", 
                           "Search", "results_per_key", "spinbox", from_=1, to=50)
        
        # Search timeout
        self.add_setting_row(scrollable_frame, "Timeout de busca (segundos):", 
                           "Search", "search_timeout", "spinbox", from_=10, to=120)
        
        # Enable chord sequence search
        self.add_setting_row(scrollable_frame, "Habilitar busca por sequência de acordes:", 
                           "Search", "enable_chord_sequence_search", "checkbox")
        
        # Preserve accidental preference
        self.add_setting_row(scrollable_frame, "Preservar preferência de acidentes:", 
                           "Search", "preserve_accidental_preference", "checkbox")
        
        # Auto transpose results
        self.add_setting_row(scrollable_frame, "Transpor resultados automaticamente:", 
                           "Search", "auto_transpose_results", "checkbox")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_export_tab(self):
        """Create export settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Exportação")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # PDF quality
        self.add_setting_row(scrollable_frame, "Qualidade do PDF:", "Export", "pdf_quality",
                           "combobox", values=["low", "medium", "high"])
        
        # XML format
        self.add_setting_row(scrollable_frame, "Formato XML:", "Export", "xml_format",
                           "combobox", values=["opensong", "chordpro"])
        
        # Include metadata
        self.add_setting_row(scrollable_frame, "Incluir metadados:", 
                           "Export", "include_metadata", "checkbox")
        
        # Auto open exports
        self.add_setting_row(scrollable_frame, "Abrir exportações automaticamente:", 
                           "Export", "auto_open_exports", "checkbox")
        
        # Backup exports
        self.add_setting_row(scrollable_frame, "Fazer backup das exportações:", 
                           "Export", "backup_exports", "checkbox")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_database_tab(self):
        """Create database settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Banco de Dados")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Auto cleanup days
        self.add_setting_row(scrollable_frame, "Limpeza automática (dias):", 
                           "Database", "auto_cleanup_days", "spinbox", from_=30, to=365)
        
        # Max search history
        self.add_setting_row(scrollable_frame, "Máximo histórico de buscas:", 
                           "Database", "max_search_history", "spinbox", from_=100, to=5000)
        
        # Enable statistics
        self.add_setting_row(scrollable_frame, "Habilitar estatísticas:", 
                           "Database", "enable_statistics", "checkbox")
        
        # Database statistics
        stats_frame = tk.LabelFrame(scrollable_frame, text="Estatísticas do Banco de Dados")
        stats_frame.pack(fill=tk.X, pady=10)
        
        try:
            stats = self.db.get_statistics()
            
            tk.Label(stats_frame, text=f"Total de músicas: {stats['total_songs']}").pack(anchor="w")
            tk.Label(stats_frame, text=f"Músicas favoritas: {stats['favorite_songs']}").pack(anchor="w")
            tk.Label(stats_frame, text=f"Total de buscas: {stats['total_searches']}").pack(anchor="w")
            tk.Label(stats_frame, text=f"Total de exportações: {stats['total_exports']}").pack(anchor="w")
            
        except Exception as e:
            tk.Label(stats_frame, text=f"Erro ao carregar estatísticas: {e}").pack(anchor="w")
        
        # Database actions
        actions_frame = tk.LabelFrame(scrollable_frame, text="Ações do Banco de Dados")
        actions_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(actions_frame, text="Limpar Dados Antigos", 
                 command=self.cleanup_database).pack(side=tk.LEFT, padx=5)
        
        tk.Button(actions_frame, text="Backup do Banco", 
                 command=self.backup_database).pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def add_setting_row(self, parent, label_text, section, key, widget_type, **kwargs):
        """Add a setting row to the parent frame."""
        row_frame = tk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=5)
        
        # Label
        label = tk.Label(row_frame, text=label_text, width=25, anchor="w")
        label.pack(side=tk.LEFT)
        
        # Widget
        var_key = f"{section}.{key}"
        
        if widget_type == "entry":
            var = tk.StringVar()
            entry = tk.Entry(row_frame, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.setting_vars[var_key] = var
            
        elif widget_type == "password":
            var = tk.StringVar()
            entry = tk.Entry(row_frame, textvariable=var, show="*")
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.setting_vars[var_key] = var
            
        elif widget_type == "checkbox":
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(row_frame, variable=var)
            checkbox.pack(side=tk.LEFT)
            self.setting_vars[var_key] = var
            
        elif widget_type == "combobox":
            var = tk.StringVar()
            combobox = ttk.Combobox(row_frame, textvariable=var, 
                                   values=kwargs.get('values', []), state="readonly")
            combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.setting_vars[var_key] = var
            
        elif widget_type == "spinbox":
            var = tk.StringVar()
            spinbox = tk.Spinbox(row_frame, textvariable=var,
                               from_=kwargs.get('from_', 0),
                               to=kwargs.get('to', 100))
            spinbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.setting_vars[var_key] = var
            
        elif widget_type == "directory":
            var = tk.StringVar()
            entry = tk.Entry(row_frame, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            def browse_directory():
                directory = filedialog.askdirectory(initialdir=var.get())
                if directory:
                    var.set(directory)
            
            tk.Button(row_frame, text="Procurar...", 
                     command=browse_directory).pack(side=tk.RIGHT, padx=(5, 0))
            
            self.setting_vars[var_key] = var
    
    def load_current_settings(self):
        """Load current settings into the UI."""
        for var_key, var in self.setting_vars.items():
            section, key = var_key.split('.', 1)
            
            if isinstance(var, tk.BooleanVar):
                value = self.settings.get_bool(section, key)
                var.set(value)
            else:
                value = self.settings.get(section, key, "")
                var.set(value)
    
    def apply_settings(self):
        """Apply current settings."""
        # Validate settings first
        issues = self.validate_current_settings()
        if issues:
            messagebox.showerror("Configurações Inválidas", 
                               "\n".join(issues))
            return
        
        # Apply settings
        for var_key, var in self.setting_vars.items():
            section, key = var_key.split('.', 1)
            value = var.get()
            self.settings.set(section, key, value)
        
        # Save to file
        self.settings.save_settings()
        
        messagebox.showinfo("Configurações", "Configurações aplicadas com sucesso!")
    
    def save_and_close(self):
        """Save settings and close window."""
        self.apply_settings()
        self.window.destroy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno("Restaurar Padrões", 
                              "Tem certeza que deseja restaurar todas as configurações para os valores padrão?"):
            self.settings.reset_to_defaults()
            self.load_current_settings()
            messagebox.showinfo("Configurações", "Configurações restauradas para os padrões!")
    
    def export_config(self):
        """Export configuration to file."""
        file_path = filedialog.asksaveasfilename(
            title="Exportar Configurações",
            defaultextension=".cfg",
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.settings.export_settings(file_path):
                messagebox.showinfo("Exportar", "Configurações exportadas com sucesso!")
            else:
                messagebox.showerror("Exportar", "Erro ao exportar configurações!")
    
    def import_config(self):
        """Import configuration from file."""
        file_path = filedialog.askopenfilename(
            title="Importar Configurações",
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.settings.import_settings(file_path):
                self.load_current_settings()
                messagebox.showinfo("Importar", "Configurações importadas com sucesso!")
            else:
                messagebox.showerror("Importar", "Erro ao importar configurações!")
    
    def cleanup_database(self):
        """Clean up old database data."""
        if messagebox.askyesno("Limpeza do Banco", 
                              "Tem certeza que deseja limpar dados antigos do banco de dados?"):
            try:
                days = self.settings.get_int('Database', 'auto_cleanup_days', 90)
                result = self.db.cleanup_old_data(days)
                
                message = f"Limpeza concluída:\n"
                message += f"- {result['cleaned_searches']} buscas antigas removidas\n"
                message += f"- {result['cleaned_exports']} exportações órfãs removidas"
                
                messagebox.showinfo("Limpeza", message)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na limpeza: {e}")
    
    def backup_database(self):
        """Create database backup."""
        file_path = filedialog.asksaveasfilename(
            title="Backup do Banco de Dados",
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.db.db_path, file_path)
                messagebox.showinfo("Backup", "Backup criado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar backup: {e}")
    
    def validate_current_settings(self):
        """Validate current settings in the UI."""
        issues = []
        
        # Add validation logic here
        # For now, just use the settings validation
        try:
            # Create temporary settings with current values
            temp_settings = {}
            for var_key, var in self.setting_vars.items():
                section, key = var_key.split('.', 1)
                if section not in temp_settings:
                    temp_settings[section] = {}
                temp_settings[section][key] = var.get()
            
            # Basic validation
            if 'Audio' in temp_settings:
                sample_rate = int(temp_settings['Audio'].get('sample_rate', 44100))
                if sample_rate not in [22050, 44100, 48000, 96000]:
                    issues.append("Taxa de amostragem inválida")
            
        except Exception as e:
            issues.append(f"Erro de validação: {e}")
        
        return issues
    
    def test_api_key(self):
        """Test the Serper API key."""
        api_key = self.setting_vars.get('API.serper_api_key', tk.StringVar()).get().strip()
        
        if not api_key:
            self.api_status_label.config(text="❌ API Key não informada", fg="red")
            return
        
        self.api_status_label.config(text="🔄 Testando...", fg="blue")
        self.window.update()
        
        def test_in_thread():
            try:
                import requests
                import json
                
                headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
                payload = {"q": "test", "gl": "br", "hl": "pt-br", "num": 1}
                
                response = requests.post("https://google.serper.dev/search", 
                                       headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    self.api_status_label.config(text="✅ API Key válida", fg="green")
                elif response.status_code == 401:
                    self.api_status_label.config(text="❌ API Key inválida", fg="red")
                elif response.status_code == 429:
                    self.api_status_label.config(text="⚠️ Limite de uso atingido", fg="orange")
                else:
                    self.api_status_label.config(text=f"❌ Erro {response.status_code}", fg="red")
                    
            except Exception as e:
                self.api_status_label.config(text=f"❌ Erro: {str(e)[:30]}...", fg="red")
        
        import threading
        threading.Thread(target=test_in_thread, daemon=True).start()

def show_settings_window(parent=None):
    """Show the settings window."""
    settings_window = SettingsWindow(parent)
    return settings_window

