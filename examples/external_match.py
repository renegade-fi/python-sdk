import asyncio
from renegade.types import OrderSide, ExternalOrder
from examples.helpers import (
    BASE_MINT, QUOTE_MINT, get_client,
    execute_bundle_async
)

async def fetch_quote_and_execute() -> None:
    """Fetch a quote, validate it, and execute the trade.
    
    Raises:
        ValueError: If no quote is found
    """
    # Create the order
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.SELL,
        quote_amount=30_000_000,  # $30 USDC
        min_fill_size=3_000_000,  # $3 USDC minimum
    )

    # Fetch a quote from the relayer
    print("Fetching quote...")
    client = get_client()
    quote = await client.request_quote(order)
    if not quote:
        raise ValueError("No quote found")
    
    # Print quote details
    print(f"\nQuote details:")
    print(f"Receive amount: {quote.quote.receive.amount}")
    print(f"Total fees: {quote.quote.fees.total()}")
    
    # Assemble the quote into a bundle
    print("\nAssembling quote...")
    bundle = await client.assemble_quote(quote)
    if not bundle:
        raise ValueError("No bundle found")

    # Execute the bundle
    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute()) 
