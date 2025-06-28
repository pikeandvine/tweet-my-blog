"""
Random delay module for human-like variability
"""

import os
import random
import time

def apply_random_delay():
    """Apply a random delay if enabled via environment variable"""
    if os.getenv("ENABLE_DELAY", "false").lower() == "true":
        delay = random.randint(0, 180)
        print(f"Delaying execution by {delay} seconds for human-like variability...")
        time.sleep(delay)
    else:
        print("Delay disabled, proceeding immediately.")

if __name__ == "__main__":
    # Allow running this module directly for testing
    apply_random_delay() 