import subprocess
import os

repo_dir = "D:/polymarket_trading_agent"
os.chdir(repo_dir)

# Reinit git
subprocess.run(["git", "init"], check=True)

# Add files
subprocess.run(["git", "add", "."], check=True)

# Check status
result = subprocess.run(["git", "status"], capture_output=True, text=True)
print(result.stdout)
