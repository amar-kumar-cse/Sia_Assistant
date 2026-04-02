import os
import subprocess
import webbrowser
import urllib.parse
import platform

def git_commit_push(commit_msg="Auto-commit via Sia"):
    """
    Automatically adds, commits, and pushes to the current Git repository.
    """
    try:
        if not os.path.exists(".git"):
            return "❌ Current directory is not a Git repository."
            
        print("🔧 Running Git add...")
        subprocess.run(["git", "add", "."], check=True)
        
        print(f"🔧 Running Git commit: '{commit_msg}'...")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        print("🔧 Running Git push...")
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return "✅ Git Pushed right away! Code is live on GitHub. 🚀"
        else:
            return f"❌ Git push failed: {result.stderr[:100]}"
            
    except subprocess.CalledProcessError as e:
        return f"❌ Git command failed: {e}"
    except Exception as e:
        return f"❌ Git automation error: {e}"

def setup_python_env():
    """
    Creates a Python virtual environment and installs requirements.txt if present.
    """
    try:
        print("🔧 Creating virtual environment 'venv'...")
        if platform.system() == "Windows":
            subprocess.run(["py", "-m", "venv", "venv"], check=True)
            pip_cmd = os.path.join("venv", "Scripts", "pip")
        else:
            subprocess.run(["python3", "-m", "venv", "venv"], check=True)
            pip_cmd = os.path.join("venv", "bin", "pip")
            
        msg = "✅ Virtual environment 'venv' created successfully. "
        
        if os.path.exists("requirements.txt"):
            print("📦 Installing requirements...")
            subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
            msg += "Dependencies installed! 🐍"
        else:
            msg += "No requirements.txt found."
            
        return msg
        
    except Exception as e:
        return f"❌ Environment setup failed: {e}"

def draft_email(subject="Update from Amar", body="Hello, this is an automated message drafted by Sia."):
    """
    Drafts an email using the system's default mail client (mailto: protocol).
    """
    try:
        subject_encoded = urllib.parse.quote(subject)
        body_encoded = urllib.parse.quote(body)
        
        # open the mailto link
        mailto_url = f"mailto:?subject={subject_encoded}&body={body_encoded}"
        webbrowser.open(mailto_url)
        
        return "✅ Email draft opened in your default mail app! 📧"
    except Exception as e:
        return f"❌ Failed to draft email: {e}"
