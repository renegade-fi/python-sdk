# Renegade Python SDK
The Renegade Python SDK is a client library for interacting with the [Renegade](https://renegade.fi/) darkpool.

## Installation
```bash
uv add renegade-sdk
```
or
```bash
pip install renegade-sdk
```

# Usage
See [`examples/`](examples/) for usage examples.

## Basic Use
Todo... 

## External Matches
In addition to the standard darkpool flow -- deposit, place order, receive a match, then withdraw -- Renegade also supports *external* matches. An external match is a match between an internal party -- with state committed into the darkpool -- and an external party, with no state in the darkpool. Importantly, external matches are settled atomically; that is, the deposit, place order, match, withdraw flow is emulated in a _single transaction_ for the external party.

An external match is generated and submitted on-chain by a client (see `ExternalMatchClient`). The client submits an `ExternalOrder` to the relayer to fetch a quote, and the relayer will attempt to match it against all consenting internal orders. If a match is found, the relayer will respond to the client with a quote containing:
- The match itself, specifying the amount and mint (ERC20 address) of the tokens bought and sold, fees, etc.
- A signature of the quote; which allows the client to authoritatively assemble the quote into a match bundle

If the client is satisfied with the quote, it can assemble the quote into a match bundle, which contains:
- The match itself, specifying the amount and mint (ERC20 address) of the tokens bought and sold
- An EVM transaction that the external party may submit in order to settle the match with the darkpool

The client should then submit this match to the darkpool.

Upon receiving an external match, the darkpool contract will update the encrypted state of the internal party, and fulfill obligations to the external party directly through ERC20 transfers. As such, the external party must approve the token they _sell_ before the external match can be settled.


### Example
The following snippet demonstrates how to request an external match, assemble the quote into a match bundle, and submit the bundle to the darkpool. See [`examples/external_match.py`](examples/external_match.py) for a complete example.
```python
from renegade import ExternalMatchClient
from renegade.types import AtomicMatchApiBundle, OrderSide, ExternalOrder

# Constants
BASE_MINT = "0xc3414a7ef14aaaa9c4522dfc00a4e66e74e9c25a"  # Testnet wETH
QUOTE_MINT = "0xdf8d259c04020562717557f2b5a3cf28e92707d1"  # Testnet USDC

# Create the client
api_key = os.getenv("EXTERNAL_MATCH_KEY")
api_secret = os.getenv("EXTERNAL_MATCH_SECRET")
client = ExternalMatchClient.new_sepolia_client(api_key, api_secret)

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
quote = await client.request_quote(order)
if not quote:
    raise ValueError("No quote found")

# Assemble the quote into a bundle
print("Assembling quote...")
bundle = await client.assemble_quote(quote)
if not bundle:
    raise ValueError("No bundle found")

print(f"Received bundle: {bundle}")
```

## Gas Sponsorship

The Renegade relayer will cover the gas cost of external match transactions, up to a daily limit. When requested, the relayer will re-route the settlement transaction through a gas rebate contract. This contract refunds the cost of the transaction (in ether) to the configured address. If no address is given, the rebate is sent to `tx.origin`. 

To request gas sponsorship, simply add `with_gas_sponsorship` to the `AssembleExternalMatchOptions` type:
```python
# Refund address defaults to tx.origin
options = AssembleExternalMatchOptions.new().with_gas_sponsorship(True).with_gas_refund_address("0xdeadbeef")
bundle = client.assemble_quote_with_options(quote, options)
# ... Submit bundle ... #
```

For a full example, see [`examples/gas_sponsorship.py`](examples/gas_sponsorship.py).

### Gas Sponsorship Notes

- There is some overhead to the gas rebate contract, so the gas cost paid by the user is non-zero. This value is consistently around **17k gas**, or around **$0.0004** with current gas prices.
- The gas estimate returned by `eth_estimateGas` will _not_ reflect the rebate, as the rebate does not _reduce_ the gas used; it merely refunds the ether paid for the gas. If you wish to understand the true gas cost ahead of time, the transaction can be simulated (e.g. with `alchemy_simulateExecution` or similar).
- The rate limits currently sponsor up to **~500 matches/day** ($100 in gas). 

### Bundle Details
The *quote* returned by the relayer for an external match has the following structure:
- `order`: The original external order
- `match_result`: The result of the match, including:
- `fees`: The fees for the match
    - `relayer_fee`: The fee paid to the relayer
    - `protocol_fee`: The fee paid to the protocol
- `receive`: The asset transfer the external party will receive, *after fees are deducted*.
    - `mint`: The token address
    - `amount`: The amount to receive
- `send`: The asset transfer the external party needs to send. No fees are charged on the send transfer. (same fields as `receive`)
- `price`: The price used for the match
- `timestamp`: The timestamp of the quote

When assembled into a bundle (returned from `assemble_quote` or `request_external_match`), the structure is as follows:
- `match_result`: The final match result
- `fees`: The fees to be paid
- `receive`: The asset transfer the external party will receive
- `send`: The asset transfer the external party needs to send
- `settlement_tx`: The transaction to submit on-chain
    - `tx_type`: The transaction type
    - `to`: The contract address
    - `data`: The calldata
    - `value`: The ETH value to send

See example [`examples/quote_validation.py`](examples/quote_validation.py) for an example of using these fields to validate a quote before submitting it.

This can be run with
```bash
uv run examples/quote_validation.py
```

### Rate Limits
The rate limits for external match endpoints are as follows: 
- **Quote**: 100 requests per minute
- **Assemble**: 5 _unsettled_ bundles per minute. That is, if an assembled bundle is submitted on-chain, the rate limiter will reset. 
If an assembled match is not settled on-chain, the rate limiter will remove one token from the per-minute allowance.

### Supported Tokens
The tokens supported by the darkpool can be found at the following links:
- [Testnet](https://github.com/renegade-fi/token-mappings/blob/main/testnet.json)
- [Mainnet](https://github.com/renegade-fi/token-mappings/blob/main/mainnet.json)