import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded if present
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

BLOCKCHAIN_RPC_URL = os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
if not BLOCKCHAIN_PRIVATE_KEY:
    raise RuntimeError(
        "BLOCKCHAIN_PRIVATE_KEY environment variable is required. "
        "Please configure a valid private key in .env or environment variables."
    )
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x71C8366420A0926718E29ce7705B732d43b91B32")
BLOCKCHAIN_CHAIN_ID = int(os.getenv("BLOCKCHAIN_CHAIN_ID", "31337"))
BLOCK_EXPLORER_BASE_URL = os.getenv("BLOCK_EXPLORER_BASE_URL", "https://amoy.polygonscan.com")
BLOCKCHAIN_NETWORK_NAME = os.getenv("BLOCKCHAIN_NETWORK_NAME", "polygon-amoy-testnet")
