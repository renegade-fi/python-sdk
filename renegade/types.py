from pydantic import BaseModel, ConfigDict, Field, model_validator
from enum import Enum
from typing import Optional, Dict, Any
from web3 import Web3
from web3.types import TxParams
import time

class OrderSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"

class BaseModelWithConfig(BaseModel):
    """Base model with common configuration"""
    model_config = ConfigDict(arbitrary_types_allowed=True, exclude_none=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        return self._remove_none_recursive(data)

    def _remove_none_recursive(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: self._remove_none_recursive(v)
                for k, v in data.items()
                if v is not None
            }
        elif isinstance(data, list):
            return [self._remove_none_recursive(item) for item in data]
        return data

class ApiExternalAssetTransfer(BaseModelWithConfig):
    mint: str
    amount: int

class ApiTimestampedPrice(BaseModelWithConfig):
    price: str
    timestamp: int

    @classmethod
    def now(cls, price: float) -> "ApiTimestampedPrice":
        return cls(
            price=str(price),
            timestamp=int(time.time() * 1000)
        )

class ApiExternalMatchResult(BaseModelWithConfig):
    quote_mint: str
    base_mint: str
    quote_amount: int
    base_amount: int
    direction: OrderSide

class FeeTake(BaseModelWithConfig):
    relayer_fee: int
    protocol_fee: int

    def total(self) -> int:
        return self.relayer_fee + self.protocol_fee

class ExternalOrder(BaseModelWithConfig):
    quote_mint: str
    base_mint: str
    side: OrderSide
    base_amount: Optional[int] = None
    quote_amount: Optional[int] = None
    exact_base_output: Optional[int] = None
    exact_quote_output: Optional[int] = None
    min_fill_size: int = 0

    def model_post_init(self, __context) -> None:
        self.quote_mint = Web3.to_checksum_address(self.quote_mint)
        self.base_mint = Web3.to_checksum_address(self.base_mint)

    @model_validator(mode='after')
    def validate_amounts(self) -> 'ExternalOrder':
        # Check if all amount fields are None or 0
        base_amt_none = self.base_amount is None or self.base_amount == 0
        quote_amt_none = self.quote_amount is None or self.quote_amount == 0
        exact_base_amt_none = self.exact_base_output is None or self.exact_base_output == 0
        exact_quote_amt_none = self.exact_quote_output is None or self.exact_quote_output == 0
        
        # Count how many amount fields are set
        amount_fields_set = sum(1 for x in [base_amt_none, quote_amt_none, exact_base_amt_none, exact_quote_amt_none] if not x)

        if amount_fields_set == 0:
            raise ValueError("One of base_amount, quote_amount, exact_base_amount, or exact_quote_amount must be set")
        if amount_fields_set > 1:
            raise ValueError("Only one of base_amount, quote_amount, exact_base_amount, or exact_quote_amount can be set")
            
        return self

class ApiExternalQuote(BaseModelWithConfig):
    order: ExternalOrder
    match_result: ApiExternalMatchResult
    fees: FeeTake
    send: ApiExternalAssetTransfer
    receive: ApiExternalAssetTransfer
    price: ApiTimestampedPrice
    timestamp: int

class ApiSignedExternalQuote(BaseModelWithConfig):
    quote: ApiExternalQuote
    signature: str

class GasSponsorshipInfo(BaseModelWithConfig):
    refund_amount: int
    refund_native_eth: bool
    refund_address: Optional[str] = None

class SignedGasSponsorshipInfo(BaseModelWithConfig):
    gas_sponsorship_info: GasSponsorshipInfo
    signature: str

class SignedExternalQuote(BaseModelWithConfig):
    quote: ApiExternalQuote
    signature: str
    gas_sponsorship_info: Optional[SignedGasSponsorshipInfo] = None

class AtomicMatchApiBundle(BaseModelWithConfig):
    match_result: ApiExternalMatchResult
    fees: FeeTake
    receive: ApiExternalAssetTransfer
    send: ApiExternalAssetTransfer
    settlement_tx: TxParams

class ExternalMatchRequest(BaseModelWithConfig):
    do_gas_estimation: bool = False
    receiver_address: Optional[str] = None
    external_order: Optional[ExternalOrder] = None

class ExternalMatchResponse(BaseModelWithConfig):
    match_bundle: AtomicMatchApiBundle
    # Whether the match has received gas sponsorship
    #
    # If `true`, the bundle is routed through a gas rebate contract that
    # refunds the gas used by the match to the configured address
    gas_sponsored: bool = Field(alias="is_sponsored", default=False)
    gas_sponsorship_info: Optional[GasSponsorshipInfo] = None

class ExternalQuoteRequest(BaseModelWithConfig):
    external_order: ExternalOrder

class ExternalQuoteResponse(BaseModelWithConfig):
    signed_quote: ApiSignedExternalQuote
    gas_sponsorship_info: Optional[SignedGasSponsorshipInfo] = None

class AssembleExternalMatchRequest(BaseModelWithConfig):
    do_gas_estimation: bool = False
    receiver_address: Optional[str] = None
    signed_quote: Optional[ApiSignedExternalQuote] = None
    updated_order: Optional[ExternalOrder] = None
