"""Example of executing a trade with an exact output amount."""

import asyncio
from renegade import OrderSide, ExternalOrder
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_async

async def fetch_quote_and_execute() -> None:
    """Fetch a quote and execute the trade."""
    # Create an order for 1 wETH
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.BUY,
        exact_quote_output=30_000_000, # $30 USDC
    )
    
    # Get a quote
    print("Fetching quote...")
    client = get_client()
    quote = await client.request_quote(order)
    
    # Assemble and execute the match
    print("Assembling quote...")
    bundle = await client.assemble_quote(quote)
    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute())
