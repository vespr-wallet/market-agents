import os
import logging
import time
from logging.handlers import RotatingFileHandler
from collections import deque
from threading import Lock

# In-memory log buffer to store recent logs for streaming
class LogBuffer:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LogBuffer, cls).__new__(cls)
                cls._instance.logs = deque(maxlen=1000)  # Store last 1000 log messages
                cls._instance.listeners = set()
            return cls._instance
    
    def add_log(self, log_entry):
        """Add a log entry to the buffer and notify all listeners"""
        with self._lock:
            self.logs.append(log_entry)
            # Make a copy to avoid issues with removing during iteration
            listeners = list(self.listeners)
        
        # Notify listeners outside the lock to avoid deadlocks
        for listener_queue in listeners:
            try:
                listener_queue.put(log_entry)
            except:
                # Remove dead listeners
                with self._lock:
                    self.listeners.discard(listener_queue)
    
    def get_recent_logs(self, n=100):
        """Get the n most recent log entries"""
        with self._lock:
            # Convert to list and return the most recent n logs
            return list(self.logs)[-n:]
    
    def add_listener(self, queue):
        """Add a new listener queue"""
        with self._lock:
            self.listeners.add(queue)
            
    def remove_listener(self, queue):
        """Remove a listener queue"""
        with self._lock:
            self.listeners.discard(queue)

# Custom log handler that adds logs to the buffer
class BufferedLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_buffer = LogBuffer()
        
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': record.levelname,
                'message': self.format(record),
                'logger': record.name
            }
            self.log_buffer.add_log(log_entry)
        except Exception:
            self.handleError(record)

def setup_logging(log_level=logging.INFO):
    """
    Configure application-wide logging
    
    Args:
        log_level: The minimum log level to capture (default: INFO)
    
    Returns:
        logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, "app.log")
    
    # Create formatter for consistent log formatting
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Set up rotating file handler (10 MB per file, keep 5 backup files)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    
    # Set up the buffered log handler for streaming
    buffer_handler = BufferedLogHandler()
    buffer_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add the handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(buffer_handler)
    
    return root_logger

def get_logger(name):
    """
    Get a logger for a specific module
    
    Args:
        name: Usually __name__ from the calling module
        
    Returns:
        A logger instance with the specified name
    """
    return logging.getLogger(name)

# Function to get the log buffer singleton
def get_log_buffer():
    """Get the global LogBuffer instance"""
    return LogBuffer() 