"""
setup_wizard.py — First-Run GUI Setup Wizard for Sia Assistant
Runs on startup if .env or GEMINI_API_KEY is missing.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / ".env"


def check_and_run_wizard(force_gui: bool = False) -> bool:
    """
    Checks if valid GEMINI_API_KEY is configured in .env.
    If missing or force_gui is True, launches graphical wizard.
    """
    load_dotenv(dotenv_path=ENV_FILE)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if gemini_key and not force_gui and "your_" not in gemini_key.lower():
        return True  # Setup already complete

    print("🔑 Launching Sia Assistant First-Run Setup Wizard...")

    try:
        import tkinter as tk
        from tkinter import messagebox, ttk

        root = tk.Tk()
        root.title("Sia Assistant — First-Run Setup")
        root.geometry("520x420")
        root.resizable(False, False)
        root.configure(bg="#1E1E2E")

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1E1E2E", foreground="#CDD6F4", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#89B4FA", foreground="#11111B")
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#89B4FA")

        ttk.Label(root, text="✨ Welcome to Sia Assistant", style="Header.TLabel").pack(pady=(20, 5))
        ttk.Label(root, text="Configure your API keys to activate your personal AI companion.").pack(pady=(0, 20))

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True, padx=20)

        # Gemini Key
        ttk.Label(frame, text="Gemini API Key (Required):").grid(row=0, column=0, sticky="w", pady=5)
        gemini_entry = ttk.Entry(frame, width=45, show="*")
        gemini_entry.grid(row=1, column=0, sticky="ew", pady=5)
        if gemini_key and "your_" not in gemini_key.lower():
            gemini_entry.insert(0, gemini_key)

        # ElevenLabs Key
        ttk.Label(frame, text="ElevenLabs API Key (Optional for Premium Voice):").grid(row=2, column=0, sticky="w", pady=(15, 5))
        eleven_entry = ttk.Entry(frame, width=45, show="*")
        eleven_entry.grid(row=3, column=0, sticky="ew", pady=5)
        eleven_val = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if eleven_val and "your_" not in eleven_val.lower():
            eleven_entry.insert(0, eleven_val)

        # Model Choice
        ttk.Label(frame, text="Default Gemini Model:").grid(row=4, column=0, sticky="w", pady=(15, 5))
        model_combo = ttk.Combobox(frame, values=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"], state="readonly")
        model_combo.set(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
        model_combo.grid(row=5, column=0, sticky="ew", pady=5)

        saved = [False]

        def on_save():
            g_key = gemini_entry.get().strip()
            e_key = eleven_entry.get().strip()
            model = model_combo.get().strip()

            if not g_key:
                messagebox.showerror("Key Required", "Gemini API Key is required!\nGet free key at https://aistudio.google.com/app/apikey")
                return

            env_content = f"""# Sia Assistant Environment Configuration
GEMINI_API_KEY={g_key}
ELEVENLABS_API_KEY={e_key or 'your_elevenlabs_api_key_here'}
GEMINI_MODEL={model}
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL=eleven_turbo_v2
"""
            try:
                with open(ENV_FILE, "w", encoding="utf-8") as f:
                    f.write(env_content)
                load_dotenv(dotenv_path=ENV_FILE, override=True)
                saved[0] = True
                messagebox.showinfo("Setup Complete", "Configuration saved successfully! Launching Sia...")
                root.destroy()
            except Exception as exc:
                messagebox.showerror("Save Error", f"Failed to write .env file: {exc}")

        ttk.Button(root, text="🚀 Save & Start Sia", command=on_save).pack(pady=20)

        root.mainloop()
        return saved[0]

    except Exception as err:
        print(f"⚠️ GUI setup wizard failed ({err}), falling back to CLI prompt...")
        g_key = input("Enter your Gemini API Key: ").strip()
        if g_key:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={g_key}\nGEMINI_MODEL=gemini-1.5-flash\n")
            load_dotenv(dotenv_path=ENV_FILE, override=True)
            return True
        return False


if __name__ == "__main__":
    check_and_run_wizard(force_gui=True)
