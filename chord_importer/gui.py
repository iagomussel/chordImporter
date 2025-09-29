from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import webbrowser

# Optional dotenv support for .env
try:  # pragma: no cover
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    _load_dotenv = None  # type: ignore

try:
    # Try relative imports first (for package usage)
    from .core import build_opensong_xml, fetch_song, save_song, download_cifraclub_pdf, download_cifraclub_pdf_alternative
    from .serper import SearchResult, search_cifraclub, search_filetype, search_query, search_chord_sequence, search_chord_sequence_dynamic
    from .dorks import Dork, add_dork, delete_dork, load_dorks, save_dorks, update_dork
    from .tuner_advanced import TunerWindow
    from .database import get_database
    from .settings import get_settings
    from .settings_window import show_settings_window
    from .cipher_manager import show_cipher_manager
except ImportError:
    # Fall back to absolute imports (for PyInstaller)
    from chord_importer.core import build_opensong_xml, fetch_song, save_song, download_cifraclub_pdf, download_cifraclub_pdf_alternative
    from chord_importer.serper import SearchResult, search_cifraclub, search_filetype, search_query, search_chord_sequence, search_chord_sequence_dynamic
    from chord_importer.dorks import Dork, add_dork, delete_dork, load_dorks, save_dorks, update_dork
    from chord_importer.tuner_advanced import TunerWindow
    from chord_importer.database import get_database
    from chord_importer.settings import get_settings
    from chord_importer.settings_window import show_settings_window
    from chord_importer.cipher_manager import show_cipher_manager


def sanitize_filename(name: str) -> str:
    """Create a Windows-safe filename from an arbitrary string.

    Removes or replaces characters not allowed in Windows filenames and trims
    trailing dots/spaces.
    """
    invalid_chars = '\\/:*?"<>|'
    cleaned = "".join("-" if c in invalid_chars else c for c in name)
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(" .")
    return cleaned[:200]  # Limit length


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Chord Importer")
        self.geometry("720x520")

        # Initialize database and settings
        self.db = get_database()
        self.settings = get_settings()
        self._settings_win = None

        # Preload dorks and build search frame
        self._dorks = load_dorks()
        frm_search = tk.Frame(self)
        frm_search.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(frm_search, text="Termo de busca:").pack(side=tk.LEFT)
        self.entry_term = tk.Entry(frm_search)
        self.entry_term.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.entry_term.bind("<Return>", lambda e: self.on_search())

        tk.Label(frm_search, text="Dork:").pack(side=tk.LEFT, padx=(8, 0))
        self.combo_dork = ttk.Combobox(frm_search, state="readonly")
        self.combo_dork.pack(side=tk.LEFT)
        self.combo_dork["values"] = [d.name for d in self._dorks]
        if self._dorks:
            self.combo_dork.current(0)

        self.btn_search = tk.Button(frm_search, text="Buscar", command=self.on_search)
        self.btn_search.pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frm_search, text="Gerenciar dorks", command=self.open_dorks_manager).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frm_search, text="🎸 Afinador", command=self.open_tuner).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frm_search, text="📚 Cipher Manager", command=self.open_cipher_manager).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frm_search, text="⚙️ Configurações", command=self.open_settings).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(frm_search, text="💾 Músicas Salvas", command=self.open_saved_songs).pack(side=tk.LEFT, padx=(8, 0))

        # Single results list
        frm_results = tk.Frame(self)
        frm_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.listbox = tk.Listbox(frm_results)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(frm_results, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Double-Button-1>", lambda e: self._open_selected_url("current"))
        self.listbox.bind("<Button-3>", lambda e: self._show_context_menu(e, "current"))

        # Context menu (single list)
        self.menu_results = tk.Menu(self, tearoff=0)
        self.menu_results.add_command(label="Abrir no navegador", command=lambda: self._open_selected_url("current"))
        self.menu_results.add_command(label="Copiar URL", command=lambda: self._copy_selected_url("current"))
        self.menu_results.add_separator()
        self.menu_results.add_command(label="💾 Salvar no DB", command=self.save_selected_song)

        # Actions frame - Only DB save functionality
        frm_actions = tk.Frame(self)
        frm_actions.pack(fill=tk.X, padx=10, pady=10)

        # Info label
        tk.Label(frm_actions, text="Salve as músicas encontradas no banco de dados local:", 
                font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.btn_save = tk.Button(frm_actions, text="💾 Salvar Selecionada", 
                                 command=self.save_selected_song, font=("Arial", 10, "bold"))
        self.btn_save.pack(side=tk.RIGHT, padx=(8, 0))
        
        self.btn_save_all = tk.Button(frm_actions, text="💾 Salvar Todas", 
                                     command=self.save_all_songs, font=("Arial", 10, "bold"))
        self.btn_save_all.pack(side=tk.RIGHT, padx=(8, 0))

        self.status = tk.StringVar(value="Pronto")
        tk.Label(self, textvariable=self.status, anchor="w").pack(fill=tk.X, padx=10, pady=(0, 4))
        self.progress = ttk.Progressbar(self, mode="indeterminate")

        # Log area
        frm_log = tk.Frame(self)
        frm_log.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(frm_log, text="Log:", anchor="w").pack(fill=tk.X)
        
        log_frame = tk.Frame(frm_log)
        log_frame.pack(fill=tk.X)
        
        self.log_text = tk.Text(log_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        self.results: list[SearchResult] = []

        # Dorks manager (on demand)
        self._dorks_win: tk.Toplevel | None = None
        
        # Tuner window (on demand)
        self._tuner_win: TunerWindow | None = None
        
        # Initial log message
        self.log("Chord Importer iniciado")
        self.log(f"Dorks carregadas: {len(self._dorks)}")
        for dork in self._dorks:
            self.log(f"  - {dork.name} (id: {dork.id})")

    def log(self, message: str) -> None:
        """Add a message to the log area."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
        self.update()  # Force GUI update

    def clear_log(self) -> None:
        """Clear the log area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def open_dorks_manager(self) -> None:
        if self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win):
            try:
                self._dorks_win.lift()
                return
            except Exception:
                pass
        win = tk.Toplevel(self)
        win.title("Gerenciar dorks")
        self._dorks_win = win

        left = tk.Frame(win)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = tk.Frame(win)
        right.pack(side=tk.RIGHT, fill=tk.Y)

        self.dm_listbox = tk.Listbox(left)
        self.dm_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(left, orient=tk.VERTICAL, command=self.dm_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.dm_listbox.config(yscrollcommand=sb.set)

        frm_form = tk.LabelFrame(right, text="Dork")
        frm_form.pack(fill=tk.X, pady=(0, 6))
        tk.Label(frm_form, text="Nome").grid(row=0, column=0, sticky="w")
        tk.Label(frm_form, text="Query").grid(row=1, column=0, sticky="w")
        tk.Label(frm_form, text="Filetype").grid(row=2, column=0, sticky="w")
        tk.Label(frm_form, text="Limite").grid(row=3, column=0, sticky="w")
        self.dm_name = tk.Entry(frm_form)
        self.dm_query = tk.Entry(frm_form)
        self.dm_filetype = tk.Entry(frm_form)
        self.dm_limit = tk.Entry(frm_form)
        self.dm_name.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.dm_query.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        self.dm_filetype.grid(row=2, column=1, sticky="ew", padx=(6, 0))
        self.dm_limit.grid(row=3, column=1, sticky="ew", padx=(6, 0))
        frm_form.columnconfigure(1, weight=1)

        frm_buttons = tk.Frame(right)
        frm_buttons.pack(fill=tk.X)
        tk.Button(frm_buttons, text="Novo", command=self.on_dork_new).pack(side=tk.LEFT)
        tk.Button(frm_buttons, text="Salvar", command=self.on_dork_save).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(frm_buttons, text="Excluir", command=self.on_dork_delete).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(frm_buttons, text="Buscar", command=self.on_dork_search).pack(side=tk.RIGHT)

        self._selected_dork_id: str | None = None
        self._refresh_dorks_list()
        self.dm_listbox.bind("<<ListboxSelect>>", self.on_dork_select)

    def _refresh_dorks_list(self) -> None:
        if not (self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win)):
            return
        self.dm_listbox.delete(0, tk.END)
        for d in self._dorks:
            self.dm_listbox.insert(tk.END, f"{d.name}")

    def on_dork_select(self, _evt: object) -> None:
        if not (self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win)):
            return
        sel = self.dm_listbox.curselection()
        if not sel:
            self._selected_dork_id = None
            return
        d = self._dorks[sel[0]]
        self._selected_dork_id = d.id
        self.dm_name.delete(0, tk.END)
        self.dm_name.insert(0, d.name)
        self.dm_query.delete(0, tk.END)
        self.dm_query.insert(0, d.query)
        self.dm_filetype.delete(0, tk.END)
        self.dm_filetype.insert(0, d.filetype or "")
        self.dm_limit.delete(0, tk.END)
        self.dm_limit.insert(0, str(d.limit))

    def on_dork_new(self) -> None:
        self._selected_dork_id = None
        if not (self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win)):
            return
        for e in (self.dm_name, self.dm_query, self.dm_filetype, self.dm_limit):
            e.delete(0, tk.END)
        self.dm_limit.insert(0, "10")

    def on_dork_save(self) -> None:
        if not (self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win)):
            return
        name = self.dm_name.get().strip()
        query = self.dm_query.get().strip()
        filetype = self.dm_filetype.get().strip() or None
        limit_txt = self.dm_limit.get().strip()
        try:
            limit = int(limit_txt) if limit_txt else 10
        except Exception:
            limit = 10
        if not name or not query:
            messagebox.showwarning("Campos obrigatórios", "Preencha Nome e Query.")
            return
        if self._selected_dork_id:
            # Update existing
            for i, d in enumerate(self._dorks):
                if d.id == self._selected_dork_id:
                    self._dorks[i] = Dork(id=d.id, name=name, query=query, filetype=filetype, limit=limit)
                    break
        else:
            # Create
            new = add_dork(name=name, query=query, filetype=filetype, limit=limit)
            self._dorks.append(new)
            self._selected_dork_id = new.id
        save_dorks(self._dorks)
        self._refresh_dorks_list()
        # Refresh dropdown
        self.combo_dork["values"] = [d.name for d in self._dorks]
        if self._dorks:
            self.combo_dork.current(0)

    def on_dork_delete(self) -> None:
        if not self._selected_dork_id:
            return
        delete_dork(self._selected_dork_id)
        self._dorks = [d for d in self._dorks if d.id != self._selected_dork_id]
        self._selected_dork_id = None
        self._refresh_dorks_list()
        self.on_dork_new()

    def on_dork_search(self) -> None:
        term = self.entry_term.get().strip()
        if not term:
            messagebox.showwarning("Aviso", "Digite um termo para buscar.")
            return
        if not (self._dorks_win and tk.Toplevel.winfo_exists(self._dorks_win)):
            return
        sel = self.dm_listbox.curselection()
        if not sel:
            messagebox.showinfo("Selecione", "Selecione um dork para buscar.")
            return
        d = self._dorks[sel[0]]
        # Build query
        query = (d.query or "{term}").replace("{term}", term)
        filetype = d.filetype or None
        limit = d.limit or 10

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Buscando dork...")
                results = search_query(query, num=limit, filetype=filetype)
                # Write into a simple modal list for now
                win = tk.Toplevel(self)
                win.title(f"Resultados: {d.name}")
                lb = tk.Listbox(win)
                lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                sb = tk.Scrollbar(win, orient=tk.VERTICAL, command=lb.yview)
                sb.pack(side=tk.RIGHT, fill=tk.Y)
                lb.config(yscrollcommand=sb.set)
                for r in results:
                    lb.insert(tk.END, f"{r.title}  —  {r.url}")
                self.status.set(f"{len(results)} resultados do dork")
            except Exception as exc:
                messagebox.showerror("Erro", str(exc))
                self.status.set("Erro na busca do dork")
            finally:
                self.set_busy(False)


    def set_busy(self, busy: bool) -> None:
        controls = [
            self.btn_search,
            self.btn_save,
            self.btn_save_all,
        ]
        for ctl in controls:
            try:
                ctl.config(state=tk.DISABLED if busy else tk.NORMAL)
            except Exception:
                pass
        self.entry_term.config(state=tk.DISABLED if busy else tk.NORMAL)
        # Do not disable listbox; programmatic inserts must work while busy
        # Progress bar
        if busy:
            # Pack if not currently visible
            try:
                self.progress.pack_forget()
            except Exception:
                pass
            self.progress.pack(fill=tk.X, padx=10, pady=(0, 8))
            try:
                self.progress.start(10)
            except Exception:
                pass
        else:
            try:
                self.progress.stop()
            except Exception:
                pass
            try:
                self.progress.pack_forget()
            except Exception:
                pass

    def on_search(self) -> None:
        term = self.entry_term.get().strip()
        if not term:
            messagebox.showwarning("Aviso", "Digite um termo para buscar.")
            return
        # Determine selected dork
        dork_index = self.combo_dork.current() if self.combo_dork is not None else -1
        if dork_index < 0 or dork_index >= len(self._dorks):
            messagebox.showwarning("Dork", "Selecione um dork válido.")
            return
        d = self._dorks[dork_index]
        query = (d.query or "{term}").replace("{term}", term)
        filetype = d.filetype or None
        limit = d.limit or 10

        # Log the search details
        self.log(f"Iniciando busca: '{term}'")
        self.log(f"Dork selecionada: {d.name} (id: {d.id})")
        self.log(f"Query gerada: {query}")
        if filetype:
            self.log(f"Tipo de arquivo: {filetype}")
        self.log(f"Limite de resultados: {limit}")

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Buscando...")
                # Run selected dork
                if d.id == "chord_sequence":
                    # Dynamic chord sequence search
                    self.log("Usando busca dinâmica por sequência de acordes")
                    self.status.set("Iniciando busca por sequência de acordes...")
                    self.listbox.delete(0, tk.END)
                    self.results = []
                    
                    # Use dynamic search to add results progressively
                    for key_index, key_name, key_results in search_chord_sequence_dynamic(term, num_per_key=10):
                        # Update status to show current key being searched
                        self.status.set(f"Buscando no tom de {key_name}... ({key_index + 1}/12)")
                        self.log(f"Tom {key_name}: {len(key_results)} resultados encontrados")
                        self.update()  # Force GUI update
                        
                        # Add results to the list as they come
                        for result in key_results:
                            self.results.append(result)
                            self.listbox.insert(tk.END, f"{result.title}  —  {result.url}")
                        
                        # Update GUI to show new results
                        self.update()
                        
                        # Small delay for visual effect
                        import time
                        time.sleep(0.1)
                    
                    self.status.set(f"Busca concluída: {len(self.results)} resultados encontrados")
                    self.log(f"Busca concluída: {len(self.results)} resultados totais")
                    return  # Don't continue with normal result processing
                    
                elif d.id == "chords" or ("cifraclub.com.br" in (d.query or "")):
                    self.log("Usando busca específica do CifraClub")
                    self.results = search_cifraclub(term)
                elif filetype:
                    self.log(f"Usando busca por tipo de arquivo: {filetype}")
                    self.results = search_filetype(term, filetype)
                else:
                    self.log("Usando busca genérica")
                    self.results = search_query(query, num=limit, filetype=filetype)

                self.listbox.delete(0, tk.END)
                for r in self.results:
                    self.listbox.insert(tk.END, f"{r.title}  —  {r.url}")
                self.status.set(f"{len(self.results)} resultados: {d.name}")
                self.log(f"Busca concluída: {len(self.results)} resultados encontrados")
            except Exception as exc:
                error_msg = f"Erro na busca: {str(exc)}"
                self.log(error_msg)
                messagebox.showerror("Erro na busca", str(exc))
                self.status.set("Erro na busca")
            finally:
                self.set_busy(False)

        threading.Thread(target=_run, daemon=True).start()

    def open_tuner(self) -> None:
        """Open the guitar tuner window."""
        if self._tuner_win and hasattr(self._tuner_win, 'window') and tk.Toplevel.winfo_exists(self._tuner_win.window):
            try:
                self._tuner_win.window.lift()
                self._tuner_win.window.focus_force()
                return
            except Exception:
                pass
        
        try:
            self._tuner_win = TunerWindow(self)
            self.log("Afinador de guitarra aberto")
        except Exception as e:
            self.log(f"Erro ao abrir afinador: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao abrir afinador: {str(e)}")
    
    def open_settings(self) -> None:
        """Open the settings window."""
        if self._settings_win and hasattr(self._settings_win, 'window') and tk.Toplevel.winfo_exists(self._settings_win.window):
            try:
                self._settings_win.window.lift()
                self._settings_win.window.focus_force()
                return
            except Exception:
                pass
        
        try:
            self._settings_win = show_settings_window(self)
            self.log("Janela de configurações aberta")
        except Exception as e:
            self.log(f"Erro ao abrir configurações: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao abrir configurações: {str(e)}")
    
    def open_cipher_manager(self) -> None:
        """Open the Cipher Manager window."""
        try:
            cipher_manager = show_cipher_manager(self)
            self.log("Cipher Manager aberto")
        except Exception as e:
            self.log(f"Erro ao abrir Cipher Manager: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao abrir Cipher Manager: {str(e)}")
    
    def open_saved_songs(self) -> None:
        """Open the saved songs window."""
        try:
            self.show_saved_songs_window()
            self.log("Janela de músicas salvas aberta")
        except Exception as e:
            self.log(f"Erro ao abrir músicas salvas: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao abrir músicas salvas: {str(e)}")
    
    def save_selected_song(self) -> None:
        """Save selected search result to database with full content."""
        if not self.results:
            messagebox.showwarning("Aviso", "Nenhuma música encontrada para salvar!")
            return

        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma música para salvar!")
            return
        
        def _save_with_content():
            try:
                self.set_busy(True)
                self.status.set("Baixando conteúdo da música...")
                
                result = self.results[selection[0]]
                
                # Extract artist and title from the result
                title_parts = result.title.split(" - ", 1)
                if len(title_parts) == 2:
                    artist, title = title_parts
                else:
                    artist = "Desconhecido"
                    title = result.title
                
                # Fetch full content from the URL
                self.log(f"Baixando conteúdo de: {result.url}")
                try:
                    fetched_title, fetched_author, full_content = fetch_song(result.url)
                    if not full_content:
                        full_content = result.snippet or "Conteúdo não disponível"
                    # Update title and artist with fetched data if available
                    if fetched_title and fetched_title.strip():
                        title = fetched_title.strip()
                    if fetched_author and fetched_author.strip():
                        artist = fetched_author.strip()
                    self.log("Conteúdo baixado com sucesso")
                except Exception as e:
                    self.log(f"Erro ao baixar conteúdo, usando snippet: {str(e)}")
                    full_content = result.snippet or "Conteúdo não disponível"
                
                # Get current dork info
                current_dork = self._dorks[self.combo_dork.current()] if self._dorks else None
                search_query = self.entry_term.get()
                
                # Save to database with full content
                song_id = self.db.save_song(
                    title=title.strip(),
                    artist=artist.strip(),
                    url=result.url,
                    source="CifraClub" if "cifraclub.com.br" in result.url else "Web",
                    search_query=search_query,
                    chord_sequence=search_query if current_dork and current_dork.id == "chord_sequence" else None,
                    content=full_content,
                    tags=[current_dork.name] if current_dork else []
                )
                
                # Save search history
                if self.settings.get_bool('General', 'auto_save_searches', True):
                    self.db.save_search_history(
                        query=search_query,
                        dork_name=current_dork.name if current_dork else None,
                        results_count=len(self.results)
                    )
                
                self.log(f"Música salva no banco de dados: {title} (ID: {song_id})")
                self.status.set("Música salva com sucesso!")
                messagebox.showinfo("Sucesso", f"Música '{title}' salva com sucesso!\nConteúdo completo armazenado localmente.")
                
            except Exception as e:
                self.log(f"Erro ao salvar música: {str(e)}")
                messagebox.showerror("Erro", f"Erro ao salvar música: {str(e)}")
                self.status.set("Erro ao salvar música")
            finally:
                self.set_busy(False)
        
        # Run in background thread
        threading.Thread(target=_save_with_content, daemon=True).start()
    
    def save_all_songs(self) -> None:
        """Save all search results to database."""
        if not self.results:
            messagebox.showwarning("Aviso", "Nenhum resultado para salvar!")
            return
        
        if not messagebox.askyesno("Confirmar", f"Salvar todas as {len(self.results)} músicas no banco de dados?\n\nIsso pode demorar alguns minutos para baixar todo o conteúdo."):
            return
        
        def _save_all_with_content():
            try:
                self.set_busy(True)
                saved_count = 0
                current_dork = self._dorks[self.combo_dork.current()] if self._dorks else None
                search_query = self.entry_term.get()
                total_songs = len(self.results)
                
                for i, result in enumerate(self.results):
                    try:
                        self.status.set(f"Salvando música {i+1}/{total_songs}: {result.title}...")
                        
                        # Extract artist and title
                        title_parts = result.title.split(" - ", 1)
                        if len(title_parts) == 2:
                            artist, title = title_parts
                        else:
                            artist = "Desconhecido"
                            title = result.title
                        
                        # Fetch full content from the URL
                        self.log(f"Baixando conteúdo de: {result.url}")
                        try:
                            fetched_title, fetched_author, full_content = fetch_song(result.url)
                            if not full_content:
                                full_content = result.snippet or "Conteúdo não disponível"
                            # Update title and artist with fetched data if available
                            if fetched_title and fetched_title.strip():
                                title = fetched_title.strip()
                            if fetched_author and fetched_author.strip():
                                artist = fetched_author.strip()
                        except Exception as e:
                            self.log(f"Erro ao baixar conteúdo de '{title}', usando snippet: {str(e)}")
                            full_content = result.snippet or "Conteúdo não disponível"
                        
                        # Save to database with full content
                        self.db.save_song(
                            title=title.strip(),
                            artist=artist.strip(),
                            url=result.url,
                            source="CifraClub" if "cifraclub.com.br" in result.url else "Web",
                            search_query=search_query,
                            chord_sequence=search_query if current_dork and current_dork.id == "chord_sequence" else None,
                            content=full_content,
                            tags=[current_dork.name] if current_dork else []
                        )
                        
                        saved_count += 1
                        self.log(f"Música salva: {title}")
                        
                    except Exception as e:
                        self.log(f"Erro ao salvar música '{result.title}': {str(e)}")
                
                # Save search history
                if self.settings.get_bool('General', 'auto_save_searches', True):
                    self.db.save_search_history(
                        query=search_query,
                        dork_name=current_dork.name if current_dork else None,
                        results_count=len(self.results)
                    )
                
                self.log(f"{saved_count} músicas salvas no banco de dados com conteúdo completo")
                self.status.set(f"{saved_count} músicas salvas com sucesso!")
                messagebox.showinfo("Sucesso", f"{saved_count} de {total_songs} músicas salvas com sucesso!\nConteúdo completo armazenado localmente.")
                
            except Exception as e:
                self.log(f"Erro ao salvar músicas: {str(e)}")
                messagebox.showerror("Erro", f"Erro ao salvar músicas: {str(e)}")
                self.status.set("Erro ao salvar músicas")
            finally:
                self.set_busy(False)
        
        # Run in background thread
        threading.Thread(target=_save_all_with_content, daemon=True).start()
    
    def show_saved_songs_window(self) -> None:
        """Show window with saved songs from database."""
        # Create window
        songs_window = tk.Toplevel(self)
        songs_window.title("💾 Músicas Salvas")
        songs_window.geometry("900x600")
        songs_window.resizable(True, True)
        
        # Search frame
        search_frame = tk.Frame(songs_window)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Buscar:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        favorites_var = tk.BooleanVar()
        tk.Checkbutton(search_frame, text="Apenas favoritas", 
                      variable=favorites_var).pack(side=tk.LEFT, padx=(10, 0))
        
        # Songs list
        list_frame = tk.Frame(songs_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview for better display
        columns = ("ID", "Título", "Artista", "Fonte", "Acessos", "Última Vez", "Favorita")
        songs_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        songs_tree.heading("ID", text="ID")
        songs_tree.heading("Título", text="Título")
        songs_tree.heading("Artista", text="Artista")
        songs_tree.heading("Fonte", text="Fonte")
        songs_tree.heading("Acessos", text="Acessos")
        songs_tree.heading("Última Vez", text="Última Vez")
        songs_tree.heading("Favorita", text="⭐")
        
        songs_tree.column("ID", width=50)
        songs_tree.column("Título", width=200)
        songs_tree.column("Artista", width=150)
        songs_tree.column("Fonte", width=100)
        songs_tree.column("Acessos", width=80)
        songs_tree.column("Última Vez", width=120)
        songs_tree.column("Favorita", width=50)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=songs_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=songs_tree.xview)
        songs_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        songs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Buttons frame
        buttons_frame = tk.Frame(songs_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def refresh_songs():
            """Refresh the songs list."""
            # Clear existing items
            for item in songs_tree.get_children():
                songs_tree.delete(item)
            
            try:
                # Get songs from database
                search_term = search_var.get().strip()
                favorites_only = favorites_var.get()
                
                songs = self.db.get_songs(
                    limit=50000,
                    search_term=search_term if search_term else None,
                    favorites_only=favorites_only
                )
                
                # Populate tree
                for song in songs:
                    values = (
                        song['id'],
                        song['title'],
                        song['artist'] or "Desconhecido",
                        song['source'] or "Web",
                        song['access_count'],
                        song['last_accessed'][:16] if song['last_accessed'] else "",
                        "⭐" if song['is_favorite'] else ""
                    )
                    songs_tree.insert("", tk.END, values=values)
                
                status_label.config(text=f"{len(songs)} músicas encontradas")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar músicas: {str(e)}")
        
        def toggle_favorite():
            """Toggle favorite status of selected song."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            try:
                item = songs_tree.item(selection[0])
                song_id = item['values'][0]
                
                is_favorite = self.db.toggle_favorite(song_id)
                status = "adicionada aos" if is_favorite else "removida dos"
                messagebox.showinfo("Favoritos", f"Música {status} favoritos!")
                
                refresh_songs()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao alterar favorito: {str(e)}")
        
        def delete_song():
            """Delete selected song."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            item = songs_tree.item(selection[0])
            song_title = item['values'][1]
            
            if messagebox.askyesno("Confirmar", f"Excluir a música '{song_title}'?"):
                try:
                    song_id = item['values'][0]
                    if self.db.delete_song(song_id):
                        messagebox.showinfo("Sucesso", "Música excluída com sucesso!")
                        refresh_songs()
                    else:
                        messagebox.showerror("Erro", "Música não encontrada!")
                        
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao excluir música: {str(e)}")
        
        def open_song_url():
            """Open selected song URL in browser."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            try:
                item = songs_tree.item(selection[0])
                song_id = item['values'][0]
                song = self.db.get_song_by_id(song_id)
                
                if song and song['url']:
                    webbrowser.open(song['url'])
                else:
                    messagebox.showerror("Erro", "URL não encontrada!")
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao abrir URL: {str(e)}")
        
        def view_song_content():
            """View selected song content in internal viewer."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            try:
                item = songs_tree.item(selection[0])
                song_id = item['values'][0]
                song = self.db.get_song_by_id(song_id)
                
                if not song:
                    messagebox.showerror("Erro", "Música não encontrada!")
                    return
                
                # Create content viewer window
                viewer_window = tk.Toplevel(songs_window)
                viewer_window.title(f"👁️ {song['title']} - {song['artist']}")
                viewer_window.geometry("800x600")
                viewer_window.resizable(True, True)
                
                # Info frame
                info_frame = tk.Frame(viewer_window)
                info_frame.pack(fill=tk.X, padx=10, pady=10)
                
                tk.Label(info_frame, text=f"Título: {song['title']}", font=("Arial", 12, "bold")).pack(anchor="w")
                tk.Label(info_frame, text=f"Artista: {song['artist'] or 'Desconhecido'}", font=("Arial", 10)).pack(anchor="w")
                tk.Label(info_frame, text=f"Fonte: {song['source'] or 'Web'}", font=("Arial", 10)).pack(anchor="w")
                tk.Label(info_frame, text=f"URL: {song['url']}", font=("Arial", 9), fg="blue").pack(anchor="w")
                
                # Content frame
                content_frame = tk.Frame(viewer_window)
                content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
                
                # Text widget with scrollbar
                text_widget = tk.Text(content_frame, wrap=tk.WORD, font=("Courier", 10))
                text_scrollbar = tk.Scrollbar(content_frame, orient=tk.VERTICAL, command=text_widget.yview)
                text_widget.configure(yscrollcommand=text_scrollbar.set)
                
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Insert content
                content = song['content'] or "Conteúdo não disponível"
                text_widget.insert(tk.END, content)
                text_widget.config(state=tk.DISABLED)  # Make read-only
                
                # Buttons frame
                viewer_buttons = tk.Frame(viewer_window)
                viewer_buttons.pack(fill=tk.X, padx=10, pady=(0, 10))
                
                tk.Button(viewer_buttons, text="🌐 Abrir URL Original", 
                         command=lambda: webbrowser.open(song['url'])).pack(side=tk.LEFT)
                tk.Button(viewer_buttons, text="📋 Copiar Conteúdo", 
                         command=lambda: viewer_window.clipboard_clear() or viewer_window.clipboard_append(content)).pack(side=tk.LEFT, padx=(10, 0))
                
                # Center window
                viewer_window.update_idletasks()
                width = viewer_window.winfo_width()
                height = viewer_window.winfo_height()
                x = (viewer_window.winfo_screenwidth() // 2) - (width // 2)
                y = (viewer_window.winfo_screenheight() // 2) - (height // 2)
                viewer_window.geometry(f"{width}x{height}+{x}+{y}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao visualizar música: {str(e)}")
        
        def export_song_pdf():
            """Export selected song to PDF."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            try:
                item = songs_tree.item(selection[0])
                song_id = item['values'][0]
                song = self.db.get_song_by_id(song_id)
                
                if not song:
                    messagebox.showerror("Erro", "Música não encontrada!")
                    return
                
                # Ask for save location
                filename = sanitize_filename(f"{song['artist']} - {song['title']}")
                filepath = filedialog.asksaveasfilename(
                    title="Salvar PDF",
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                    initialvalue=f"{filename}.pdf"
                )
                
                if not filepath:
                    return
                
                # Check if it's a CifraClub URL for direct PDF export
                if "cifraclub.com.br" in song['url']:
                    def _export_pdf():
                        try:
                            self.set_busy(True)
                            self.status.set(f"Exportando PDF: {song['title']}")
                            
                            # Try to download PDF from CifraClub
                            download_cifraclub_pdf_alternative(song['url'], filepath)
                            
                            self.status.set("PDF exportado com sucesso!")
                            messagebox.showinfo("Sucesso", f"PDF salvo em:\n{filepath}")
                            
                        except Exception as e:
                            messagebox.showerror("Erro", f"Erro ao exportar PDF: {str(e)}")
                            self.status.set("Erro ao exportar PDF")
                        finally:
                            self.set_busy(False)
                    
                    threading.Thread(target=_export_pdf, daemon=True).start()
                else:
                    messagebox.showinfo("Aviso", "Export PDF disponível apenas para URLs do CifraClub.\nUse Export XML para outras fontes.")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar PDF: {str(e)}")
        
        def export_song_xml():
            """Export selected song to XML."""
            selection = songs_tree.selection()
            if not selection:
                messagebox.showwarning("Aviso", "Selecione uma música!")
                return
            
            try:
                item = songs_tree.item(selection[0])
                song_id = item['values'][0]
                song = self.db.get_song_by_id(song_id)
                
                if not song:
                    messagebox.showerror("Erro", "Música não encontrada!")
                    return
                
                # Ask for save location
                filename = sanitize_filename(f"{song['artist']} - {song['title']}")
                filepath = filedialog.asksaveasfilename(
                    title="Salvar XML",
                    defaultextension=".xml",
                    filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
                    initialvalue=f"{filename}.xml"
                )
                
                if not filepath:
                    return
                
                def _export_xml():
                    try:
                        self.set_busy(True)
                        self.status.set(f"Exportando XML: {song['title']}")
                        
                        # Build XML from stored content
                        xml_content = build_opensong_xml(
                            title=song['title'],
                            artist=song['artist'] or "Desconhecido",
                            lyrics=song['content'] or "Conteúdo não disponível"
                        )
                        
                        # Save XML file
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(xml_content)
                        
                        self.status.set("XML exportado com sucesso!")
                        messagebox.showinfo("Sucesso", f"XML salvo em:\n{filepath}")
                        
                    except Exception as e:
                        messagebox.showerror("Erro", f"Erro ao exportar XML: {str(e)}")
                        self.status.set("Erro ao exportar XML")
                    finally:
                        self.set_busy(False)
                
                threading.Thread(target=_export_xml, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar XML: {str(e)}")
        
        # Buttons
        tk.Button(buttons_frame, text="🔄 Atualizar", command=refresh_songs).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="👁️ Ver Música", command=lambda: view_song_content()).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons_frame, text="📄 Export PDF", command=lambda: export_song_pdf()).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons_frame, text="📝 Export XML", command=lambda: export_song_xml()).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons_frame, text="⭐ Favoritar/Desfavoritar", command=toggle_favorite).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons_frame, text="🌐 Abrir URL", command=open_song_url).pack(side=tk.LEFT, padx=(10, 0))
        tk.Button(buttons_frame, text="🗑️ Excluir", command=delete_song).pack(side=tk.LEFT, padx=(10, 0))
        
        # Status label
        status_label = tk.Label(buttons_frame, text="")
        status_label.pack(side=tk.RIGHT)
        
        # Bind search
        def on_search_change(*args):
            refresh_songs()
        
        search_var.trace('w', on_search_change)
        favorites_var.trace('w', on_search_change)
        
        # Initial load
        refresh_songs()
        
        # Center window
        songs_window.update_idletasks()
        width = songs_window.winfo_width()
        height = songs_window.winfo_height()
        x = (songs_window.winfo_screenwidth() // 2) - (width // 2)
        y = (songs_window.winfo_screenheight() // 2) - (height // 2)
        songs_window.geometry(f"{width}x{height}+{x}+{y}")

    def on_tab_changed(self, _event: object) -> None:
        # No-op; legacy tabs removed
        pass

    def _get_selected_result(self, _tab: str) -> tuple[SearchResult, str] | None:
        sel = self.listbox.curselection()
        if not sel:
            return None
        r = self.results[sel[0]]
        return r, r.url

    def _open_selected_url(self, tab: str) -> None:
        item = self._get_selected_result(tab)
        if not item:
            return
        _res, url = item
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def _copy_selected_url(self, tab: str) -> None:
        item = self._get_selected_result(tab)
        if not item:
            return
        _res, url = item
        try:
            self.clipboard_clear()
            self.clipboard_append(url)
        except Exception:
            pass

    def _show_context_menu(self, event: tk.Event, _tab: str) -> None:  # type: ignore[name-defined]
        try:
            lb = event.widget  # type: ignore[assignment]
            index = lb.nearest(event.y)
            if index >= 0:
                lb.selection_clear(0, tk.END)
                lb.selection_set(index)
        except Exception:
            pass
        menu = self.menu_results
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _download_url(self, url: str, dest_path: str, filetype: str) -> None:
        import requests
        from bs4 import BeautifulSoup
        # Try direct download when URL already looks like file
        if url.lower().endswith("." + filetype):
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return
        # Otherwise, fetch page and look for first link ending with the extension
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        target = None
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            if href.lower().endswith("." + filetype):
                target = href
                break
        if not target:
            raise RuntimeError(f"Não encontrei link .{filetype} na página")
        if target.startswith("/") and "://" not in target:
            # build absolute from base
            from urllib.parse import urljoin
            target = urljoin(url, target)
        with requests.get(target, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    def on_download_book(self) -> None:
        sel = self.listbox_books.curselection()
        if not sel:
            messagebox.showinfo("Selecione", "Selecione um livro na aba Livros.")
            return
        result = self.results_books[sel[0]]
        file_path = filedialog.asksaveasfilename(
            defaultextension=".epub",
            filetypes=[("EPUB", "*.epub"), ("Todos", "*.*")],
            title="Salvar livro como",
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".epub"):
            file_path = file_path + ".epub"

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Baixando livro...")
                self._download_url(result.url, file_path, "epub")
                self.status.set("Livro salvo")
                messagebox.showinfo("Sucesso", f"Livro salvo: {file_path}")
            except Exception as exc:
                messagebox.showerror("Erro", str(exc))
                self.status.set("Erro ao baixar livro")
            finally:
                self.set_busy(False)

        threading.Thread(target=_run, daemon=True).start()

    def on_download_music(self) -> None:
        sel = self.listbox_music.curselection()
        if not sel:
            messagebox.showinfo("Selecione", "Selecione uma música na aba Música.")
            return
        result = self.results_music[sel[0]]
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3", "*.mp3"), ("Todos", "*.*")],
            title="Salvar música como",
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".mp3"):
            file_path = file_path + ".mp3"

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Baixando música...")
                self._download_url(result.url, file_path, "mp3")
                self.status.set("Música salva")
                messagebox.showinfo("Sucesso", f"Música salva: {file_path}")
            except Exception as exc:
                messagebox.showerror("Erro", str(exc))
                self.status.set("Erro ao baixar música")
            finally:
                self.set_busy(False)

        threading.Thread(target=_run, daemon=True).start()

    def on_export(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Selecione", "Selecione um resultado para exportar.")
            return
        result = self.results[sel[0]]

        # Check if it's a CifraClub URL to decide between PDF or XML
        is_cifraclub = "cifraclub.com.br" in result.url
        
        self.log(f"Exportando: {result.title}")
        self.log(f"URL: {result.url}")
        self.log(f"É CifraClub: {'Sim' if is_cifraclub else 'Não'}")
        
        if is_cifraclub:
            # For CifraClub, save as PDF
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
                title="Salvar cifra como PDF",
            )
            if not file_path:
                return

            def _run_pdf() -> None:
                try:
                    self.set_busy(True)
                    self.status.set("Baixando PDF da cifra...")
                    self.log("Método de export: PDF (CifraClub)")
                    
                    # Auto-append .pdf if user omitted extension
                    if not file_path.lower().endswith(".pdf"):
                        file_path_local = file_path + ".pdf"
                    else:
                        file_path_local = file_path
                    
                    self.log(f"Salvando em: {file_path_local}")
                    
                    # Try pdfkit first, fallback to playwright
                    try:
                        self.log("Usando Playwright para gerar PDF")
                        download_cifraclub_pdf(result.url, file_path_local)
                    except RuntimeError as e:
                        self.log(f"Erro no método principal: {str(e)}")
                        if "pdfkit" in str(e):
                            # Fallback to Playwright
                            self.status.set("Tentando método alternativo...")
                            self.log("Tentando método alternativo...")
                            download_cifraclub_pdf_alternative(result.url, file_path_local)
                        else:
                            raise
                    
                    self.status.set("PDF salvo")
                    self.log("PDF salvo com sucesso")
                    messagebox.showinfo("Sucesso", f"PDF salvo: {file_path_local}")
                except Exception as exc:
                    error_msg = f"Erro ao baixar PDF: {str(exc)}"
                    self.log(error_msg)
                    messagebox.showerror("Erro", str(exc))
                    self.status.set("Erro ao baixar PDF")
                finally:
                    self.set_busy(False)

            threading.Thread(target=_run_pdf, daemon=True).start()
        else:
            # For other sites, keep XML export
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xml",
                filetypes=[("OpenSong XML", "*.xml"), ("Todos", "*.*")],
                title="Salvar como XML",
            )
            if not file_path:
                return

            def _run_xml() -> None:
                try:
                    self.set_busy(True)
                    self.status.set("Baixando e gerando XML...")
                    self.log("Método de export: XML (OpenSong)")
                    self.log("Modo dinâmico: Desativado")
                    
                    title, author, lyrics = fetch_song(
                        result.url,
                        use_dynamic=False,
                    )
                    
                    self.log(f"Título extraído: {title}")
                    self.log(f"Autor extraído: {author}")
                    
                    # Auto-append .xml if user omitted extension
                    if not file_path.lower().endswith(".xml"):
                        file_path_local = file_path + ".xml"
                    else:
                        file_path_local = file_path
                    
                    self.log(f"Salvando em: {file_path_local}")
                    
                    xml_content = build_opensong_xml(title, author, lyrics)
                    save_song(file_path_local, xml_content)
                    self.status.set("Arquivo salvo")
                    self.log("XML salvo com sucesso")
                    messagebox.showinfo("Sucesso", f"Arquivo salvo: {file_path_local}")
                except Exception as exc:
                    error_msg = f"Erro ao salvar XML: {str(exc)}"
                    self.log(error_msg)
                    messagebox.showerror("Erro", str(exc))
                    self.status.set("Erro ao exportar")
                finally:
                    self.set_busy(False)

            threading.Thread(target=_run_xml, daemon=True).start()

    def on_export_all(self) -> None:
        if not self.results:
            messagebox.showinfo("Sem resultados", "Faça uma busca antes de exportar.")
            return

        folder = filedialog.askdirectory(title="Escolher pasta para salvar todos")
        if not folder:
            return

        from pathlib import Path
        dest = Path(folder)

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Exportando todos...")
                ok = 0
                total = len(self.results)
                
                for i, r in enumerate(self.results):
                    try:
                        self.status.set(f"Exportando {i+1}/{total}...")
                        
                        # Check if it's CifraClub for PDF or other for XML
                        is_cifraclub = "cifraclub.com.br" in r.url
                        
                        if is_cifraclub:
                            # Save as PDF
                            filename = sanitize_filename(r.title or "cifra") + ".pdf"
                            out_path = dest / filename
                            
                            # Try pdfkit first, fallback to playwright
                            try:
                                download_cifraclub_pdf(r.url, str(out_path))
                            except RuntimeError as e:
                                if "pdfkit" in str(e):
                                    download_cifraclub_pdf_alternative(r.url, str(out_path))
                                else:
                                    raise
                        else:
                            # Save as XML
                            title, author, lyrics = fetch_song(
                                r.url,
                                use_dynamic=False,
                            )
                            filename = (title or r.title).strip()
                            if not filename:
                                filename = "song"
                            # sanitize like CLI
                            safe = sanitize_filename(filename) + ".xml"
                            out_path = dest / safe
                            xml_content = build_opensong_xml(title, author, lyrics)
                            save_song(str(out_path), xml_content)
                        
                        ok += 1
                    except Exception:
                        # Continue with others
                        pass
                        
                self.status.set(f"Exportados: {ok}/{total}")
                messagebox.showinfo("Concluído", f"Exportados: {ok}/{total}")
            except Exception as exc:
                messagebox.showerror("Erro", str(exc))
                self.status.set("Erro ao exportar todos")
            finally:
                self.set_busy(False)

        threading.Thread(target=_run, daemon=True).start()

    def on_action_for_current(self) -> None:
        # Decide based on selected dork whether to export XML (cifras) or download file (filetype)
        dork_index = self.combo_dork.current() if self.combo_dork is not None else -1
        if dork_index < 0 or dork_index >= len(self._dorks):
            messagebox.showwarning("Dork", "Selecione um dork válido.")
            return
        d = self._dorks[dork_index]
        if d.filetype is None and ("cifraclub.com.br" in (d.query or "") or d.id == "chords" or d.id == "chord_sequence"):
            self.on_export()
        else:
            # Download according to filetype
            sel = self.listbox.curselection()
            if not sel:
                messagebox.showinfo("Selecione", "Selecione um resultado para salvar.")
                return
            result = self.results[sel[0]]
            ext = (d.filetype or "").lower().strip(".") or "bin"
            filetypes = [(ext.upper(), f"*.{ext}"), ("Todos", "*.*")]
            file_path = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                filetypes=filetypes,
                title="Salvar arquivo como",
            )
            if not file_path:
                return
            if not file_path.lower().endswith(f".{ext}"):
                file_path = file_path + f".{ext}"

            def _run() -> None:
                try:
                    self.set_busy(True)
                    self.status.set("Baixando arquivo...")
                    self._download_url(result.url, file_path, ext)
                    self.status.set("Arquivo salvo")
                    messagebox.showinfo("Sucesso", f"Arquivo salvo: {file_path}")
                except Exception as exc:
                    messagebox.showerror("Erro", str(exc))
                    self.status.set("Erro ao salvar arquivo")
                finally:
                    self.set_busy(False)

            threading.Thread(target=_run, daemon=True).start()

    def on_action_all_for_current(self) -> None:
        dork_index = self.combo_dork.current() if self.combo_dork is not None else -1
        if dork_index < 0 or dork_index >= len(self._dorks):
            messagebox.showwarning("Dork", "Selecione um dork válido.")
            return
        d = self._dorks[dork_index]
        if d.filetype is None and ("cifraclub.com.br" in (d.query or "") or d.id == "chords" or d.id == "chord_sequence"):
            self.on_export_all()
            return
        if not self.results:
            messagebox.showinfo("Sem resultados", "Faça uma busca antes de salvar.")
            return
        folder = filedialog.askdirectory(title="Escolher pasta para salvar todos")
        if not folder:
            return
        from pathlib import Path
        dest = Path(folder)
        ext = (d.filetype or "").lower().strip(".") or "bin"

        def _run() -> None:
            try:
                self.set_busy(True)
                self.status.set("Salvando todos...")
                ok = 0
                for r in self.results:
                    try:
                        # Make filename from title
                        filename = sanitize_filename(r.title or "file") + f".{ext}"
                        out_path = dest / filename
                        self._download_url(r.url, str(out_path), ext)
                        ok += 1
                    except Exception:
                        pass
                self.status.set(f"Salvos: {ok}/{len(self.results)}")
                messagebox.showinfo("Concluído", f"Salvos: {ok}/{len(self.results)}")
            except Exception as exc:
                messagebox.showerror("Erro", str(exc))
                self.status.set("Erro ao salvar todos")
            finally:
                self.set_busy(False)

        threading.Thread(target=_run, daemon=True).start()


def run() -> None:
    # Load .env if available
    if _load_dotenv:
        try:
            _load_dotenv()
        except Exception:
            pass
    # Check if API key is configured
    try:
        from chord_importer.settings import get_settings
        settings = get_settings()
        api_key = settings.get_serper_api_key()
        if not api_key and not os.environ.get("SERPER_API_KEY"):
            messagebox.showwarning(
                "API Key Não Configurada",
                "Configure sua chave API do Serper nas configurações (⚙️) para habilitar a busca avançada.\n\n"
                "Alternativamente, você pode definir a variável de ambiente SERPER_API_KEY.",
            )
    except Exception:
        # Fallback to old behavior
        if not os.environ.get("SERPER_API_KEY"):
            messagebox.showwarning(
                "SERPER_API_KEY",
                "Configure sua chave API do Serper nas configurações (⚙️) para habilitar a busca.",
            )
    app = App()
    app.mainloop()


# Allow: python -m chord_importer.gui
if __name__ == "__main__":
    run()

