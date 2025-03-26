"""Example of executing a trade synchronously."""

from renegade import OrderSide, ExternalOrder
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_sync

def fetch_quote_and_execute() -> None:
    """Fetch a quote and execute the trade."""
    
    # Create an order for 1 wETH
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.SELL,
        quote_amount=30_000_000,  # $30 USDC
        min_fill_size=3_000_000,  # $3 USDC minimum
    )
    
    # Get a quote
    print("Fetching quote...")
    client = get_client()
    quote = client.request_quote_sync(order)
    
    # Assemble and execute the match
    print("Assembling quote...")
    bundle = client.assemble_quote_sync(quote)
    execute_bundle_sync(bundle)

if __name__ == "__main__":
    fetch_quote_and_execute()