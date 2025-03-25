"""Example of executing a trade with in-kind gas sponsorship."""

import asyncio
from renegade import  OrderSide, ExternalOrder
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_async

# Constants
GAS_REFUND_ADDRESS = "0x99D9133afE1B9eC1726C077cA2b79Dcbb5969707"

async def fetch_quote_and_execute() -> None:
    """Fetch a quote and execute the trade."""
    # Create the order
    order = ExternalOrder(
        base_mint=BASE_MINT,
        quote_mint=QUOTE_MINT,
        side=OrderSide.SELL,
        quote_amount=30_000_000,  # $30 USDC
        min_fill_size=3_000_000,  # $3 USDC minimum
    )
    
    # Fetch a quote from the relayer with in-kind gas sponsorship.
    # Note that this is the default behavior, so no options need to be set.
    # Also note: When you leave the `refund_address` unset, the in-kind refund is
    # directed to the receiver address. This is equivalent to the trade itself
    # having a better price, so the price in the quote will be updated to
    # reflect this
    print("Fetching quote...")
    client = get_client()
    quote = await client.request_quote(order)
    if not quote:
        raise ValueError("No quote found")

    # Check for sponsorship
    if not quote.gas_sponsorship_info or quote.gas_sponsorship_info.gas_sponsorship_info.refund_native_eth:
            raise ValueError("Quote was not sponsored in-kind")
    
    # Assemble and execute the match
    print("Assembling quote...")
    bundle = await client.assemble_quote(quote)
    if not bundle.gas_sponsored:
        print("Gas not sponsored, aborting")
        return

    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute()) 