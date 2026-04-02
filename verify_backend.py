import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from engine import brain
from engine import actions

print("--- Testing Brain ---")
response = brain.think("Hello Sia!")
print(f"Sia: {response}")

print("\n--- Testing Actions ---")
action_result = actions.perform_action("What is my battery?")
print(f"Action: {action_result}")
