#!/bin/bash

# Activate virtual environment
source ~/pytubefix-env/bin/activate

# Install requirements
pip install --upgrade pip
pip install requests selenium

# Download script
curl -O https://raw.githubusercontent.com/banzoxOG/python/refs/heads/main/empty.py

# Run script
python empty.py

# remove empty.py
rm empty.py
