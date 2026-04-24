"""
Streaming Manager - Zero Latency Coordination
Handles the pipeline: Gemini Stream → Text Chunks → Voice Synthesis → Audio Playback
Built for Sia 2.0 - High-Speed Virtual Assistant
"""

import threading
import queue
import time
import re
import logging
from typing import Generator, Callable, Optional

logger = logging.getLogger(__name__)

class StreamingManager:
    """
    Coordinates streaming from Gemini to ElevenLabs for instant responses.
    Implements parallel processing for thinking, speaking, and animation sync.
    """
    
    def __init__(self):
        # Queues for pipeline coordination
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        # State management
        self.is_streaming = False
        self.is_speaking = False
        self.should_stop = False
        
        # Callbacks
        self.on_chunk_received = None
        self.on_speaking_start = None
        self.on_speaking_end = None
        
        # Configuration
        self.min_chunk_length = 70  # TRD: start speaking at sentence boundary or >=70 chars
        self.sentence_endings = r'[.!?।]'  # Include Hindi sentence ending
        
        # ✅ FIX #6: Track threads for proper cleanup
        self._text_thread: Optional[threading.Thread] = None
        self._voice_thread: Optional[threading.Thread] = None
        
    def process_stream(self, text_generator: Generator, voice_callback: Callable, timeout_seconds: int = 120) -> bool:
        """
        ✅ FIX #6: Main streaming pipeline coordinator with proper timeout and cleanup.
        
        Args:
            text_generator: Generator yielding text chunks from Gemini
            voice_callback: Function to call with complete sentences for TTS
            timeout_seconds: Max time to allow for streaming
            
        Returns:
            True if completed successfully, False if timeout/error
        """
        self.is_streaming = True
        self.should_stop = False
        success = False
        
        try:
            # ✅ FIX #6: Create non-daemon threads for proper cleanup
            self._text_thread = threading.Thread(
                target=self._text_collector_thread,
                args=(text_generator,),
                name="StreamTextCollector",
                daemon=True
            )
            
            self._voice_thread = threading.Thread(
                target=self._voice_synthesis_thread,
                args=(voice_callback,),
                name="StreamVoiceSynthesis",
                daemon=True
            )
            
            self._text_thread.start()
            self._voice_thread.start()
            
            # ✅ FIX #6: Join with timeout
            logger.info(f"Starting stream processing (timeout={timeout_seconds}s)")
            
            self._text_thread.join(timeout=timeout_seconds)
            self._voice_thread.join(timeout=timeout_seconds)
            
            # ✅ FIX #6: Check if threads completed
            if self._text_thread.is_alive() or self._voice_thread.is_alive():
                logger.error("Stream threads did not complete within timeout")
                self.should_stop = True
                
                # ✅ FIX #6: Force cleanup
                self._text_thread.join(timeout=5)
                self._voice_thread.join(timeout=5)
                
                if self._text_thread.is_alive() or self._voice_thread.is_alive():
                    logger.error("Threads still alive after cleanup - possible deadlock")
                    return False
            else:
                success = True
                logger.info("Stream processing completed successfully")
            
        except Exception as e:
            logger.error(f"Stream processing error: {e}", exc_info=True)
            self.should_stop = True
        
        finally:
            self.is_streaming = False
            # ✅ FIX #6: Clear references
            self._text_thread = None
            self._voice_thread = None
            
            return success
    
    def stop_streaming(self) -> None:
        """✅ FIX #6: Force stop streaming with cleanup."""
        logger.info("Stopping stream processing")
        self.should_stop = True
        
        # ✅ FIX #6: Wait for threads to finish
        if self._text_thread and self._text_thread.is_alive():
            self._text_thread.join(timeout=5)
        
        if self._voice_thread and self._voice_thread.is_alive():
            self._voice_thread.join(timeout=5)
        
        self.is_streaming = False
        
    def _text_collector_thread(self, text_generator: Generator):
        """
        Thread 1: Collect text chunks from Gemini streaming.
        Buffer and split into complete sentences for natural speech.
        """
        buffer = ""
        
        try:
            for chunk in text_generator:
                if self.should_stop:
                    break
                
                # Accumulate text
                buffer += chunk
                
                # Callback for live text display
                if self.on_chunk_received:
                    self.on_chunk_received(chunk)
                
                # Check if we have complete sentences
                complete, remaining = self._extract_sentences(buffer)
                for sentence in complete:
                    if len(sentence.strip()) >= self.min_chunk_length:
                        self.text_queue.put(sentence)
                buffer = remaining

                # Fallback chunk threshold for long streams without punctuation.
                if len(buffer.strip()) >= self.min_chunk_length:
                    self.text_queue.put(buffer.strip())
                    buffer = ""
                
        except Exception as e:
            print(f"❌ Streaming error: {e}")
        
        finally:
            # Send remaining buffer if any
            if buffer.strip():
                self.text_queue.put(buffer)
            
            # Signal completion
            self.text_queue.put(None)
    
    def _voice_synthesis_thread(self, voice_callback: Callable):
        """
        Thread 2: Convert text chunks to speech.
        Processes queue and triggers voice synthesis.
        """
        self.is_speaking = True
        
        if self.on_speaking_start:
            self.on_speaking_start()
        
        try:
            while True:
                # Get next text chunk
                text_chunk = self.text_queue.get()
                
                # Check for completion signal
                if text_chunk is None:
                    break
                
                if self.should_stop:
                    break
                
                # Synthesize and play
                voice_callback(text_chunk)
                
        except Exception as e:
            print(f"❌ Voice synthesis error: {e}")
        
        finally:
            self.is_speaking = False
            
            if self.on_speaking_end:
                self.on_speaking_end()
    
    def _extract_sentences(self, text: str):
        """
        Extract complete sentences from buffered text.
        Splits on common sentence endings while preserving them.
        """
        matches = list(re.finditer(self.sentence_endings, text))

        if not matches:
            return [], text

        complete = []
        start = 0
        last_end = 0
        for match in matches:
            end = match.end()
            sentence = text[start:end].strip()
            if sentence:
                complete.append(sentence)
            start = end
            last_end = end

        remaining = text[last_end:].strip()
        return complete, remaining
    
    def stop(self):
        """Emergency stop for streaming."""
        self.should_stop = True
        self.is_streaming = False
        self.is_speaking = False
    
    def get_state(self) -> dict:
        """Get current streaming state."""
        return {
            "is_streaming": self.is_streaming,
            "is_speaking": self.is_speaking,
            "queue_size": self.text_queue.qsize()
        }


# Global streaming manager instance
_streaming_manager = StreamingManager()

def get_streaming_manager() -> StreamingManager:
    """Get the global streaming manager instance."""
    return _streaming_manager


# Helper function for quick sentence chunking
def chunk_text_smart(text: str, min_length: int = 70) -> list:
    """
    Smart text chunking for natural speech flow.
    
    Args:
        text: Full text to chunk
        min_length: Minimum chunk length
    
    Returns:
        List of text chunks
    """
    # Split on sentence boundaries
    sentences = re.split(r'([.!?।]\s+)', text)
    
    chunks = []
    current_chunk = ""
    
    for i, part in enumerate(sentences):
        current_chunk += part
        
        # Check if we have a complete sentence
        if re.match(r'[.!?।]\s*$', part) or i == len(sentences) - 1:
            if len(current_chunk.strip()) >= min_length:
                chunks.append(current_chunk.strip())
                current_chunk = ""
    
    # Add remaining text
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks
