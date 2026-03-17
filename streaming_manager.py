"""
Streaming Manager - Zero Latency Coordination
Handles the pipeline: Gemini Stream → Text Chunks → Voice Synthesis → Audio Playback
Built for Sia 2.0 - High-Speed Virtual Assistant
"""

import threading
import queue
import time
import re
from typing import Generator, Callable, Optional

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
        self.min_chunk_length = 20  # Minimum characters before speaking
        self.sentence_endings = r'[.!?।]'  # Include Hindi sentence ending
        
    def process_stream(self, text_generator: Generator, voice_callback: Callable):
        """
        Main streaming pipeline coordinator.
        
        Args:
            text_generator: Generator yielding text chunks from Gemini
            voice_callback: Function to call with complete sentences for TTS
        """
        self.is_streaming = True
        self.should_stop = False
        
        # Start parallel threads
        text_thread = threading.Thread(
            target=self._text_collector_thread,
            args=(text_generator,),
            daemon=True
        )
        
        voice_thread = threading.Thread(
            target=self._voice_synthesis_thread,
            args=(voice_callback,),
            daemon=True
        )
        
        text_thread.start()
        voice_thread.start()
        
        # Wait for completion
        text_thread.join()
        voice_thread.join()
        
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
                sentences = self._extract_sentences(buffer)
                
                for sentence in sentences:
                    if len(sentence.strip()) >= self.min_chunk_length:
                        # Send to voice synthesis queue
                        self.text_queue.put(sentence)
                        buffer = buffer.replace(sentence, "", 1)
                
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
    
    def _extract_sentences(self, text: str) -> list:
        """
        Extract complete sentences from buffered text.
        Splits on common sentence endings while preserving them.
        """
        # Find all sentence boundaries
        matches = list(re.finditer(self.sentence_endings, text))
        
        sentences = []
        for match in matches:
            # Get text up to and including the sentence ending
            end_pos = match.end()
            sentence = text[:end_pos].strip()
            
            if sentence:
                sentences.append(sentence)
        
        return sentences
    
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
def chunk_text_smart(text: str, min_length: int = 20) -> list:
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
