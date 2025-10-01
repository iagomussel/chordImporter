"""
Audio Player - Real audio playback functionality for converted songs and audio files.
Follows audio dependency rules with proper error handling and no fallbacks.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import queue
from typing import Optional, Callable
import os

# Required audio libraries - NO FALLBACKS
import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa

# Verify critical dependencies are available
if not hasattr(np, 'zeros'):
    raise ImportError("numpy not properly installed")
if not hasattr(sd, 'OutputStream'):
    raise ImportError("sounddevice not properly installed")
if not hasattr(sf, 'read'):
    raise ImportError("soundfile not properly installed")
if not hasattr(librosa, 'load'):
    raise ImportError("librosa not properly installed")


class AudioPlayer:
    """
    Real audio playback system for converted songs and audio files.
    Implements proper audio output following dependency rules.
    """
    
    def __init__(self):
        """Initialize the audio player."""
        
        # Audio parameters
        self.sample_rate = 44100
        self.channels = 2
        self.buffer_size = 1024
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.total_duration = 0.0
        
        # Audio data
        self.audio_data = None
        self.current_file = None
        
        # Streaming
        self.audio_stream = None
        self.playback_thread = None
        self.audio_queue = queue.Queue()
        
        # Callbacks
        self.position_callback = None
        self.finished_callback = None
        
    def load_file(self, file_path: str) -> bool:
        """
        Load an audio file for playback.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Load audio file using soundfile (supports many formats)
            self.audio_data, self.sample_rate = sf.read(file_path, always_2d=True)
            
            # Ensure stereo output
            if self.audio_data.shape[1] == 1:
                # Convert mono to stereo
                self.audio_data = np.column_stack([self.audio_data, self.audio_data])
            elif self.audio_data.shape[1] > 2:
                # Convert multi-channel to stereo
                self.audio_data = self.audio_data[:, :2]
            
            self.channels = self.audio_data.shape[1]
            self.total_duration = len(self.audio_data) / self.sample_rate
            self.current_position = 0.0
            self.current_file = file_path
            
            return True
            
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return False
    
    def play(self) -> bool:
        """
        Start or resume audio playback.
        
        Returns:
            True if playback started successfully, False otherwise
        """
        if not self.audio_data is None and not self.is_playing:
            try:
                self.is_playing = True
                self.is_paused = False
                
                # Start audio stream
                self.audio_stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=self._audio_callback,
                    blocksize=self.buffer_size
                )
                
                self.audio_stream.start()
                
                # Start position tracking thread
                self.playback_thread = threading.Thread(target=self._position_tracker, daemon=True)
                self.playback_thread.start()
                
                return True
                
            except Exception as e:
                print(f"Error starting playback: {e}")
                self.is_playing = False
                return False
        
        return False
    
    def pause(self):
        """Pause audio playback."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
    
    def resume(self):
        """Resume audio playback."""
        if self.is_playing and self.is_paused:
            self.is_paused = False
    
    def stop(self):
        """Stop audio playback."""
        self.is_playing = False
        self.is_paused = False
        
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        
        self.current_position = 0.0
    
    def seek(self, position: float):
        """
        Seek to a specific position in the audio.
        
        Args:
            position: Position in seconds
        """
        if self.audio_data is not None:
            self.current_position = max(0, min(position, self.total_duration))
    
    def set_position_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for position updates.
        
        Args:
            callback: Function that receives (current_position, total_duration)
        """
        self.position_callback = callback
    
    def set_finished_callback(self, callback: Callable[[], None]):
        """
        Set callback for when playback finishes.
        
        Args:
            callback: Function called when playback ends
        """
        self.finished_callback = callback
    
    def get_position(self) -> float:
        """Get current playback position in seconds."""
        return self.current_position
    
    def get_duration(self) -> float:
        """Get total duration in seconds."""
        return self.total_duration
    
    def is_loaded(self) -> bool:
        """Check if an audio file is loaded."""
        return self.audio_data is not None
    
    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback for sounddevice output stream."""
        if status:
            print(f"Audio output status: {status}")
        
        if not self.is_playing or self.is_paused or self.audio_data is None:
            # Output silence
            outdata.fill(0)
            return
        
        try:
            # Calculate current sample position
            start_sample = int(self.current_position * self.sample_rate)
            end_sample = start_sample + frames
            
            # Check if we've reached the end
            if start_sample >= len(self.audio_data):
                outdata.fill(0)
                self.is_playing = False
                if self.finished_callback:
                    self.finished_callback()
                return
            
            # Get audio data for this chunk
            if end_sample <= len(self.audio_data):
                chunk = self.audio_data[start_sample:end_sample]
            else:
                # Handle end of file
                remaining_samples = len(self.audio_data) - start_sample
                chunk = np.zeros((frames, self.channels), dtype=np.float32)
                if remaining_samples > 0:
                    chunk[:remaining_samples] = self.audio_data[start_sample:]
                
                # Mark as finished
                self.is_playing = False
                if self.finished_callback:
                    self.finished_callback()
            
            # Copy to output buffer
            outdata[:] = chunk
            
            # Update position
            self.current_position += frames / self.sample_rate
            
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)
    
    def _position_tracker(self):
        """Track playback position and call position callback."""
        while self.is_playing:
            if self.position_callback and not self.is_paused:
                self.position_callback(self.current_position, self.total_duration)
            
            time.sleep(0.1)  # Update 10 times per second
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()


class AudioPlayerWidget(tk.Frame):
    """
    Tkinter widget for audio playback with controls.
    """
    
    def __init__(self, parent, **kwargs):
        """Initialize the audio player widget."""
        super().__init__(parent, **kwargs)
        
        
        self.player = AudioPlayer()
        self.player.set_position_callback(self._on_position_update)
        self.player.set_finished_callback(self._on_playback_finished)
        
        self._create_ui()
    
    def _create_error_ui(self):
        """Create error UI when audio libraries are not available."""
        error_label = tk.Label(
            self,
            text="⚠️ Audio playback not available\nRequired libraries not installed",
            font=("Arial", 12),
            fg="red",
            justify=tk.CENTER
        )
        error_label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
    
    def _create_ui(self):
        """Create the audio player UI."""
        # Control buttons frame
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Play/Pause button
        self.play_button = tk.Button(
            controls_frame,
            text="▶️",
            command=self._toggle_playback,
            font=("Arial", 14),
            width=3
        )
        self.play_button.pack(side=tk.LEFT, padx=2)
        
        # Stop button
        self.stop_button = tk.Button(
            controls_frame,
            text="⏹️",
            command=self._stop_playback,
            font=("Arial", 14),
            width=3
        )
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        # Position display
        self.position_label = tk.Label(
            controls_frame,
            text="00:00",
            font=("Arial", 10),
            width=8
        )
        self.position_label.pack(side=tk.LEFT, padx=5)
        
        # Progress bar frame
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Progress scale
        self.progress_var = tk.DoubleVar()
        self.progress_scale = tk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var,
            command=self._on_seek,
            showvalue=False,
            length=300
        )
        self.progress_scale.pack(fill=tk.X)
        
        # Duration display
        self.duration_label = tk.Label(
            progress_frame,
            text="/ 00:00",
            font=("Arial", 10)
        )
        self.duration_label.pack()
        
        # File info
        self.file_label = tk.Label(
            self,
            text="No file loaded",
            font=("Arial", 9),
            fg="gray"
        )
        self.file_label.pack(pady=2)
        
        # Initially disable controls
        self._update_controls_state(False)
    
    def load_file(self, file_path: str) -> bool:
        """
        Load an audio file for playback.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        
        if self.player.load_file(file_path):
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"Loaded: {filename}")
            
            # Update duration display
            duration = self.player.get_duration()
            duration_text = self._format_time(duration)
            self.duration_label.config(text=f"/ {duration_text}")
            
            # Enable controls
            self._update_controls_state(True)
            
            return True
        else:
            self.file_label.config(text="Failed to load file")
            self._update_controls_state(False)
            return False
    
    def _toggle_playback(self):
        """Toggle play/pause."""
        if not self.player.is_loaded():
            return
        
        if self.player.is_playing:
            if self.player.is_paused:
                self.player.resume()
                self.play_button.config(text="⏸️")
            else:
                self.player.pause()
                self.play_button.config(text="▶️")
        else:
            if self.player.play():
                self.play_button.config(text="⏸️")
    
    def _stop_playback(self):
        """Stop playback."""
        self.player.stop()
        self.play_button.config(text="▶️")
        self.progress_var.set(0)
        self.position_label.config(text="00:00")
    
    def _on_seek(self, value):
        """Handle seek bar movement."""
        if self.player.is_loaded():
            position = (float(value) / 100) * self.player.get_duration()
            self.player.seek(position)
    
    def _on_position_update(self, position: float, duration: float):
        """Handle position updates from player."""
        # Update position display
        position_text = self._format_time(position)
        self.position_label.config(text=position_text)
        
        # Update progress bar
        if duration > 0:
            progress = (position / duration) * 100
            self.progress_var.set(progress)
    
    def _on_playback_finished(self):
        """Handle playback finished."""
        self.play_button.config(text="▶️")
        self.progress_var.set(0)
        self.position_label.config(text="00:00")
    
    def _update_controls_state(self, enabled: bool):
        """Update the state of control buttons."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.play_button.config(state=state)
        self.stop_button.config(state=state)
        self.progress_scale.config(state=state)
    
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'player'):
            self.player.cleanup()


def create_audio_player_window(parent=None, file_path=None):
    """
    Create a standalone audio player window.
    
    Args:
        parent: Parent window (optional)
        file_path: Initial file to load (optional)
        
    Returns:
        The created window
    """
    
    # Create window
    if parent:
        window = tk.Toplevel(parent)
    else:
        window = tk.Tk()
    
    window.title("🎵 Audio Player")
    window.geometry("400x200")
    window.resizable(True, False)
    
    # Create player widget
    player_widget = AudioPlayerWidget(window)
    player_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Load initial file if provided
    if file_path:
        player_widget.load_file(file_path)
    
    # Handle window close
    def on_close():
        player_widget.cleanup()
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_close)
    
    return window


# Test function
def test_audio_player():
    """Test the audio player functionality."""
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()  # Hide root window
    
    # Ask user to select an audio file
    file_path = filedialog.askopenfilename(
        title="Select Audio File",
        filetypes=[
            ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
            ("All Files", "*.*")
        ]
    )
    
    if file_path:
        window = create_audio_player_window(file_path=file_path)
        if window:
            window.mainloop()
    else:
        print("No file selected")
    
    root.destroy()


if __name__ == "__main__":
    test_audio_player()
