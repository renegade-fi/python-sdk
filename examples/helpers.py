import os
from typing import Tuple, Optional
from dotenv import load_dotenv
from web3 import Web3, AsyncWeb3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.middleware import SignAndSendRawMiddlewareBuilder
from renegade import ExternalMatchClient
from renegade.types import ExternalMatchResponse

# Common constants
BASE_MINT = "0xc3414a7ef14aaaa9c4522dfc00a4e66e74e9c25a"  # Testnet wETH
QUOTE_MINT = "0xdf8d259c04020562717557f2b5a3cf28e92707d1"  # Testnet USDC

def get_wallet(is_async: bool = True) -> Tuple[Web3 | AsyncWeb3, LocalAccount]:
    """Get a Web3 instance and account from environment variables.
    
    Args:
        is_async: Whether to return an async Web3 instance
        
    Returns:
        A tuple of (Web3 instance, LocalAccount)
        
    Raises:
        ValueError: If required environment variables are not set
    """
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise ValueError("RPC_URL environment variable not set")

    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url)) if is_async else Web3(Web3.HTTPProvider(rpc_url))
    private_key = os.getenv("PKEY")
    if not private_key:
        raise ValueError("PKEY environment variable not set")
    
    account: LocalAccount = Account.from_key(private_key)
    w3.eth.default_account = account.address
    w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(private_key), layer=0)
    
    return w3, account

async def execute_bundle_async(bundle: ExternalMatchResponse) -> None:
    """Execute a settlement transaction bundle asynchronously.
    
    Args:
        bundle: The bundle to execute
    """
    (w3, account) = get_wallet(is_async=True)

    print("Submitting bundle...")
    tx = bundle.match_bundle.settlement_tx
    tx['to'] = Web3.to_checksum_address(tx['to'])
    
    # Add required transaction fields
    tx['nonce'] = await w3.eth.get_transaction_count(account.address)
    
    # Get current gas prices
    base_fee = await w3.eth.get_block('latest')
    max_priority_fee = await w3.eth.max_priority_fee
    max_fee_per_gas = 2 * base_fee.baseFeePerGas + max_priority_fee
    
    tx['maxFeePerGas'] = max_fee_per_gas
    tx['maxPriorityFeePerGas'] = max_priority_fee
    tx['chainId'] = await w3.eth.chain_id
    tx['from'] = account.address
    
    # Add gas estimation
    gas = await w3.eth.estimate_gas(tx)
    tx['gas'] = int(gas * 1.1)  # Add 10% buffer
    
    tx_hash = await w3.eth.send_transaction(tx)
    print(f"Transaction submitted: 0x{tx_hash.hex()}")

def execute_bundle_sync(bundle: ExternalMatchResponse) -> None:
    """Execute a settlement transaction bundle synchronously.
    
    Args:
        bundle: The bundle to execute
    """
    (w3, account) = get_wallet(is_async=False)

    print("Submitting bundle...")
    tx = bundle.match_bundle.settlement_tx
    tx['to'] = Web3.to_checksum_address(tx['to'])
    
    # Add required transaction fields
    tx['nonce'] = w3.eth.get_transaction_count(account.address)
    
    # Get current gas prices
    base_fee = w3.eth.get_block('latest')
    max_priority_fee = w3.eth.max_priority_fee
    max_fee_per_gas = 2 * base_fee.baseFeePerGas + max_priority_fee
    
    tx['maxFeePerGas'] = max_fee_per_gas
    tx['maxPriorityFeePerGas'] = max_priority_fee
    tx['chainId'] = w3.eth.chain_id
    tx['from'] = account.address
    
    # Add gas estimation
    gas = w3.eth.estimate_gas(tx)
    tx['gas'] = int(gas * 1.1)  # Add 10% buffer
    
    tx_hash = w3.eth.send_transaction(tx)
    print(f"Transaction submitted: 0x{tx_hash.hex()}")

def get_client() -> ExternalMatchClient:
    """Get an ExternalMatchClient instance from environment variables.
    
    Returns:
        An ExternalMatchClient instance configured for Sepolia testnet
        
    Raises:
        ValueError: If required environment variables are not set
    """
    load_dotenv(override=True)
    
    api_key = os.getenv("EXTERNAL_MATCH_KEY")
    api_secret = os.getenv("EXTERNAL_MATCH_SECRET")
    if not api_key or not api_secret:
        raise ValueError("EXTERNAL_MATCH_KEY and EXTERNAL_MATCH_SECRET must be set")

    return ExternalMatchClient.new_sepolia_client(api_key, api_secret) 