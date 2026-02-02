#!/bin/bash

# Clear any temporary audio files before pushing
rm -f *.mp3 *.ogg

# Standard git update sequence
git add .
git commit -m "Update Vini: Fixed Song Search and Group Logic"
git push origin main

echo "✅ Vini update pushed successfully!"

alias 'update vini'='./push.sh'
