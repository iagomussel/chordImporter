from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Dork:
    id: str
    name: str
    query: str  # May include {term}
    filetype: Optional[str] = None
    limit: int = 10
    country: str = "br"
    language: str = "pt-br"


def _store_path() -> Path:
    # Persist in user home to survive project updates
    return Path.home() / ".chord_importer_dorks.json"


def _defaults() -> List[Dork]:
    return [
        Dork(id="chords", name="Cifras (CifraClub)", query="site:cifraclub.com.br {term}", filetype=None),
        Dork(id="chord_sequence", name="Sequência de Acordes", query="chord_sequence:{term}", filetype=None),
        Dork(id="books", name="Livros (EPUB)", query="{term} filetype:epub", filetype="epub"),
        Dork(id="music", name="Música (MP3)", query="{term} filetype:mp3", filetype="mp3"),
    ]


def load_dorks() -> List[Dork]:
    path = _store_path()
    if not path.exists():
        dorks = _defaults()
        save_dorks(dorks)
        return dorks
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        dorks: List[Dork] = []
        for item in data if isinstance(data, list) else []:
            try:
                dorks.append(
                    Dork(
                        id=str(item.get("id") or str(uuid.uuid4())),
                        name=str(item.get("name") or "Unnamed"),
                        query=str(item.get("query") or "{term}"),
                        filetype=item.get("filetype") or None,
                        limit=int(item.get("limit") or 10),
                        country=str(item.get("country") or "br"),
                        language=str(item.get("language") or "pt-br"),
                    )
                )
            except Exception:
                continue
        
        # Check for missing default dorks and add them
        existing_ids = {d.id for d in dorks}
        defaults = _defaults()
        default_ids = {d.id for d in defaults}
        missing_ids = default_ids - existing_ids
        
        if missing_ids:
            # Add missing default dorks
            for default_dork in defaults:
                if default_dork.id in missing_ids:
                    dorks.append(default_dork)
            save_dorks(dorks)
        
        if not dorks:
            dorks = _defaults()
            save_dorks(dorks)
        return dorks
    except Exception:
        dorks = _defaults()
        save_dorks(dorks)
        return dorks


def save_dorks(dorks: List[Dork]) -> None:
    path = _store_path()
    payload = [asdict(d) for d in dorks]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def add_dork(name: str, query: str, filetype: Optional[str] = None, limit: int = 10, country: str = "br", language: str = "pt-br") -> Dork:
    dorks = load_dorks()
    new = Dork(id=str(uuid.uuid4()), name=name, query=query, filetype=filetype, limit=limit, country=country, language=language)
    dorks.append(new)
    save_dorks(dorks)
    return new


def update_dork(updated: Dork) -> None:
    dorks = load_dorks()
    for i, d in enumerate(dorks):
        if d.id == updated.id:
            dorks[i] = updated
            break
    save_dorks(dorks)


def delete_dork(dork_id: str) -> None:
    dorks = load_dorks()
    dorks = [d for d in dorks if d.id != dork_id]
    save_dorks(dorks)


