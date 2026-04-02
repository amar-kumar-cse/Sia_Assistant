"""
Knowledge Base (RAG) Module for Sia
Personal knowledge retrieval from local files, notes, and code projects.
Simple TF-IDF based search - no external vector DB required.
"""

import os
import json
import time
import re
import math
from collections import Counter, defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(SCRIPT_DIR, "knowledge_index.json")

# Supported file extensions for indexing
SUPPORTED_EXTENSIONS = {
    ".py", ".java", ".cpp", ".c", ".js", ".ts", ".html", ".css",
    ".json", ".xml", ".yaml", ".yml",
    ".md", ".txt", ".rst", ".log",
    ".sql", ".sh", ".bat", ".ps1",
    ".csv",
}

# Maximum file size to index (500 KB)
MAX_FILE_SIZE = 500 * 1024

# In-memory index cache
_index_cache = None
_idf_cache = None


class KnowledgeBase:
    """Simple TF-IDF based knowledge retrieval system."""
    
    def __init__(self):
        self.documents = {}  # {filepath: {"content": str, "tokens": list, "modified": float}}
        self.idf = {}        # Inverse document frequency
        self.indexed_paths = []
        self._load_index()
    
    def _load_index(self):
        """Load existing index from disk."""
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.indexed_paths = data.get("indexed_paths", [])
                    self._rebuild_idf()
                    print(f"📚 Knowledge base loaded: {len(self.documents)} documents")
            except Exception as e:
                print(f"⚠️ Failed to load knowledge index: {e}")
                self.documents = {}
    
    def _save_index(self):
        """Save index to disk (lightweight - stores metadata, not full content)."""
        try:
            # Save lightweight version (just metadata + tokens, not full content)
            save_data = {
                "indexed_paths": self.indexed_paths,
                "documents": {},
                "last_updated": datetime.now().isoformat()
            }
            
            for filepath, doc in self.documents.items():
                save_data["documents"][filepath] = {
                    "tokens": doc.get("tokens", []),
                    "modified": doc.get("modified", 0),
                    "summary": doc.get("content", "")[:200]  # Store first 200 chars as summary
                }
            
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Knowledge index saved: {len(self.documents)} documents")
            
        except Exception as e:
            print(f"❌ Failed to save knowledge index: {e}")
    
    def _tokenize(self, text):
        """Simple tokenization: split on non-alphanumeric, lowercase, remove short tokens."""
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
        return tokens
    
    def _rebuild_idf(self):
        """Rebuild IDF values from all documents."""
        if not self.documents:
            self.idf = {}
            return
        
        doc_count = len(self.documents)
        doc_freq = defaultdict(int)
        
        for doc in self.documents.values():
            unique_tokens = set(doc.get("tokens", []))
            for token in unique_tokens:
                doc_freq[token] += 1
        
        self.idf = {}
        for token, freq in doc_freq.items():
            self.idf[token] = math.log(doc_count / (1 + freq))
    
    def index_file(self, filepath):
        """Index a single file."""
        try:
            # Check if file exists and is valid
            if not os.path.exists(filepath):
                return False
            
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return False
            
            # Check file size
            if os.path.getsize(filepath) > MAX_FILE_SIZE:
                return False
            
            # Check if already indexed and not modified
            mod_time = os.path.getmtime(filepath)
            if filepath in self.documents:
                if self.documents[filepath].get("modified", 0) >= mod_time:
                    return True  # Already up to date
            
            # Read file content
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                return False
            
            # Tokenize and store
            tokens = self._tokenize(content)
            
            self.documents[filepath] = {
                "content": content,
                "tokens": tokens,
                "modified": mod_time,
                "filename": os.path.basename(filepath)
            }
            
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to index {filepath}: {e}")
            return False
    
    def index_directory(self, dir_path, max_files=500):
        """
        Recursively index all supported files in a directory.
        
        Args:
            dir_path: Directory to scan
            max_files: Maximum number of files to index
        
        Returns:
            Status message
        """
        if not os.path.exists(dir_path):
            return f"❌ Directory nahi mila: {dir_path}"
        
        # Skip common non-useful directories
        skip_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.venv_old', 'env', '.env', 'dist', 'build', '.idea',
            '.vs', '.vscode', 'target', 'bin', 'obj'
        }
        
        indexed = 0
        skipped = 0
        
        for root, dirs, files in os.walk(dir_path):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for filename in files:
                if indexed >= max_files:
                    break
                
                filepath = os.path.join(root, filename)
                if self.index_file(filepath):
                    indexed += 1
                else:
                    skipped += 1
        
        # Save the indexed path
        abs_path = os.path.abspath(dir_path)
        if abs_path not in self.indexed_paths:
            self.indexed_paths.append(abs_path)
        
        # Rebuild IDF and save
        self._rebuild_idf()
        self._save_index()
        
        return f"✅ {indexed} files indexed from {os.path.basename(dir_path)} ({skipped} skipped)"
    
    def search(self, query, top_k=3):
        """
        Search the knowledge base for relevant documents.
        Uses TF-IDF cosine similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
        
        Returns:
            List of (filepath, relevance_score, snippet) tuples
        """
        if not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Calculate TF-IDF scores for each document
        scores = {}
        
        for filepath, doc in self.documents.items():
            doc_tokens = doc.get("tokens", [])
            if not doc_tokens:
                continue
            
            # Term frequency in document
            tf = Counter(doc_tokens)
            doc_len = len(doc_tokens)
            
            # Score = sum of TF-IDF for matching query tokens
            score = 0.0
            for token in query_tokens:
                if token in tf:
                    token_tf = tf[token] / doc_len
                    token_idf = self.idf.get(token, 0)
                    score += token_tf * token_idf
            
            # Bonus for filename match
            filename = doc.get("filename", "").lower()
            for token in query_tokens:
                if token in filename:
                    score += 0.5  # Boost filename matches
            
            if score > 0:
                scores[filepath] = score
        
        # Sort by score and return top_k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for filepath, score in sorted_results:
            content = self.documents[filepath].get("content", "")
            snippet = self._extract_snippet(content, query_tokens)
            results.append((filepath, score, snippet))
        
        return results
    
    def _extract_snippet(self, content, query_tokens, max_length=300):
        """Extract a relevant snippet from content around matching tokens."""
        lines = content.split('\n')
        
        # Find the most relevant line
        best_line_idx = 0
        best_score = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            score = sum(1 for token in query_tokens if token in line_lower)
            if score > best_score:
                best_score = score
                best_line_idx = i
        
        # Extract surrounding context
        start = max(0, best_line_idx - 2)
        end = min(len(lines), best_line_idx + 5)
        snippet = '\n'.join(lines[start:end])
        
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + "..."
        
        return snippet
    
    def get_relevant_context(self, query, top_k=3):
        """
        Get relevant context from knowledge base for brain.py integration.
        Returns formatted string ready for prompt injection.
        """
        results = self.search(query, top_k)
        
        if not results:
            return ""
        
        context = "\n\n=== PERSONAL KNOWLEDGE BASE RESULTS ===\n"
        context += "(Found in your local files)\n\n"
        
        for filepath, score, snippet in results:
            filename = os.path.basename(filepath)
            rel_path = filepath  # Could make relative if needed
            context += f"📄 File: {filename}\n"
            context += f"   Path: {rel_path}\n"
            context += f"   Relevant snippet:\n```\n{snippet}\n```\n\n"
        
        return context
    
    def get_stats(self):
        """Get knowledge base statistics."""
        return {
            "total_documents": len(self.documents),
            "indexed_paths": self.indexed_paths,
            "total_tokens": sum(len(doc.get("tokens", [])) for doc in self.documents.values()),
            "unique_terms": len(self.idf)
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLOBAL INSTANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_kb_instance = None


def get_knowledge_base():
    """Get the global knowledge base instance."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance


def index_project(path=None):
    """Quick function to index a project directory."""
    kb = get_knowledge_base()
    if path is None:
        path = SCRIPT_DIR  # Index Sia's own project by default
    return kb.index_directory(path)


def search_knowledge(query, top_k=3):
    """Quick function to search the knowledge base."""
    kb = get_knowledge_base()
    return kb.get_relevant_context(query, top_k)


def get_kb_stats():
    """Quick function to get KB statistics."""
    kb = get_knowledge_base()
    stats = kb.get_stats()
    return f"""📚 Knowledge Base Stats:
• Documents: {stats['total_documents']}
• Total tokens: {stats['total_tokens']}
• Unique terms: {stats['unique_terms']}
• Indexed paths: {', '.join(stats['indexed_paths']) if stats['indexed_paths'] else 'None'}"""
