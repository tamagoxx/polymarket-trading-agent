import subprocess
import os

os.chdir("D:/polymarket_trading_agent")

# Run git init
result = subprocess.run(["git", "init"], capture_output=True, text=True)
print("init:", result.stdout, result.stderr)

# Add all files
result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
print("add:", result.stdout, result.stderr)

# Commit
result = subprocess.run(["git", "commit", "-m", "Initial commit"], capture_output=True, text=True)
print("commit:", result.stdout, result.stderr)

# Push
result = subprocess.run(["git", "push", "-u", "origin", "main", "--force"], capture_output=True, text=True, input="\n")
print("push:", result.stdout, result.stderr)
