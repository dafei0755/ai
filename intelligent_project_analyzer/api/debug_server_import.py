import sys
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
    import importlib

    prebuilt = importlib.import_module("langgraph.prebuilt")
    has_create = hasattr(prebuilt, "create_react_agent")
    print(f"Success: imported langgraph.prebuilt, create_react_agent={has_create}")
except ImportError as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
