# check.py
import os
for f in os.listdir('.'):
    if f.endswith('.db'):
        print(f"Found: {f}")