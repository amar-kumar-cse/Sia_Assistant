"""
Advanced Actions Module
Optimized system integration for Amar's workflow
"""

import webbrowser
import os
import subprocess
import platform
import memory

def open_url(url):
    """Open URL in default browser."""
    try:
        webbrowser.open(url)
        return f"✅ Opening {url}..."
    except Exception as e:
        return f"❌ Failed to open URL: {e}"

def open_file(filepath):
    """Open file with system default application."""
    if not os.path.exists(filepath):
        return f"❌ File not found: {filepath}"
    
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', filepath])
        else:  # Linux
            subprocess.run(['xdg-open', filepath])
        
        return f"✅ Opened: {os.path.basename(filepath)}"
    except Exception as e:
        return f"❌ Error opening file: {e}"

def open_resume():
    """
    Open Amar's professional resume/CV.
    Smart search across common locations.
    """
    # Get saved path from memory
    resume_path = memory.get_file_path("resume_path")
    
    if resume_path and os.path.exists(resume_path):
        return open_file(resume_path)
    
    # Search common locations
    user_home = os.path.expanduser("~")
    possible_locations = [
        os.path.join(user_home, "OneDrive", "Documents", "Resume.pdf"),
        os.path.join(user_home, "Documents", "Resume.pdf"),
        os.path.join(user_home, "Desktop", "Resume.pdf"),
        os.path.join(user_home, "OneDrive", "Desktop", "Resume.pdf"),
        os.path.join(user_home, "Downloads", "Resume.pdf"),
        # Also try .docx format
        os.path.join(user_home, "OneDrive", "Documents", "Resume.docx"),
        os.path.join(user_home, "Documents", "Resume.docx"),
        os.path.join(user_home, "Desktop", "Resume.docx"),
    ]
    
    for path in possible_locations:
        if os.path.exists(path):
            # Save for future use
            memory.update_file_path("resume_path", path)
            return open_file(path)
    
    return "❌ Resume not found! Please update path in memory.json → files → resume_path"

def open_college_portal():
    """
    Open RIT Roorkee college portal (CyborgERP).
    """
    portal_url = memory.get_file_path("college_portal")
    
    if not portal_url:
        portal_url = "https://cyborgerp.in/"
        memory.update_file_path("college_portal", portal_url)
    
    return open_url(portal_url)

def open_code_editor():
    """
    Open preferred code editor.
    Priority: VS Code → PyCharm → Notepad++
    """
    editors = [
        ("VS Code", "code"),
        ("PyCharm", "pycharm"),
        ("Notepad++", "notepad++")
    ]
    
    for name, command in editors:
        try:
            subprocess.Popen([command], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            return f"✅ Opening {name}..."
        except:
            continue
    
    return "❌ No code editor found. Install VS Code, PyCharm, or Notepad++"

def open_terminal():
    """Open terminal/command prompt."""
    try:
        if platform.system() == 'Windows':
            subprocess.Popen(['cmd'])
        else:
            subprocess.Popen(['gnome-terminal'])  # Linux
        return "✅ Terminal opened"
    except:
        return "❌ Failed to open terminal"

def perform_action(command_text):
    """
    Intelligent command parser.
    Detects intent and executes appropriate action.
    """
    cmd = command_text.lower()
    
    # Resume/CV commands
    if any(keyword in cmd for keyword in ["resume", "cv", "biodata", "bio data"]):
        return open_resume()
    
    # College portal commands
    if any(keyword in cmd for keyword in ["college", "portal", "cyborg", "erp", "rit"]):
        return open_college_portal()
    
    # Code editor commands
    if any(keyword in cmd for keyword in ["code editor", "vscode", "vs code", "pycharm", "editor"]):
        return open_code_editor()
    
    # Terminal commands  
    if any(keyword in cmd for keyword in ["terminal", "command prompt", "cmd", "powershell"]):
        return open_terminal()
    
    # Career sites (for TCS, J.P. Morgan applications)
    if "tcs" in cmd or "tata consultancy" in cmd:
        return open_url("https://www.tcs.com/careers")
    
    if "jp morgan" in cmd or "jpmorgan" in cmd or "j.p. morgan" in cmd:
        return open_url("https://careers.jpmorgan.com/")
    
    if "naukri" in cmd:
        return open_url("https://www.naukri.com")
    
    if "linkedin" in cmd:
        return open_url("https://www.linkedin.com")
    
    # Development sites
    if "github" in cmd:
        github_url = memory.get_file_path("github_profile")
        if not github_url:
            github_url = "https://github.com"  # Fallback
        return open_url(github_url)
    
    if "stackoverflow" in cmd or "stack overflow" in cmd:
        return open_url("https://stackoverflow.com")
    
    if "leetcode" in cmd:
        return open_url("https://leetcode.com")
    
    if "hackerrank" in cmd:
        return open_url("https://www.hackerrank.com")
    
    if "geeksforgeeks" in cmd or "gfg" in cmd:
        return open_url("https://www.geeksforgeeks.org")
    
    # Common sites
    if "google" in cmd:
        return open_url("https://www.google.com")
    
    if "youtube" in cmd:
        return open_url("https://www.youtube.com")
    
    if "gmail" in cmd or "mail" in cmd:
        return open_url("https://mail.google.com")
    
    # No action matched
    return None

# Quick action shortcuts (can be called directly)
def quick_resume():
    """Quick shortcut to open resume."""
    return open_resume()

def quick_portal():
    """Quick shortcut to open college portal."""
    return open_college_portal()

def quick_tcs():
    """Quick shortcut to TCS careers."""
    return open_url("https://www.tcs.com/careers")

def quick_jpmorgan():
    """Quick shortcut to J.P. Morgan careers."""
    return open_url("https://careers.jpmorgan.com/")
