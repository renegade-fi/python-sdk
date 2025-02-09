import os
import asyncio
from dotenv import load_dotenv
from web3 import AsyncWeb3, Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.middleware import SignAndSendRawMiddlewareBuilder
from renegade import ExternalMatchClient
from renegade.types import (
    ExternalMatchResponse,
    OrderSide,
    ExternalOrder,
    ApiExternalQuote,
)

# Constants
BASE_MINT = "0xc3414a7ef14aaaa9c4522dfc00a4e66e74e9c25a"  # Testnet wETH
QUOTE_MINT = "0xdf8d259c04020562717557f2b5a3cf28e92707d1"  # Testnet USDC

# Validation constants
MIN_AMOUNT = 1000000000000000  # 0.001 WETH
MAX_FEE = 100000000000000  # 0.0001 WETH

def get_wallet() -> tuple[AsyncWeb3, LocalAccount]:
    """Get a Web3 instance and account from environment variables."""
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise ValueError("RPC_URL environment variable not set")

    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
    private_key = os.getenv("PKEY")
    if not private_key:
        raise ValueError("PKEY environment variable not set")
    
    account: LocalAccount = Account.from_key(private_key)
    w3.eth.default_account = account.address
    w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(private_key), layer=0)
    
    return w3, account

async def validate_quote(quote: ApiExternalQuote) -> None:
    """Validate a quote against minimum amount and maximum fee thresholds.
    
    Args:
        quote: The quote to validate
        
    Raises:
        ValueError: If the quote fails validation
    """
    total_fee = quote.fees.total()
    recv_amount = quote.receive.amount

    if recv_amount < MIN_AMOUNT:
        raise ValueError(f"Received amount {recv_amount} is less than the minimum amount {MIN_AMOUNT}")

    if total_fee > MAX_FEE:
        raise ValueError(f"Total fee {total_fee} is greater than the maximum fee {MAX_FEE}")

async def execute_bundle(bundle: ExternalMatchResponse) -> None:
    """Execute a settlement transaction bundle.
    
    Args:
        bundle: The bundle to execute
    """
    (w3, account) = get_wallet()

    print("\nSubmitting bundle...")
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

async def fetch_quote_and_execute(
    client: ExternalMatchClient,
    order: ExternalOrder,
) -> None:
    """Fetch a quote, validate it, and execute the trade.
    
    Args:
        client: The ExternalMatchClient to use
        order: The order to request a quote for
        
    Raises:
        ValueError: If no quote is found or validation fails
    """
    # Fetch a quote from the relayer
    print("Fetching quote...")
    quote = await client.request_quote(order)
    if not quote:
        raise ValueError("No quote found")
    
    # Validate the quote
    await validate_quote(quote.quote)
    
    # Assemble the quote into a bundle
    print("\nAssembling quote...")
    bundle = await client.assemble_quote(quote)
    if not bundle:
        raise ValueError("No bundle found")

    # Execute the bundle
    await execute_bundle(bundle)

async def main():
    # Load environment variables
    load_dotenv(override=True)

    # Get the external match client
    api_key = os.getenv("EXTERNAL_MATCH_KEY")
    api_secret = os.getenv("EXTERNAL_MATCH_SECRET")
    if not api_key or not api_secret:
        raise ValueError("EXTERNAL_MATCH_KEY and EXTERNAL_MATCH_SECRET must be set")

    client = ExternalMatchClient.new_sepolia_client(api_key, api_secret)

    # Create the order
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.BUY,
        base_amount=8000000000000000,  # 0.8 WETH
        min_fill_size=1000000000000000,  # 0.001 WETH minimum
    )

    await fetch_quote_and_execute(client, order)

if __name__ == "__main__":
    asyncio.run(main()) 