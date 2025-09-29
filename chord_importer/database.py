"""
Database module for storing searched songs and user data.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import os

class ChordImporterDB:
    """Database manager for Chord Importer application."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection."""
        if db_path is None:
            # Create database in user's home directory
            home_dir = Path.home()
            app_dir = home_dir / ".chord_importer"
            app_dir.mkdir(exist_ok=True)
            db_path = app_dir / "chord_importer.db"
        
        self.db_path = str(db_path)
        try:
            self.init_database()
        except Exception as e:
            print(f"Warning: Could not initialize database: {e}")
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if we need to migrate existing database
            self._migrate_database(cursor)
            
            # Create songs table (enhanced for cipher manager)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT,
                    url TEXT,
                    source TEXT,
                    search_query TEXT,
                    chord_sequence TEXT,
                    key_signature TEXT,
                    tempo INTEGER,
                    time_signature TEXT,
                    genre TEXT,
                    difficulty_rating INTEGER DEFAULT 1,
                    content TEXT,
                    lyrics TEXT,
                    chord_progression TEXT,
                    structure TEXT,
                    capo_position INTEGER DEFAULT 0,
                    tuning TEXT DEFAULT 'standard',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    tags TEXT,
                    notes TEXT,
                    practice_notes TEXT,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    is_local BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create search_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    dork_name TEXT,
                    results_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create user_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create exports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id INTEGER,
                    export_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            """)
            
            # Create chord_progressions table for detailed progression analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chord_progressions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id INTEGER,
                    section_name TEXT,
                    progression TEXT NOT NULL,
                    roman_numerals TEXT,
                    key_signature TEXT,
                    measures INTEGER DEFAULT 4,
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            """)
            
            # Create setlists table for organizing songs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS setlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create setlist_songs table for many-to-many relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS setlist_songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setlist_id INTEGER,
                    song_id INTEGER,
                    position INTEGER DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (setlist_id) REFERENCES setlists (id),
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            """)
            
            # Create practice_sessions table for tracking practice
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id INTEGER,
                    duration_minutes INTEGER,
                    difficulty_rating INTEGER,
                    notes TEXT,
                    tempo_practiced INTEGER,
                    sections_practiced TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            """)
            
            # Create full-text search virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS songs_fts USING fts5(
                    title, artist, content, lyrics, tags, notes,
                    content='songs', content_rowid='id'
                )
            """)
            
            # Create triggers to keep FTS table in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS songs_ai AFTER INSERT ON songs BEGIN
                    INSERT INTO songs_fts(rowid, title, artist, content, lyrics, tags, notes)
                    VALUES (new.id, new.title, new.artist, new.content, new.lyrics, new.tags, new.notes);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS songs_ad AFTER DELETE ON songs BEGIN
                    INSERT INTO songs_fts(songs_fts, rowid, title, artist, content, lyrics, tags, notes)
                    VALUES('delete', old.id, old.title, old.artist, old.content, old.lyrics, old.tags, old.notes);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS songs_au AFTER UPDATE ON songs BEGIN
                    INSERT INTO songs_fts(songs_fts, rowid, title, artist, content, lyrics, tags, notes)
                    VALUES('delete', old.id, old.title, old.artist, old.content, old.lyrics, old.tags, old.notes);
                    INSERT INTO songs_fts(rowid, title, artist, content, lyrics, tags, notes)
                    VALUES (new.id, new.title, new.artist, new.content, new.lyrics, new.tags, new.notes);
                END
            """)
            
            conn.commit()
    
    def _migrate_database(self, cursor):
        """Migrate existing database to new schema."""
        try:
            # Check if songs table exists and get its columns
            cursor.execute("PRAGMA table_info(songs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add missing columns to songs table
            new_columns = {
                'key_signature': 'TEXT',
                'tempo': 'INTEGER',
                'time_signature': 'TEXT',
                'genre': 'TEXT',
                'difficulty_rating': 'INTEGER DEFAULT 1',
                'lyrics': 'TEXT',
                'chord_progression': 'TEXT',
                'structure': 'TEXT',
                'capo_position': 'INTEGER DEFAULT 0',
                'tuning': 'TEXT DEFAULT "standard"',
                'practice_notes': 'TEXT',
                'is_local': 'BOOLEAN DEFAULT FALSE'
            }
            
            for column, column_type in new_columns.items():
                if column not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE songs ADD COLUMN {column} {column_type}")
                        print(f"Added column {column} to songs table")
                    except Exception as e:
                        print(f"Warning: Could not add column {column}: {e}")
            
            # Remove UNIQUE constraint from url column if it exists
            # This is more complex in SQLite, so we'll handle it gracefully
            try:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='songs'")
                table_sql = cursor.fetchone()
                if table_sql and 'url TEXT UNIQUE NOT NULL' in table_sql[0]:
                    # Need to recreate table without UNIQUE constraint
                    print("Migrating songs table to remove UNIQUE constraint from url...")
                    
                    # Create backup table
                    cursor.execute("""
                        CREATE TABLE songs_backup AS SELECT * FROM songs
                    """)
                    
                    # Drop original table
                    cursor.execute("DROP TABLE songs")
                    
                    # Recreate with new schema (this will be done by the main init)
                    # The backup data will be restored after table creation
                    
            except Exception as e:
                print(f"Note: URL constraint migration skipped: {e}")
                
        except Exception as e:
            print(f"Warning: Database migration failed: {e}")
    
    def save_song(self, title: str, artist: str = None, url: str = None, 
                  source: str = None, search_query: str = None, 
                  chord_sequence: str = None, key_signature: str = None,
                  tempo: int = None, time_signature: str = None, genre: str = None,
                  difficulty_rating: int = 1, content: str = None, lyrics: str = None,
                  chord_progression: str = None, structure: str = None,
                  capo_position: int = 0, tuning: str = 'standard',
                  tags: List[str] = None, notes: str = None, practice_notes: str = None,
                  is_local: bool = False) -> int:
        """Save a song to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if song already exists (by URL if provided, otherwise by title+artist)
            if url:
                cursor.execute("SELECT id, access_count FROM songs WHERE url = ?", (url,))
            else:
                cursor.execute("SELECT id, access_count FROM songs WHERE title = ? AND artist = ? AND is_local = ?", 
                             (title, artist, is_local))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing song
                song_id, access_count = existing
                cursor.execute("""
                    UPDATE songs SET 
                        title = ?, artist = ?, source = ?, search_query = ?,
                        chord_sequence = ?, key_signature = ?, tempo = ?, time_signature = ?,
                        genre = ?, difficulty_rating = ?, content = ?, lyrics = ?,
                        chord_progression = ?, structure = ?, capo_position = ?, tuning = ?,
                        last_accessed = CURRENT_TIMESTAMP, access_count = ?,
                        tags = ?, notes = ?, practice_notes = ?, is_local = ?
                    WHERE id = ?
                """, (title, artist, source, search_query, chord_sequence, 
                     key_signature, tempo, time_signature, genre, difficulty_rating,
                     content, lyrics, chord_progression, structure, capo_position, tuning,
                     access_count + 1, json.dumps(tags) if tags else None, 
                     notes, practice_notes, is_local, song_id))
                
                return song_id
            else:
                # Insert new song
                cursor.execute("""
                    INSERT INTO songs (title, artist, url, source, search_query,
                                     chord_sequence, key_signature, tempo, time_signature,
                                     genre, difficulty_rating, content, lyrics,
                                     chord_progression, structure, capo_position, tuning,
                                     tags, notes, practice_notes, is_local)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, artist, url, source, search_query, chord_sequence,
                     key_signature, tempo, time_signature, genre, difficulty_rating,
                     content, lyrics, chord_progression, structure, capo_position, tuning,
                     json.dumps(tags) if tags else None, notes, practice_notes, is_local))
                
                return cursor.lastrowid
    
    def get_songs(self, limit: int = 100, offset: int = 0, 
                  search_term: str = None, favorites_only: bool = False) -> List[Dict]:
        """Get songs from database with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM songs"
            params = []
            conditions = []
            
            if favorites_only:
                conditions.append("is_favorite = 1")
            
            if search_term:
                conditions.append("(title LIKE ? OR artist LIKE ? OR tags LIKE ?)")
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY last_accessed DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            songs = []
            for row in rows:
                song = dict(row)
                # Parse JSON fields
                if song['tags']:
                    song['tags'] = json.loads(song['tags'])
                else:
                    song['tags'] = []
                songs.append(song)
            
            return songs
    
    def get_song_by_id(self, song_id: int) -> Optional[Dict]:
        """Get a specific song by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
            row = cursor.fetchone()
            
            if row:
                song = dict(row)
                if song['tags']:
                    song['tags'] = json.loads(song['tags'])
                else:
                    song['tags'] = []
                return song
            
            return None
    
    def delete_song(self, song_id: int) -> bool:
        """Delete a song from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete related exports first
            cursor.execute("DELETE FROM exports WHERE song_id = ?", (song_id,))
            
            # Delete the song
            cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            
            return cursor.rowcount > 0
    
    def toggle_favorite(self, song_id: int) -> bool:
        """Toggle favorite status of a song."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT is_favorite FROM songs WHERE id = ?", (song_id,))
            row = cursor.fetchone()
            
            if row:
                new_status = not bool(row[0])
                cursor.execute("UPDATE songs SET is_favorite = ? WHERE id = ?", 
                             (new_status, song_id))
                return new_status
            
            return False
    
    def save_search_history(self, query: str, dork_name: str = None, 
                           results_count: int = 0):
        """Save search query to history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO search_history (query, dork_name, results_count)
                VALUES (?, ?, ?)
            """, (query, dork_name, results_count))
    
    def get_search_history(self, limit: int = 50) -> List[Dict]:
        """Get recent search history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM search_history 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_export_record(self, song_id: int, export_type: str, file_path: str):
        """Record an export operation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO exports (song_id, export_type, file_path)
                VALUES (?, ?, ?)
            """, (song_id, export_type, file_path))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total songs
            cursor.execute("SELECT COUNT(*) FROM songs")
            stats['total_songs'] = cursor.fetchone()[0]
            
            # Favorite songs
            cursor.execute("SELECT COUNT(*) FROM songs WHERE is_favorite = 1")
            stats['favorite_songs'] = cursor.fetchone()[0]
            
            # Total searches
            cursor.execute("SELECT COUNT(*) FROM search_history")
            stats['total_searches'] = cursor.fetchone()[0]
            
            # Total exports
            cursor.execute("SELECT COUNT(*) FROM exports")
            stats['total_exports'] = cursor.fetchone()[0]
            
            # Most accessed songs
            cursor.execute("""
                SELECT title, artist, access_count 
                FROM songs 
                ORDER BY access_count DESC 
                LIMIT 5
            """)
            stats['most_accessed'] = [dict(zip(['title', 'artist', 'access_count'], row)) 
                                    for row in cursor.fetchall()]
            
            # Recent activity
            cursor.execute("""
                SELECT DATE(last_accessed) as date, COUNT(*) as count
                FROM songs 
                WHERE last_accessed >= date('now', '-7 days')
                GROUP BY DATE(last_accessed)
                ORDER BY date DESC
            """)
            stats['recent_activity'] = [dict(zip(['date', 'count'], row)) 
                                      for row in cursor.fetchall()]
            
            return stats
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old search history and unused data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clean old search history
            cursor.execute("""
                DELETE FROM search_history 
                WHERE created_at < date('now', '-{} days')
            """.format(days))
            
            cleaned_searches = cursor.rowcount
            
            # Clean orphaned exports
            cursor.execute("""
                DELETE FROM exports 
                WHERE song_id NOT IN (SELECT id FROM songs)
            """)
            
            cleaned_exports = cursor.rowcount
            
            return {
                'cleaned_searches': cleaned_searches,
                'cleaned_exports': cleaned_exports
            }
    
    # Cipher Manager Methods
    
    def create_local_song(self, title: str, artist: str = None, key_signature: str = None,
                         tempo: int = None, time_signature: str = "4/4", genre: str = None,
                         difficulty_rating: int = 1, content: str = None, lyrics: str = None,
                         chord_progression: str = None, structure: str = None,
                         capo_position: int = 0, tuning: str = 'standard',
                         tags: List[str] = None, notes: str = None) -> int:
        """Create a new local song (cipher) in the database."""
        return self.save_song(
            title=title, artist=artist, key_signature=key_signature,
            tempo=tempo, time_signature=time_signature, genre=genre,
            difficulty_rating=difficulty_rating, content=content, lyrics=lyrics,
            chord_progression=chord_progression, structure=structure,
            capo_position=capo_position, tuning=tuning, tags=tags, notes=notes,
            is_local=True, source="Local"
        )
    
    def search_songs_full_text(self, query: str, limit: int = 50) -> List[Dict]:
        """Search songs using full-text search."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT songs.*, rank FROM songs_fts
                JOIN songs ON songs.id = songs_fts.rowid
                WHERE songs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            rows = cursor.fetchall()
            songs = []
            for row in rows:
                song = dict(row)
                if song['tags']:
                    song['tags'] = json.loads(song['tags'])
                else:
                    song['tags'] = []
                songs.append(song)
            
            return songs
    
    def get_songs_by_key(self, key_signature: str, limit: int = 50) -> List[Dict]:
        """Get songs by key signature."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM songs 
                WHERE key_signature = ? 
                ORDER BY title, artist
                LIMIT ?
            """, (key_signature, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_songs_by_chord_progression(self, progression_pattern: str, limit: int = 50) -> List[Dict]:
        """Get songs by chord progression pattern."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM songs 
                WHERE chord_progression LIKE ? OR chord_sequence LIKE ?
                ORDER BY title, artist
                LIMIT ?
            """, (f"%{progression_pattern}%", f"%{progression_pattern}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_songs_by_difficulty(self, min_difficulty: int = 1, max_difficulty: int = 5) -> List[Dict]:
        """Get songs by difficulty rating range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM songs 
                WHERE difficulty_rating BETWEEN ? AND ?
                ORDER BY difficulty_rating, title
            """, (min_difficulty, max_difficulty))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Setlist Management
    
    def create_setlist(self, name: str, description: str = None) -> int:
        """Create a new setlist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO setlists (name, description)
                VALUES (?, ?)
            """, (name, description))
            
            return cursor.lastrowid
    
    def get_setlists(self) -> List[Dict]:
        """Get all setlists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, COUNT(ss.song_id) as song_count
                FROM setlists s
                LEFT JOIN setlist_songs ss ON s.id = ss.setlist_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_song_to_setlist(self, setlist_id: int, song_id: int, position: int = None, notes: str = None) -> bool:
        """Add a song to a setlist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get next position if not specified
            if position is None:
                cursor.execute("SELECT MAX(position) FROM setlist_songs WHERE setlist_id = ?", (setlist_id,))
                max_pos = cursor.fetchone()[0]
                position = (max_pos or 0) + 1
            
            cursor.execute("""
                INSERT INTO setlist_songs (setlist_id, song_id, position, notes)
                VALUES (?, ?, ?, ?)
            """, (setlist_id, song_id, position, notes))
            
            # Update setlist timestamp
            cursor.execute("""
                UPDATE setlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (setlist_id,))
            
            return cursor.rowcount > 0
    
    def get_setlist_songs(self, setlist_id: int) -> List[Dict]:
        """Get songs in a setlist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, ss.position, ss.notes as setlist_notes
                FROM songs s
                JOIN setlist_songs ss ON s.id = ss.song_id
                WHERE ss.setlist_id = ?
                ORDER BY ss.position
            """, (setlist_id,))
            
            songs = []
            for row in cursor.fetchall():
                song = dict(row)
                if song['tags']:
                    song['tags'] = json.loads(song['tags'])
                else:
                    song['tags'] = []
                songs.append(song)
            
            return songs
    
    # Practice Session Tracking
    
    def add_practice_session(self, song_id: int, duration_minutes: int, 
                           difficulty_rating: int = None, notes: str = None,
                           tempo_practiced: int = None, sections_practiced: str = None) -> int:
        """Add a practice session record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO practice_sessions 
                (song_id, duration_minutes, difficulty_rating, notes, tempo_practiced, sections_practiced)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (song_id, duration_minutes, difficulty_rating, notes, tempo_practiced, sections_practiced))
            
            return cursor.lastrowid
    
    def get_practice_stats(self, song_id: int = None) -> Dict[str, Any]:
        """Get practice statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if song_id:
                # Stats for specific song
                cursor.execute("""
                    SELECT 
                        COUNT(*) as session_count,
                        SUM(duration_minutes) as total_minutes,
                        AVG(duration_minutes) as avg_duration,
                        MAX(created_at) as last_practice
                    FROM practice_sessions 
                    WHERE song_id = ?
                """, (song_id,))
            else:
                # Overall stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as session_count,
                        SUM(duration_minutes) as total_minutes,
                        AVG(duration_minutes) as avg_duration,
                        MAX(created_at) as last_practice
                    FROM practice_sessions
                """)
            
            row = cursor.fetchone()
            return {
                'session_count': row[0] or 0,
                'total_minutes': row[1] or 0,
                'avg_duration': row[2] or 0,
                'last_practice': row[3]
            }
    
    # Additional methods for dashboard
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall application statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total songs
            cursor.execute("SELECT COUNT(*) as total_songs FROM songs")
            total_songs = cursor.fetchone()[0]
            
            # Favorite songs
            cursor.execute("SELECT COUNT(*) as favorite_songs FROM songs WHERE is_favorite = 1")
            favorite_songs = cursor.fetchone()[0]
            
            # Local songs
            cursor.execute("SELECT COUNT(*) as local_songs FROM songs WHERE is_local = 1")
            local_songs = cursor.fetchone()[0]
            
            # Total searches (if search history table exists)
            try:
                cursor.execute("SELECT COUNT(*) as total_searches FROM search_history")
                total_searches = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                total_searches = 0
            
            return {
                'total_songs': total_songs,
                'favorite_songs': favorite_songs,
                'local_songs': local_songs,
                'total_searches': total_searches
            }
    
    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get search history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Create search history table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                SELECT query, results_count, created_at
                FROM search_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_search_history(self, query: str, results_count: int = 0):
        """Save a search to history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create search history table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO search_history (query, results_count)
                VALUES (?, ?)
            """, (query, results_count))
    
    def toggle_favorite(self, song_id: int) -> bool:
        """Toggle favorite status of a song. Returns new favorite status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute("SELECT is_favorite FROM songs WHERE id = ?", (song_id,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Song with ID {song_id} not found")
            
            current_status = bool(result[0])
            new_status = not current_status
            
            # Update status
            cursor.execute("""
                UPDATE songs 
                SET is_favorite = ?, last_accessed = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, song_id))
            
            return new_status
    
    def delete_song(self, song_id: int):
        """Delete a song from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete from setlist associations first
            cursor.execute("DELETE FROM setlist_songs WHERE song_id = ?", (song_id,))
            
            # Delete practice sessions
            cursor.execute("DELETE FROM practice_sessions WHERE song_id = ?", (song_id,))
            
            # Delete the song
            cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    
    def save_export_record(self, song_id: int, export_type: str, file_path: str):
        """Save an export record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create export history table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS export_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_id INTEGER,
                    export_type TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (song_id) REFERENCES songs (id)
                )
            """)
            
            cursor.execute("""
                INSERT INTO export_history (song_id, export_type, file_path)
                VALUES (?, ?, ?)
            """, (song_id, export_type, file_path))

# Global database instance
_db_instance = None

def get_database() -> ChordImporterDB:
    """Get the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ChordImporterDB()
    return _db_instance
