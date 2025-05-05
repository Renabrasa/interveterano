import sys
import os

# Caminho absoluto até a pasta onde está o main.py
sys.path.insert(0, os.path.dirname(__file__))

from main import app as application
