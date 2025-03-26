"""Example of executing a trade with native ETH gas sponsorship."""

import asyncio
from renegade import OrderSide, ExternalOrder
from examples.helpers import BASE_MINT, QUOTE_MINT, get_client, execute_bundle_async
from renegade.client import RequestQuoteOptions

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
    
    # Fetch a quote with native ETH gas sponsorship
    print("Fetching quote...")
    client = get_client()
    options = RequestQuoteOptions.new().with_refund_native_eth(True).with_gas_refund_address(GAS_REFUND_ADDRESS)
    quote = await client.request_quote_with_options(order, options)
    if not quote:
        raise ValueError("No quote found")
    
    if not quote.gas_sponsorship_info or not quote.gas_sponsorship_info.gas_sponsorship_info.refund_native_eth:
        raise ValueError("Quote was not sponsored with native ETH")
    
    print("\nAssembling quote...")
    bundle = await client.assemble_quote(quote)
    if not bundle:
        raise ValueError("No bundle found")
    
    await execute_bundle_async(bundle)

if __name__ == "__main__":
    asyncio.run(fetch_quote_and_execute()) 