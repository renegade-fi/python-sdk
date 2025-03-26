"""Example of modifying an order before assembly."""

import asyncio
from renegade import OrderSide, ExternalOrder
from renegade.client import AssembleExternalMatchOptions
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_async

# Constants
BASE_MINT = "0xc3414a7ef14aaaa9c4522dfc00a4e66e74e9c25a"  # Testnet wETH
QUOTE_MINT = "0xdf8d259c04020562717557f2b5a3cf28e92707d1"  # Testnet USDC

async def fetch_quote_and_execute() -> None:
    """Fetch a quote, modify it, and execute the trade."""
    # Create the order
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.BUY,
        quote_amount=20_000_000,  # 20 USDC
        min_fill_size=1000000000000000,  # 0.001 WETH minimum
    )
    
    # Get a quote
    print("Fetching quote...")
    client = get_client()
    signed_quote = await client.request_quote(order)
    
    # Modify the order before assembly
    print("Assembling quote...")
    order.quote_amount = 19_000_000  # 19 USDC
    options = AssembleExternalMatchOptions().with_updated_order(order)
    bundle = await client.assemble_quote_with_options(signed_quote, options)
    if not bundle:
        raise ValueError("No bundle found")
    
    # Execute the bundle
    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute()) 