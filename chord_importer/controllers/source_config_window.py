#!/usr/bin/env python3
"""
Source Configuration Management Window
GUI for managing flexible extraction configurations.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
from typing import Dict, Optional

try:
    from .source_configs import get_source_manager, SourceConfig, SourceSelector, SearchDork
    from .flexible_extractor import FlexibleExtractor
except ImportError:
    from chord_importer.source_configs import get_source_manager, SourceConfig, SourceSelector, SearchDork
    from chord_importer.flexible_extractor import FlexibleExtractor


class SourceConfigWindow:
    """Window for managing source configurations."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.source_manager = get_source_manager()
        self.current_source_id = None
        
        self.setup_window()
        self.setup_ui()
        self.refresh_source_list()
    
    def setup_window(self):
        """Setup the main window."""
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("Configuração de Fontes - Musical Tools Suite")
        self.window.geometry("900x700")
        self.window.resizable(True, True)
        
        # Center window
        self.window.transient(self.parent)
        if self.parent:
            self.window.grab_set()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Gerenciador de Configurações de Fontes", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Left panel - Source list
        left_frame = ttk.LabelFrame(main_frame, text="Fontes Configuradas", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Source list
        self.source_listbox = tk.Listbox(left_frame, width=25)
        self.source_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.source_listbox.bind('<<ListboxSelect>>', self.on_source_select)
        
        # Source list scrollbar
        list_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.source_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.source_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # Source list buttons
        list_buttons_frame = ttk.Frame(left_frame)
        list_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(list_buttons_frame, text="Nova Fonte", command=self.new_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_buttons_frame, text="Duplicar", command=self.duplicate_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_buttons_frame, text="Excluir", command=self.delete_source).pack(side=tk.LEFT)
        
        # Configure left frame grid
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # Right panel - Configuration editor
        right_frame = ttk.LabelFrame(main_frame, text="Configuração da Fonte", padding="10")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # Notebook for different configuration sections
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Basic configuration tab
        self.create_basic_tab()
        
        # Selectors tab
        self.create_selectors_tab()
        
        # Advanced tab
        self.create_advanced_tab()
        
        # Dorks tab
        self.create_dorks_tab()
        
        # Test tab
        self.create_test_tab()
        
        # Bottom buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(buttons_frame, text="Salvar", command=self.save_current_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Testar", command=self.test_current_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Importar", command=self.import_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Exportar", command=self.export_source).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Restaurar Padrões", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Fechar", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def create_basic_tab(self):
        """Create the basic configuration tab."""
        basic_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(basic_frame, text="Básico")
        
        # Source name
        ttk.Label(basic_frame, text="Nome da Fonte:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Domain patterns
        ttk.Label(basic_frame, text="Padrões de Domínio:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.domains_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.domains_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(basic_frame, text="(separados por vírgula, ex: cifraclub.com.br,letras.mus.br)", 
                 font=("Arial", 8)).grid(row=2, column=1, sticky=tk.W, pady=(0, 10))
        
        # URL suffix
        ttk.Label(basic_frame, text="Sufixo da URL:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.suffix_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.suffix_var, width=40).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(basic_frame, text="(ex: /imprimir.html, /print, deixe vazio se não usar)", 
                 font=("Arial", 8)).grid(row=4, column=1, sticky=tk.W, pady=(0, 10))
        
        # Configure grid
        basic_frame.columnconfigure(1, weight=1)
    
    def create_selectors_tab(self):
        """Create the selectors configuration tab."""
        selectors_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(selectors_frame, text="Seletores")
        
        # Create scrollable frame
        canvas = tk.Canvas(selectors_frame)
        scrollbar = ttk.Scrollbar(selectors_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Selector fields
        self.selector_vars = {}
        
        fields = [
            ("title", "Título"),
            ("artist", "Artista"),
            ("key", "Tom"),
            ("capo", "Capotraste"),
            ("content", "Conteúdo/Cifra"),
            ("composer", "Compositor"),
            ("views", "Visualizações"),
            ("difficulty", "Dificuldade"),
            ("instrument", "Instrumento")
        ]
        
        row = 0
        for field_id, field_name in fields:
            # Field label
            field_frame = ttk.LabelFrame(scrollable_frame, text=field_name, padding="5")
            field_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10), padx=(0, 10))
            field_frame.columnconfigure(1, weight=1)
            
            self.selector_vars[field_id] = {}
            
            # CSS Selector
            ttk.Label(field_frame, text="CSS Selector:").grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
            self.selector_vars[field_id]['css'] = tk.StringVar()
            ttk.Entry(field_frame, textvariable=self.selector_vars[field_id]['css'], width=50).grid(
                row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
            
            # Text Search
            ttk.Label(field_frame, text="Busca de Texto:").grid(row=1, column=0, sticky=tk.W, pady=(0, 2))
            self.selector_vars[field_id]['text'] = tk.StringVar()
            ttk.Entry(field_frame, textvariable=self.selector_vars[field_id]['text'], width=50).grid(
                row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
            
            # Regex Pattern
            ttk.Label(field_frame, text="Padrão Regex:").grid(row=2, column=0, sticky=tk.W, pady=(0, 2))
            self.selector_vars[field_id]['regex'] = tk.StringVar()
            ttk.Entry(field_frame, textvariable=self.selector_vars[field_id]['regex'], width=50).grid(
                row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
            
            # Fallback selectors
            ttk.Label(field_frame, text="Seletores Alternativos:").grid(row=3, column=0, sticky=tk.W, pady=(0, 2))
            self.selector_vars[field_id]['fallback'] = tk.StringVar()
            ttk.Entry(field_frame, textvariable=self.selector_vars[field_id]['fallback'], width=50).grid(
                row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 2))
            
            # Join separator
            ttk.Label(field_frame, text="Separador (múltiplos):").grid(row=4, column=0, sticky=tk.W)
            self.selector_vars[field_id]['join_separator'] = tk.StringVar()
            join_entry = ttk.Entry(field_frame, textvariable=self.selector_vars[field_id]['join_separator'], width=50)
            join_entry.grid(row=4, column=1, sticky=(tk.W, tk.E))
            
            # Add help text for join separator
            help_text = "Separador para unir múltiplos elementos (ex: ', ', ' | ', '\\n'). Deixe vazio para pegar apenas o primeiro."
            ttk.Label(field_frame, text=help_text, font=("Arial", 8), foreground="gray").grid(
                row=5, column=1, sticky=tk.W, pady=(0, 5))
            
            row += 1
        
        # Configure scrollable frame
        scrollable_frame.columnconfigure(0, weight=1)
    
    def create_advanced_tab(self):
        """Create the advanced configuration tab."""
        advanced_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(advanced_frame, text="Avançado")
        
        # Processing options
        options_frame = ttk.LabelFrame(advanced_frame, text="Opções de Processamento", padding="10")
        options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.remove_scripts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Remover scripts", variable=self.remove_scripts_var).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.remove_styles_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Remover estilos CSS", variable=self.remove_styles_var).grid(
            row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Timeout
        ttk.Label(options_frame, text="Timeout (segundos):").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.timeout_var = tk.StringVar(value="15")
        ttk.Entry(options_frame, textvariable=self.timeout_var, width=10).grid(
            row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # Encoding
        ttk.Label(options_frame, text="Codificação:").grid(row=3, column=0, sticky=tk.W)
        self.encoding_var = tk.StringVar(value="utf-8")
        ttk.Entry(options_frame, textvariable=self.encoding_var, width=20).grid(
            row=3, column=1, sticky=tk.W)
        
        advanced_frame.columnconfigure(0, weight=1)
    
    def create_dorks_tab(self):
        """Create the search dorks configuration tab."""
        dorks_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(dorks_frame, text="Dorks de Busca")
        
        # Dorks list frame
        list_frame = ttk.LabelFrame(dorks_frame, text="Dorks Configurados", padding="10")
        list_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Dorks treeview
        columns = ("Nome", "Padrão", "Prioridade", "Ativo")
        self.dorks_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        
        # Configure columns
        self.dorks_tree.heading("Nome", text="Nome")
        self.dorks_tree.heading("Padrão", text="Padrão de Busca")
        self.dorks_tree.heading("Prioridade", text="Prioridade")
        self.dorks_tree.heading("Ativo", text="Ativo")
        
        self.dorks_tree.column("Nome", width=120)
        self.dorks_tree.column("Padrão", width=300)
        self.dorks_tree.column("Prioridade", width=80)
        self.dorks_tree.column("Ativo", width=60)
        
        self.dorks_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for dorks tree
        dorks_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dorks_tree.yview)
        dorks_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.dorks_tree.configure(yscrollcommand=dorks_scrollbar.set)
        
        # Dorks buttons
        dorks_buttons_frame = ttk.Frame(list_frame)
        dorks_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(dorks_buttons_frame, text="Novo Dork", command=self.new_dork).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dorks_buttons_frame, text="Editar", command=self.edit_dork).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dorks_buttons_frame, text="Excluir", command=self.delete_dork).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dorks_buttons_frame, text="Testar", command=self.test_dork).pack(side=tk.LEFT)
        
        # Configure grid weights
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Dork editor frame
        editor_frame = ttk.LabelFrame(dorks_frame, text="Editor de Dork", padding="10")
        editor_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Dork name
        ttk.Label(editor_frame, text="Nome:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.dork_name_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.dork_name_var, width=30).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        
        # Dork pattern
        ttk.Label(editor_frame, text="Padrão:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.dork_pattern_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.dork_pattern_var, width=50).grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        
        # Help text for pattern
        help_text = "Use {query} para o termo de busca, {domain} para o domínio\nExemplos: 'site:{domain} {query}', '{query} filetype:pdf'"
        ttk.Label(editor_frame, text=help_text, font=("Arial", 8), foreground="gray").grid(
            row=2, column=1, sticky=tk.W, pady=(0, 10), padx=(5, 0))
        
        # Dork description
        ttk.Label(editor_frame, text="Descrição:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.dork_description_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.dork_description_var, width=50).grid(
            row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(5, 0))
        
        # Priority and enabled
        controls_frame = ttk.Frame(editor_frame)
        controls_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(controls_frame, text="Prioridade:").pack(side=tk.LEFT)
        self.dork_priority_var = tk.StringVar(value="5")
        priority_spinbox = ttk.Spinbox(controls_frame, from_=1, to=10, textvariable=self.dork_priority_var, width=5)
        priority_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        self.dork_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Ativo", variable=self.dork_enabled_var).pack(side=tk.LEFT)
        
        # Filetype and max results
        ttk.Label(controls_frame, text="Filetype:").pack(side=tk.LEFT, padx=(20, 5))
        self.dork_filetype_var = tk.StringVar()
        ttk.Entry(controls_frame, textvariable=self.dork_filetype_var, width=10).pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(controls_frame, text="Max Resultados:").pack(side=tk.LEFT, padx=(0, 5))
        self.dork_max_results_var = tk.StringVar(value="10")
        ttk.Spinbox(controls_frame, from_=1, to=50, textvariable=self.dork_max_results_var, width=5).pack(side=tk.LEFT)
        
        # Configure editor frame grid
        editor_frame.columnconfigure(1, weight=1)
        
        # Configure main dorks frame grid
        dorks_frame.columnconfigure(0, weight=1)
        dorks_frame.rowconfigure(0, weight=1)
        
        # Bind tree selection
        self.dorks_tree.bind('<<TreeviewSelect>>', self.on_dork_select)
    
    def create_test_tab(self):
        """Create the test tab."""
        test_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(test_frame, text="Teste")
        
        # Test URL
        ttk.Label(test_frame, text="URL de Teste:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.test_url_var = tk.StringVar()
        ttk.Entry(test_frame, textvariable=self.test_url_var, width=60).grid(
            row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(test_frame, text="Testar Extração", command=self.run_test).grid(
            row=0, column=2, padx=(10, 0), pady=(0, 5))
        
        # Test results
        ttk.Label(test_frame, text="Resultados do Teste:").grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        
        self.test_results = tk.Text(test_frame, height=20, width=80)
        self.test_results.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Test results scrollbar
        test_scrollbar = ttk.Scrollbar(test_frame, orient=tk.VERTICAL, command=self.test_results.yview)
        test_scrollbar.grid(row=2, column=3, sticky=(tk.N, tk.S))
        self.test_results.configure(yscrollcommand=test_scrollbar.set)
        
        test_frame.columnconfigure(1, weight=1)
        test_frame.rowconfigure(2, weight=1)
    
    def refresh_source_list(self):
        """Refresh the source list."""
        self.source_listbox.delete(0, tk.END)
        
        sources = self.source_manager.list_sources()
        for source_id, source_name in sources.items():
            self.source_listbox.insert(tk.END, f"{source_id} - {source_name}")
    
    def on_source_select(self, event):
        """Handle source selection."""
        selection = self.source_listbox.curselection()
        if selection:
            selected_text = self.source_listbox.get(selection[0])
            source_id = selected_text.split(' - ')[0]
            self.load_source_config(source_id)
    
    def load_source_config(self, source_id: str):
        """Load a source configuration into the form."""
        config = self.source_manager.get_source(source_id)
        if not config:
            return
        
        self.current_source_id = source_id
        
        # Load basic info
        self.name_var.set(config.name)
        self.domains_var.set(", ".join(config.domain_patterns))
        self.suffix_var.set(config.url_suffix)
        
        # Load selectors
        selector_configs = {
            'title': config.title_selector,
            'artist': config.artist_selector,
            'key': config.key_selector,
            'capo': config.capo_selector,
            'content': config.content_selector,
            'composer': config.composer_selector,
            'views': config.views_selector,
            'difficulty': config.difficulty_selector,
            'instrument': config.instrument_selector
        }
        
        for field_id, selector_config in selector_configs.items():
            if field_id in self.selector_vars and selector_config:
                self.selector_vars[field_id]['css'].set(selector_config.css_selector or "")
                self.selector_vars[field_id]['text'].set(selector_config.text_search or "")
                self.selector_vars[field_id]['regex'].set(selector_config.regex_pattern or "")
                self.selector_vars[field_id]['fallback'].set(", ".join(selector_config.fallback_selectors))
                self.selector_vars[field_id]['join_separator'].set(selector_config.join_separator or "")
        
        # Load advanced options
        self.remove_scripts_var.set(config.remove_scripts)
        self.remove_styles_var.set(config.remove_styles)
        self.timeout_var.set(str(config.timeout))
        self.encoding_var.set(config.encoding)
        
        # Load dorks
        self.refresh_dorks_list()
        self._clear_dork_form()
    
    def save_current_source(self):
        """Save the current source configuration."""
        if not self.current_source_id:
            messagebox.showerror("Erro", "Nenhuma fonte selecionada para salvar.")
            return
        
        try:
            # Save current dork if any
            self.save_dork()
            
            # Create source config from form data
            config = self._create_config_from_form()
            
            # Save to manager
            self.source_manager.add_source(self.current_source_id, config)
            self.source_manager.save_sources()
            
            messagebox.showinfo("Sucesso", "Configuração salva com sucesso!")
            self.refresh_source_list()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configuração: {str(e)}")
    
    def _create_config_from_form(self) -> SourceConfig:
        """Create a SourceConfig from the form data."""
        # Parse domains
        domains_text = self.domains_var.get().strip()
        domains = [d.strip() for d in domains_text.split(',') if d.strip()]
        
        # Create selectors
        selectors = {}
        for field_id in self.selector_vars:
            css_sel = self.selector_vars[field_id]['css'].get().strip()
            text_search = self.selector_vars[field_id]['text'].get().strip()
            regex_pattern = self.selector_vars[field_id]['regex'].get().strip()
            fallback_text = self.selector_vars[field_id]['fallback'].get().strip()
            fallback_selectors = [f.strip() for f in fallback_text.split(',') if f.strip()]
            join_separator = self.selector_vars[field_id]['join_separator'].get().strip()
            
            selectors[field_id] = SourceSelector(
                css_selector=css_sel if css_sel else None,
                text_search=text_search if text_search else None,
                regex_pattern=regex_pattern if regex_pattern else None,
                fallback_selectors=fallback_selectors,
                join_separator=join_separator if join_separator else None
            )
        
        # Create config
        config = SourceConfig(
            name=self.name_var.get().strip(),
            domain_patterns=domains,
            url_suffix=self.suffix_var.get().strip(),
            title_selector=selectors['title'],
            artist_selector=selectors['artist'],
            key_selector=selectors['key'],
            capo_selector=selectors['capo'],
            content_selector=selectors['content'],
            composer_selector=selectors['composer'],
            views_selector=selectors['views'],
            difficulty_selector=selectors['difficulty'],
            instrument_selector=selectors['instrument'],
            remove_scripts=self.remove_scripts_var.get(),
            remove_styles=self.remove_styles_var.get(),
            timeout=int(self.timeout_var.get()),
            encoding=self.encoding_var.get().strip()
        )
        
        return config
    
    def new_source(self):
        """Create a new source configuration."""
        source_id = tk.simpledialog.askstring("Nova Fonte", "Digite o ID da nova fonte:")
        if source_id and source_id not in self.source_manager.sources:
            self.current_source_id = source_id
            self._clear_form()
            self.name_var.set(f"Nova Fonte - {source_id}")
        elif source_id:
            messagebox.showerror("Erro", "ID da fonte já existe!")
    
    def duplicate_source(self):
        """Duplicate the current source."""
        if not self.current_source_id:
            messagebox.showerror("Erro", "Nenhuma fonte selecionada para duplicar.")
            return
        
        new_id = tk.simpledialog.askstring("Duplicar Fonte", "Digite o ID da nova fonte:")
        if new_id and new_id not in self.source_manager.sources:
            config = self.source_manager.get_source(self.current_source_id)
            if config:
                new_config = SourceConfig(**config.__dict__)
                new_config.name = f"{config.name} (Cópia)"
                self.source_manager.add_source(new_id, new_config)
                self.source_manager.save_sources()
                self.refresh_source_list()
        elif new_id:
            messagebox.showerror("Erro", "ID da fonte já existe!")
    
    def delete_source(self):
        """Delete the current source."""
        if not self.current_source_id:
            messagebox.showerror("Erro", "Nenhuma fonte selecionada para excluir.")
            return
        
        if messagebox.askyesno("Confirmar", f"Excluir a fonte '{self.current_source_id}'?"):
            self.source_manager.remove_source(self.current_source_id)
            self.source_manager.save_sources()
            self.refresh_source_list()
            self._clear_form()
            self.current_source_id = None
    
    def _clear_form(self):
        """Clear all form fields."""
        self.name_var.set("")
        self.domains_var.set("")
        self.suffix_var.set("")
        
        for field_vars in self.selector_vars.values():
            for var_name, var in field_vars.items():
                var.set("")
        
        self.remove_scripts_var.set(True)
        self.remove_styles_var.set(True)
        self.timeout_var.set("15")
        self.encoding_var.set("utf-8")
        
        # Clear dorks
        if hasattr(self, 'dorks_tree'):
            for item in self.dorks_tree.get_children():
                self.dorks_tree.delete(item)
        if hasattr(self, '_clear_dork_form'):
            self._clear_dork_form()
    
    def test_current_source(self):
        """Test the current source configuration."""
        test_url = self.test_url_var.get().strip()
        if not test_url:
            messagebox.showerror("Erro", "Digite uma URL de teste.")
            return
        
        self.run_test()
    
    def run_test(self):
        """Run extraction test."""
        test_url = self.test_url_var.get().strip()
        if not test_url:
            return
        
        try:
            # Create config from current form
            config = self._create_config_from_form()
            
            # Run extraction
            extractor = FlexibleExtractor()
            song_data = extractor.extract_song_data(test_url, config)
            formatted_content = extractor.format_song_export(song_data, config.name)
            
            # Display results
            self.test_results.delete(1.0, tk.END)
            self.test_results.insert(tk.END, "=== DADOS EXTRAÍDOS ===\n")
            self.test_results.insert(tk.END, f"Título: {song_data.get('title', 'N/A')}\n")
            self.test_results.insert(tk.END, f"Artista: {song_data.get('artist', 'N/A')}\n")
            self.test_results.insert(tk.END, f"Tom: {song_data.get('key', 'N/A')}\n")
            self.test_results.insert(tk.END, f"Capotraste: {song_data.get('capo', 'N/A')}\n")
            self.test_results.insert(tk.END, f"Conteúdo: {len(song_data.get('content', ''))} caracteres\n")
            self.test_results.insert(tk.END, f"Metadados: {song_data.get('metadata', {})}\n\n")
            
            self.test_results.insert(tk.END, "=== CONTEÚDO FORMATADO ===\n")
            self.test_results.insert(tk.END, formatted_content)
            self.test_results.insert(tk.END, f"\n\n=== ESTATÍSTICAS ===\n")
            self.test_results.insert(tk.END, f"Tamanho total do conteúdo: {len(formatted_content)} caracteres\n")
            self.test_results.insert(tk.END, f"Linhas: {formatted_content.count(chr(10)) + 1}\n")
            
        except Exception as e:
            self.test_results.delete(1.0, tk.END)
            self.test_results.insert(tk.END, f"ERRO: {str(e)}")
    
    def import_source(self):
        """Import source configuration from file."""
        file_path = filedialog.askopenfilename(
            title="Importar Configuração",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                imported = self.source_manager.import_source(file_path)
                self.source_manager.save_sources()
                self.refresh_source_list()
                messagebox.showinfo("Sucesso", f"Importadas {len(imported)} configurações: {', '.join(imported)}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao importar: {str(e)}")
    
    def export_source(self):
        """Export current source configuration to file."""
        if not self.current_source_id:
            messagebox.showerror("Erro", "Nenhuma fonte selecionada para exportar.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Exportar Configuração",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.source_manager.export_source(self.current_source_id, file_path)
                messagebox.showinfo("Sucesso", f"Configuração exportada para {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    # Dorks management methods
    
    def refresh_dorks_list(self):
        """Refresh the dorks list for the current source."""
        # Clear current items
        for item in self.dorks_tree.get_children():
            self.dorks_tree.delete(item)
        
        if not self.current_source_id:
            return
        
        config = self.source_manager.get_source(self.current_source_id)
        if not config or not config.search_dorks:
            return
        
        # Add dorks to tree
        for dork in config.search_dorks:
            self.dorks_tree.insert("", tk.END, values=(
                dork.name,
                dork.pattern,
                str(dork.priority),
                "Sim" if dork.enabled else "Não"
            ))
    
    def on_dork_select(self, event):
        """Handle dork selection in tree."""
        selection = self.dorks_tree.selection()
        if not selection:
            self._clear_dork_form()
            return
        
        item = selection[0]
        values = self.dorks_tree.item(item)['values']
        
        if not values or not self.current_source_id:
            return
        
        # Find the dork by name
        config = self.source_manager.get_source(self.current_source_id)
        if not config:
            return
        
        dork_name = values[0]
        dork = config.get_dork(dork_name)
        
        if dork:
            self._load_dork_to_form(dork)
    
    def _load_dork_to_form(self, dork: SearchDork):
        """Load dork data to form fields."""
        self.dork_name_var.set(dork.name)
        self.dork_pattern_var.set(dork.pattern)
        self.dork_description_var.set(dork.description)
        self.dork_priority_var.set(str(dork.priority))
        self.dork_enabled_var.set(dork.enabled)
        self.dork_filetype_var.set(dork.filetype or "")
        self.dork_max_results_var.set(str(dork.max_results))
    
    def _clear_dork_form(self):
        """Clear dork form fields."""
        self.dork_name_var.set("")
        self.dork_pattern_var.set("")
        self.dork_description_var.set("")
        self.dork_priority_var.set("5")
        self.dork_enabled_var.set(True)
        self.dork_filetype_var.set("")
        self.dork_max_results_var.set("10")
    
    def new_dork(self):
        """Create a new dork."""
        if not self.current_source_id:
            messagebox.showerror("Erro", "Selecione uma fonte primeiro.")
            return
        
        self._clear_dork_form()
        # Focus on name field
        self.dork_name_var.set("Novo Dork")
        self.dork_pattern_var.set("{query}")
    
    def edit_dork(self):
        """Edit selected dork."""
        selection = self.dorks_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um dork para editar.")
            return
        
        # The form is already populated by on_dork_select
        pass
    
    def delete_dork(self):
        """Delete selected dork."""
        selection = self.dorks_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um dork para excluir.")
            return
        
        if not self.current_source_id:
            return
        
        item = selection[0]
        values = self.dorks_tree.item(item)['values']
        dork_name = values[0]
        
        if messagebox.askyesno("Confirmar", f"Excluir o dork '{dork_name}'?"):
            self.source_manager.remove_dork_from_source(self.current_source_id, dork_name)
            self.refresh_dorks_list()
            self._clear_dork_form()
    
    def save_dork(self):
        """Save current dork (called when saving source)."""
        if not self.current_source_id:
            return
        
        name = self.dork_name_var.get().strip()
        pattern = self.dork_pattern_var.get().strip()
        
        if not name or not pattern:
            return  # Skip invalid dorks
        
        try:
            priority = int(self.dork_priority_var.get())
            max_results = int(self.dork_max_results_var.get())
        except ValueError:
            priority = 5
            max_results = 10
        
        filetype = self.dork_filetype_var.get().strip() or None
        
        dork = SearchDork(
            name=name,
            pattern=pattern,
            description=self.dork_description_var.get().strip(),
            priority=priority,
            enabled=self.dork_enabled_var.get(),
            max_results=max_results,
            filetype=filetype
        )
        
        # Check if updating existing dork
        config = self.source_manager.get_source(self.current_source_id)
        if config:
            existing_dork = config.get_dork(name)
            if existing_dork:
                # Update existing
                self.source_manager.update_dork_in_source(self.current_source_id, name, dork)
            else:
                # Add new
                self.source_manager.add_dork_to_source(self.current_source_id, dork)
    
    def test_dork(self):
        """Test selected dork with a sample query."""
        selection = self.dorks_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um dork para testar.")
            return
        
        if not self.current_source_id:
            return
        
        # Get test query from user
        test_query = simpledialog.askstring("Teste de Dork", "Digite um termo de busca para testar:")
        if not test_query:
            return
        
        item = selection[0]
        values = self.dorks_tree.item(item)['values']
        dork_name = values[0]
        
        config = self.source_manager.get_source(self.current_source_id)
        if not config:
            return
        
        dork = config.get_dork(dork_name)
        if not dork:
            return
        
        # Format the query
        primary_domain = config.domain_patterns[0] if config.domain_patterns else ""
        formatted_query = dork.format_query(test_query, primary_domain)
        
        # Show result
        messagebox.showinfo("Resultado do Teste", 
                          f"Dork: {dork_name}\n"
                          f"Padrão: {dork.pattern}\n"
                          f"Query de teste: {test_query}\n"
                          f"Resultado formatado: {formatted_query}")
    
    def reset_to_defaults(self):
        """Reset all sources to default configurations."""
        if messagebox.askyesno("Confirmar", 
                              "Isso irá restaurar todas as configurações para os padrões originais.\n"
                              "Suas configurações personalizadas serão perdidas.\n\n"
                              "Deseja continuar?"):
            try:
                reset_sources = self.source_manager.reset_to_defaults()
                self.refresh_source_list()
                self._clear_form()
                self.current_source_id = None
                messagebox.showinfo("Sucesso", 
                                  f"Configurações restauradas para os padrões.\n"
                                  f"Fontes carregadas: {', '.join(reset_sources)}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao restaurar padrões: {str(e)}")


def show_source_config_window(parent=None):
    """Show the source configuration window."""
    window = SourceConfigWindow(parent)
    if parent:
        parent.wait_window(window.window)
    else:
        window.window.mainloop()


if __name__ == "__main__":
    show_source_config_window()
