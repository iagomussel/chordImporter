"""
Audio helper utilities to eliminate duplicated audio processing code.
"""

import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from .imports import ImportManager


class AudioHelpers:
    """Collection of audio helper methods to reduce code duplication."""
    
    # Cache for audio modules
    _sounddevice = None
    _pyaudio = None
    _librosa = None
    _scipy = None
    
    @classmethod
    def get_sounddevice(cls):
        """Get sounddevice module with caching."""
        if cls._sounddevice is None:
            cls._sounddevice = ImportManager.safe_import('sounddevice')
        return cls._sounddevice
    
    @classmethod
    def get_pyaudio(cls):
        """Get pyaudio module with caching."""
        if cls._pyaudio is None:
            cls._pyaudio = ImportManager.safe_import('pyaudio')
        return cls._pyaudio
    
    @classmethod
    def get_librosa(cls):
        """Get librosa module with caching."""
        if cls._librosa is None:
            cls._librosa = ImportManager.safe_import('librosa')
        return cls._librosa
    
    @classmethod
    def get_scipy(cls):
        """Get scipy module with caching."""
        if cls._scipy is None:
            cls._scipy = ImportManager.safe_import('scipy')
        return cls._scipy
    
    @staticmethod
    def get_audio_devices() -> List[Dict[str, Any]]:
        """
        Get list of available audio devices.
        
        Returns:
            List of audio device information
        """
        sd = AudioHelpers.get_sounddevice()
        if sd is None:
            return []
        
        try:
            devices = sd.query_devices()
            return [
                {
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': device['default_samplerate']
                }
                for i, device in enumerate(devices)
                if device['max_input_channels'] > 0
            ]
        except Exception:
            return []
    
    @staticmethod
    def get_default_input_device() -> Optional[int]:
        """
        Get default input device index.
        
        Returns:
            Default input device index or None
        """
        sd = AudioHelpers.get_sounddevice()
        if sd is None:
            return None
        
        try:
            return sd.default.device[0]  # Input device
        except Exception:
            return None
    
    @staticmethod
    def validate_audio_parameters(sample_rate: int, channels: int, 
                                 chunk_size: int) -> Tuple[bool, str]:
        """
        Validate audio parameters.
        
        Args:
            sample_rate: Sample rate in Hz
            channels: Number of channels
            chunk_size: Chunk size in samples
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if sample_rate <= 0:
            return False, "Sample rate must be positive"
        
        if channels <= 0:
            return False, "Channels must be positive"
        
        if chunk_size <= 0:
            return False, "Chunk size must be positive"
        
        # Check if sample rate is reasonable
        if sample_rate < 8000 or sample_rate > 192000:
            return False, "Sample rate should be between 8kHz and 192kHz"
        
        # Check if chunk size is reasonable
        if chunk_size < 64 or chunk_size > 8192:
            return False, "Chunk size should be between 64 and 8192 samples"
        
        return True, ""
    
    @staticmethod
    def calculate_frequency(audio_data: np.ndarray, sample_rate: int, 
                          method: str = "hps") -> float:
        """
        Calculate fundamental frequency from audio data.
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate in Hz
            method: Method to use ("hps", "autocorr", "fft")
            
        Returns:
            Fundamental frequency in Hz
        """
        if len(audio_data) == 0:
            return 0.0
        
        if method == "hps":
            return AudioHelpers._hps_frequency(audio_data, sample_rate)
        elif method == "autocorr":
            return AudioHelpers._autocorr_frequency(audio_data, sample_rate)
        elif method == "fft":
            return AudioHelpers._fft_frequency(audio_data, sample_rate)
        else:
            return AudioHelpers._hps_frequency(audio_data, sample_rate)
    
    @staticmethod
    def _hps_frequency(audio_data: np.ndarray, sample_rate: int) -> float:
        """Calculate frequency using Harmonic Product Spectrum."""
        # Apply window
        windowed = audio_data * np.hanning(len(audio_data))
        
        # FFT
        fft = np.abs(np.fft.rfft(windowed))
        
        # HPS
        hps = fft.copy()
        for h in range(2, 6):  # Harmonics 2-5
            decimated = fft[::h]
            hps[:len(decimated)] *= decimated
        
        # Find peak
        peak_idx = np.argmax(hps[1:]) + 1  # Skip DC
        frequency = peak_idx * sample_rate / len(audio_data)
        
        return frequency
    
    @staticmethod
    def _autocorr_frequency(audio_data: np.ndarray, sample_rate: int) -> float:
        """Calculate frequency using autocorrelation."""
        # Autocorrelation
        autocorr = np.correlate(audio_data, audio_data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find first peak after zero lag
        if len(autocorr) < 2:
            return 0.0
        
        # Find peaks
        peaks = []
        for i in range(1, len(autocorr) - 1):
            if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                peaks.append((i, autocorr[i]))
        
        if not peaks:
            return 0.0
        
        # Get highest peak
        peak_idx = max(peaks, key=lambda x: x[1])[0]
        frequency = sample_rate / peak_idx
        
        return frequency
    
    @staticmethod
    def _fft_frequency(audio_data: np.ndarray, sample_rate: int) -> float:
        """Calculate frequency using simple FFT peak detection."""
        fft = np.abs(np.fft.rfft(audio_data))
        peak_idx = np.argmax(fft[1:]) + 1  # Skip DC
        frequency = peak_idx * sample_rate / len(audio_data)
        return frequency
    
    @staticmethod
    def note_from_frequency(frequency: float) -> Tuple[str, int, float]:
        """
        Convert frequency to musical note.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Tuple of (note_name, octave, cents_offset)
        """
        if frequency <= 0:
            return "N/A", 0, 0.0
        
        # A4 = 440 Hz
        A4 = 440.0
        
        # Calculate semitones from A4
        semitones = 12 * np.log2(frequency / A4)
        
        # Note names
        notes = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
        
        # Calculate note index and octave
        note_index = int(round(semitones)) % 12
        octave = 4 + (int(round(semitones)) + 9) // 12
        
        # Calculate cents offset
        exact_semitones = semitones
        rounded_semitones = round(semitones)
        cents = (exact_semitones - rounded_semitones) * 100
        
        return notes[note_index], octave, cents
    
    @staticmethod
    def apply_window(audio_data: np.ndarray, window_type: str = "hanning") -> np.ndarray:
        """
        Apply window function to audio data.
        
        Args:
            audio_data: Input audio data
            window_type: Type of window ("hanning", "hamming", "blackman")
            
        Returns:
            Windowed audio data
        """
        if window_type == "hanning":
            window = np.hanning(len(audio_data))
        elif window_type == "hamming":
            window = np.hamming(len(audio_data))
        elif window_type == "blackman":
            window = np.blackman(len(audio_data))
        else:
            window = np.hanning(len(audio_data))
        
        return audio_data * window
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray, target_level: float = 0.5) -> np.ndarray:
        """
        Normalize audio data to target level.
        
        Args:
            audio_data: Input audio data
            target_level: Target RMS level (0.0 to 1.0)
            
        Returns:
            Normalized audio data
        """
        if len(audio_data) == 0:
            return audio_data
        
        # Calculate RMS
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        if rms == 0:
            return audio_data
        
        # Normalize
        scale_factor = target_level / rms
        return audio_data * scale_factor
    
    @staticmethod
    def detect_silence(audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """
        Detect if audio data contains mostly silence.
        
        Args:
            audio_data: Input audio data
            threshold: Silence threshold (RMS level)
            
        Returns:
            True if audio is mostly silent
        """
        if len(audio_data) == 0:
            return True
        
        rms = np.sqrt(np.mean(audio_data ** 2))
        return rms < threshold
