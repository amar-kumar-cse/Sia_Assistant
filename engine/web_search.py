"""
Web Search Module for Sia - Real-time Internet Learning
Gives Sia access to live web search results.
Uses DuckDuckGo (no API key required!) with Google fallback.
"""

import os
import re
import threading
from datetime import datetime
from typing import Optional


def search_web(query, num_results=3, timeout_seconds: int = 5) -> str:
    """
    Search the web using DuckDuckGo (no API key needed).
    
    Args:
        query: Search query string
        num_results: Number of results to return
        timeout_seconds: Maximum time to wait for search (default 5)
    
    Returns:
        Formatted search results string or error message
    """
    try:
        from duckduckgo_search import DDGS
        
        # ✅ Set timeout using threading for Windows compatibility
        results = None
        error_msg = None
        
        def _search_with_ddgs():
            nonlocal results, error_msg
            try:
                with DDGS(timeout=timeout_seconds) as ddgs:
                    results = list(ddgs.text(query, max_results=num_results))
            except Exception as e:
                error_msg = str(e)
        
        # ✅ Run search in thread with timeout
        search_thread = threading.Thread(target=_search_with_ddgs, daemon=True)
        search_thread.start()
        search_thread.join(timeout=timeout_seconds)
        
        if search_thread.is_alive():
            return f"⏱️ Web search ke liye timeout ho gaya ({timeout_seconds}s). Internet dhire hai."
        
        if error_msg:
            raise Exception(error_msg)
        
        if results is None:
            results = []
        
        if not results:
            return f"❌ '{query}' ke liye kuch nahi mila internet pe."
        
        formatted = f"🌐 Web Search Results for: '{query}'\n"
        formatted += "=" * 50 + "\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            url = result.get('href', '')
            
            formatted += f"📌 {i}. {title}\n"
            formatted += f"   {body[:200]}\n"
            formatted += f"   🔗 {url}\n\n"
        
        return formatted
        
    except ImportError:
        return "⚠️ duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"❌ Web search failed: {str(e)[:100]}"


def get_latest_news(topic="technology India", num_results=5):
    """
    Get latest news headlines on a topic.
    
    Args:
        topic: News topic to search for
        num_results: Number of news articles
    
    Returns:
        Formatted news results
    """
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.news(topic, max_results=num_results))
        
        if not results:
            return f"❌ '{topic}' ke baare mein koi news nahi mili."
        
        formatted = f"📰 Latest News: '{topic}'\n"
        formatted += f"📅 {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n"
        formatted += "=" * 50 + "\n\n"
        
        for i, article in enumerate(results, 1):
            title = article.get('title', 'No title')
            body = article.get('body', '')[:150]
            source = article.get('source', 'Unknown')
            date = article.get('date', '')
            url = article.get('url', '')
            
            formatted += f"📌 {i}. {title}\n"
            if body:
                formatted += f"   {body}...\n"
            formatted += f"   Source: {source}"
            if date:
                formatted += f" | {date}"
            formatted += f"\n   🔗 {url}\n\n"
        
        return formatted
        
    except ImportError:
        return "⚠️ duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"❌ News fetch failed: {str(e)[:100]}"


def search_coding_docs(query, language="python"):
    """
    Search for coding-related documentation and solutions.
    Focuses on StackOverflow, documentation sites, etc.
    
    Args:
        query: Coding question or topic
        language: Programming language context
    
    Returns:
        Formatted coding results
    """
    search_query = f"{language} {query} site:stackoverflow.com OR site:docs.python.org OR site:geeksforgeeks.org OR site:w3schools.com"
    
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=3))
        
        if not results:
            # Fallback to general search
            with DDGS() as ddgs:
                results = list(ddgs.text(f"{language} {query}", max_results=3))
        
        if not results:
            return f"❌ '{query}' ka coding solution nahi mila."
        
        formatted = f"💻 Coding Help: '{query}' ({language})\n"
        formatted += "=" * 50 + "\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', '')[:250]
            url = result.get('href', '')
            
            formatted += f"📌 {i}. {title}\n"
            formatted += f"   {body}\n"
            formatted += f"   🔗 {url}\n\n"
        
        return formatted
        
    except ImportError:
        return "⚠️ duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"❌ Coding search failed: {str(e)[:100]}"


def get_weather(city="Roorkee"):
    """
    Get current weather info for a city.
    
    Args:
        city: City name
    
    Returns:
        Weather information string
    """
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(f"weather {city} today temperature", max_results=2))
        
        if results:
            formatted = f"🌤️ Weather in {city}:\n"
            for r in results:
                body = r.get('body', '')
                if body:
                    formatted += f"  {body[:200]}\n"
            return formatted
        
        return f"❌ Weather info nahi mili for {city}"
        
    except ImportError:
        return "⚠️ duckduckgo-search not installed"
    except Exception as e:
        return f"❌ Weather fetch failed: {e}"


def quick_answer(question):
    """
    Get a quick answer to a factual question.
    
    Args:
        question: The question to answer
    
    Returns:
        Quick answer or search results
    """
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            # Try instant answer first
            results = list(ddgs.text(question, max_results=2))
        
        if results:
            # Return the most relevant snippet
            best = results[0]
            title = best.get('title', '')
            body = best.get('body', '')
            return f"🔍 {title}\n{body[:300]}"
        
        return f"❌ '{question}' ka answer nahi mila"
        
    except ImportError:
        return "⚠️ duckduckgo-search not installed"
    except Exception as e:
        return f"❌ Answer fetch failed: {e}"


def search_for_brain(query, context_type="general"):
    """
    Main function used by brain.py to get web context.
    Returns formatted string suitable for injection into AI prompts.
    
    Args:
        query: Search query
        context_type: "general", "news", "coding", "weather"
    
    Returns:
        Formatted context string for the brain prompt
    """
    try:
        if context_type == "news":
            results = get_latest_news(query, num_results=3)
        elif context_type == "coding":
            results = search_coding_docs(query)
        elif context_type == "weather":
            results = get_weather(query)
        else:
            results = search_web(query, num_results=3)
        
        if results and not results.startswith("❌") and not results.startswith("⚠️"):
            context = "\n\n=== LIVE INTERNET SEARCH RESULTS ===\n"
            context += f"(Searched at: {datetime.now().strftime('%I:%M %p, %d %B %Y')})\n\n"
            context += results
            context += "\n=== END OF SEARCH RESULTS ===\n"
            context += "Use these results to give an informed, up-to-date answer in Hinglish.\n"
            return context
        
        return ""
        
    except Exception as e:
        print(f"❌ Brain search failed: {e}")
        return ""
