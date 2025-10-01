"""
Centralized error handling to eliminate duplicated error handling patterns.
"""

import logging
import traceback
from typing import Optional, Callable, Any, Dict
from functools import wraps
import tkinter as tk
from tkinter import messagebox


class ErrorHandler:
    """Centralized error handling for the application."""
    
    _logger: Optional[logging.Logger] = None
    _error_callbacks: Dict[str, Callable] = {}
    
    @classmethod
    def setup_logging(cls, log_file: str = "chord_importer.log", 
                     level: int = logging.INFO) -> None:
        """
        Setup application logging.
        
        Args:
            log_file: Log file path
            level: Logging level
        """
        cls._logger = logging.getLogger("ChordImporter")
        cls._logger.setLevel(level)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        cls._logger.addHandler(file_handler)
        cls._logger.addHandler(console_handler)
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the application logger."""
        if cls._logger is None:
            cls.setup_logging()
        return cls._logger
    
    @classmethod
    def log_error(cls, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log an error message.
        
        Args:
            message: Error message
            exception: Optional exception object
        """
        logger = cls.get_logger()
        
        if exception:
            logger.error(f"{message}: {str(exception)}")
            logger.debug(traceback.format_exc())
        else:
            logger.error(message)
    
    @classmethod
    def log_warning(cls, message: str) -> None:
        """Log a warning message."""
        logger = cls.get_logger()
        logger.warning(message)
    
    @classmethod
    def log_info(cls, message: str) -> None:
        """Log an info message."""
        logger = cls.get_logger()
        logger.info(message)
    
    @classmethod
    def handle_exception(cls, exception: Exception, context: str = "", 
                        show_dialog: bool = True, parent: Optional[tk.Widget] = None) -> None:
        """
        Handle an exception with logging and optional user notification.
        
        Args:
            exception: Exception to handle
            context: Context where the exception occurred
            show_dialog: Whether to show error dialog to user
            parent: Parent widget for dialog
        """
        error_msg = f"Error in {context}: {str(exception)}" if context else str(exception)
        cls.log_error(error_msg, exception)
        
        if show_dialog:
            title = f"Error in {context}" if context else "Error"
            messagebox.showerror(title, error_msg, parent=parent)
        
        # Call registered error callbacks
        for callback_name, callback in cls._error_callbacks.items():
            try:
                callback(exception, context)
            except Exception as callback_error:
                cls.log_error(f"Error in callback {callback_name}", callback_error)
    
    @classmethod
    def register_error_callback(cls, name: str, callback: Callable) -> None:
        """
        Register an error callback.
        
        Args:
            name: Callback name
            callback: Callback function
        """
        cls._error_callbacks[name] = callback
    
    @classmethod
    def unregister_error_callback(cls, name: str) -> None:
        """Unregister an error callback."""
        cls._error_callbacks.pop(name, None)
    
    @staticmethod
    def safe_execute(func: Callable, *args, context: str = "", 
                    default_return: Any = None, show_dialog: bool = True,
                    parent: Optional[tk.Widget] = None, **kwargs) -> Any:
        """
        Safely execute a function with error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            context: Context description
            default_return: Default return value on error
            show_dialog: Whether to show error dialog
            parent: Parent widget for dialog
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_exception(e, context, show_dialog, parent)
            return default_return
    
    @staticmethod
    def error_handler(context: str = "", show_dialog: bool = True, 
                     default_return: Any = None):
        """
        Decorator for automatic error handling.
        
        Args:
            context: Context description
            show_dialog: Whether to show error dialog
            default_return: Default return value on error
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    func_context = context or f"{func.__module__}.{func.__name__}"
                    ErrorHandler.handle_exception(e, func_context, show_dialog)
                    return default_return
            return wrapper
        return decorator
    
    @staticmethod
    def validate_required_params(**params) -> None:
        """
        Validate that required parameters are not None.
        
        Args:
            **params: Parameters to validate
            
        Raises:
            ValueError: If any parameter is None
        """
        for name, value in params.items():
            if value is None:
                raise ValueError(f"Required parameter '{name}' cannot be None")
    
    @staticmethod
    def validate_type(value: Any, expected_type: type, param_name: str) -> None:
        """
        Validate parameter type.
        
        Args:
            value: Value to validate
            expected_type: Expected type
            param_name: Parameter name
            
        Raises:
            TypeError: If type doesn't match
        """
        if not isinstance(value, expected_type):
            raise TypeError(
                f"Parameter '{param_name}' must be of type {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
    
    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, 
                      param_name: str) -> None:
        """
        Validate that a value is within a range.
        
        Args:
            value: Value to validate
            min_val: Minimum value
            max_val: Maximum value
            param_name: Parameter name
            
        Raises:
            ValueError: If value is out of range
        """
        if not (min_val <= value <= max_val):
            raise ValueError(
                f"Parameter '{param_name}' must be between {min_val} and {max_val}, "
                f"got {value}"
            )


# Convenience decorators
def handle_errors(context: str = "", show_dialog: bool = True, default_return: Any = None):
    """Convenience decorator for error handling."""
    return ErrorHandler.error_handler(context, show_dialog, default_return)


def log_errors(func):
    """Decorator to log errors without showing dialogs."""
    return ErrorHandler.error_handler(show_dialog=False)(func)
