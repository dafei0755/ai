import sys
import os
from pathlib import Path

# Mimic server.py path setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print(f"sys.path[0]: {sys.path[0]}")

try:
    import langgraph
    print(f"langgraph: {langgraph}")
    if hasattr(langgraph, '__path__'):
        print(f"langgraph path: {langgraph.__path__}")
except ImportError as e:
    print(f"Failed to import langgraph: {e}")

try:
    from langgraph.prebuilt import create_react_agent
    print("Success: imported create_react_agent")
except ImportError as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
