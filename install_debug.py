import subprocess
import sys

# Get pip path (assuming we are running with the venv python)
python_exe = sys.executable

def install(package):
    print(f"--- Installing {package} ---")
    try:
        subprocess.check_call([python_exe, '-m', 'pip', 'install', package])
        print(f"SUCCESS: {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"FAILURE: {package}")
        return False

failed_packages = []

with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Remove comments after package name if any
        pkg = line.split('#')[0].strip()
        
        if not install(pkg):
            failed_packages.append(pkg)

print("\n\n=== SUMMARY ===")
if failed_packages:
    print("Failed packages:")
    for p in failed_packages:
        print(f"- {p}")
    sys.exit(1)
else:
    print("All packages installed successfully!")
    sys.exit(0)
