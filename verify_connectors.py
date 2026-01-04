
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import asyncio
from connectors.drive import DriveConnector
from connectors.notion import NotionConnector

try:
    print("Instantiating DriveConnector...")
    drive = DriveConnector()
    print("✅ DriveConnector instantiated successfully.")
except Exception as e:
    print(f"❌ Failed to instantiate DriveConnector: {e}")

try:
    print("Instantiating NotionConnector...")
    notion = NotionConnector()
    print("✅ NotionConnector instantiated successfully.")
except Exception as e:
    print(f"❌ Failed to instantiate NotionConnector: {e}")
