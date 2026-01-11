"""
Global terminal output streaming via SSE
Captures all stdout/stderr from backend
"""

import sys
import asyncio
from typing import Set, Optional
from datetime import datetime
import io
import threading


class TerminalBroadcaster:
    """Broadcasts all terminal output to subscribed clients"""
    
    def __init__(self):
        self.subscribers: Set[asyncio.Queue] = set()
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations"""
        self._loop = loop
        
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to terminal output"""
        queue = asyncio.Queue(maxsize=1000)
        with self._lock:
            self.subscribers.add(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from terminal output"""
        with self._lock:
            self.subscribers.discard(queue)
    
    def broadcast_sync(self, message: str, stream_type: str = "stdout"):
        """Synchronously broadcast message (called from interceptor)"""
        if not self.subscribers or not self._loop:
            return
            
        timestamp = datetime.utcnow().isoformat()
        
        # Remove dead queues
        dead_queues = set()
        with self._lock:
            for queue in list(self.subscribers):
                try:
                    # Use put_nowait to avoid blocking
                    self._loop.call_soon_threadsafe(
                        queue.put_nowait,
                        {
                            "timestamp": timestamp,
                            "stream": stream_type,
                            "content": message
                        }
                    )
                except asyncio.QueueFull:
                    dead_queues.add(queue)
            
            self.subscribers -= dead_queues


# Global broadcaster
terminal_broadcaster = TerminalBroadcaster()


class StreamInterceptor(io.TextIOBase):
    """Intercepts writes to stdout/stderr"""
    
    def __init__(self, original_stream, stream_type: str, broadcaster: TerminalBroadcaster):
        self.original = original_stream
        self.stream_type = stream_type
        self.broadcaster = broadcaster
        
    def write(self, text: str) -> int:
        """Write to both original stream and broadcast"""
        # Write to original
        result = self.original.write(text)
        self.original.flush()
        
        # Broadcast to subscribers
        if text and text.strip():
            self.broadcaster.broadcast_sync(text, self.stream_type)
        
        return result
    
    def flush(self):
        """Flush the original stream"""
        self.original.flush()
    
    def isatty(self):
        """Check if original is a tty"""
        return self.original.isatty()


def install_terminal_interceptor():
    """Install stdout/stderr interceptors"""
    sys.stdout = StreamInterceptor(terminal_broadcaster._original_stdout, "stdout", terminal_broadcaster)
    sys.stderr = StreamInterceptor(terminal_broadcaster._original_stderr, "stderr", terminal_broadcaster)
    print("[Terminal Streamer] Installed - all output will be broadcast to subscribers")


def uninstall_terminal_interceptor():
    """Restore original stdout/stderr"""
    sys.stdout = terminal_broadcaster._original_stdout
    sys.stderr = terminal_broadcaster._original_stderr
    print("[Terminal Streamer] Uninstalled")

