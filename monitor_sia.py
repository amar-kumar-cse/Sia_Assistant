import subprocess
import sys
import traceback
import time
from engine.automation import auto_heal_script # आपका पिछला फंक्शन

def run_and_monitor(script_name):
    print(f"[Monitor]: Starting {script_name} in safe mode...")
    
    while True:
        # मुख्य स्क्रिप्ट को एक सब-प्रोसेस के रूप में चलाना
        process = subprocess.Popen([sys.executable, script_name], 
                                   stderr=subprocess.PIPE, 
                                   text=True)
        
        # एरर (stderr) का इंतज़ार करना
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            print("\n" + "="*30)
            print(f"[Monitor]: CRASH DETECTED at {time.ctime()}")
            print(f"Error Log:\n{stderr}")
            print("="*30)
            
            # Auto-Heal इंजन को ट्रिगर करना
            print("[Monitor]: Triggering Auto-Heal Engine...")
            status = auto_heal_script(script_name, stderr)
            print(f"[Sia]: {status}")
            
            # थोड़ा रुककर फिर से रीस्टार्ट करना
            print("[Monitor]: Restarting in 5 seconds...\n")
            time.sleep(5)
            continue
        else:
            print("[Monitor]: Sia closed normally.")
            break

if __name__ == "__main__":
    run_and_monitor('main_sia.py')
