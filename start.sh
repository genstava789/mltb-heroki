#!/bin/sh

pip install --break-system-packages --no-cache-dir --requirement requirements.txt
python update.py
python -m bot