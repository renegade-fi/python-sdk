"""Example of validating a quote before execution."""

import asyncio
from renegade import OrderSide, ExternalOrder
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_async

async def fetch_quote_and_execute() -> None:
    """Fetch a quote, validate it, and execute the trade."""
    # Create the order
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.BUY,
        base_amount=8_000_000_000_000_000,  # 0.008 WETH
        min_fill_size=1_000_000_000_000_000,  # 0.001 wETH minimum
    )
    
    # Get a quote
    print("Fetching quote...")
    client = get_client()
    quote = await client.request_quote(order)
        
    # Check if the quote meets our minimum requirements
    if quote.quote.fees.total() > 4_000_000_000_000:  # Less than 1 wETH
        raise ValueError("Quote fees too high")
    
    # Assemble and execute the match
    print("Assembling quote...")
    bundle = await client.assemble_quote(quote)
    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute()) 