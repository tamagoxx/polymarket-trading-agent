@echo off
cd /d D:\polymarket_trading_agent
git init
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main
pause
