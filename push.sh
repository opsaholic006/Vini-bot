#!/bin/bash
git add .
read -p "What did you change? " msg
git commit -m "$msg"
git push origin main
echo "🚀 Code sent to GitHub! Railway is now updating Vini..."
