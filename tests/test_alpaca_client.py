import pytest
from alpaca.trading.enums import OrderClass, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

from src.core.contracts import OrderRequest
from src.core.data.alpaca_client import AlpacaClient, AlpacaCredentials


class DummyResponse:
    def model_dump(self) -> dict:
        return {"id": "order-1", "status": "accepted", "filled_qty": "0", "filled_avg_price": None}


class DummyTradingClient:
    def __init__(self) -> None:
        self.last_order = None
        self.called_with_kwargs = False

    def submit_order(self, *args, **kwargs):
        self.called_with_kwargs = "order_data" in kwargs
        self.last_order = kwargs.get("order_data") or (args[0] if args else None)
        return DummyResponse()


def build_client() -> AlpacaClient:
    credentials = AlpacaCredentials(
        api_key="key",
        secret_key="secret",
        trading_base_url="https://paper-api.alpaca.markets",
        data_base_url="https://data.alpaca.markets",
    )
    client = AlpacaClient(credentials=credentials, paper=True)
    client._trading = DummyTradingClient()
    return client


def test_submit_bracket_market_order_includes_bracket_fields():
    client = build_client()
    request = OrderRequest(
        symbol="AAPL",
        side="buy",
        quantity=10,
        order_type="market",
        time_in_force="day",
        stop_loss=145.0,
        take_profit=165.0,
    )
    client.submit_order(request)
    order = client._trading.last_order
    assert client._trading.called_with_kwargs is True
    assert isinstance(order, MarketOrderRequest)
    assert order.order_class == OrderClass.BRACKET
    assert order.take_profit.limit_price == 165.0
    assert order.stop_loss.stop_price == 145.0
    assert order.time_in_force == TimeInForce.DAY


def test_submit_limit_order_uses_limit_request():
    client = build_client()
    request = OrderRequest(
        symbol="MSFT",
        side="buy",
        quantity=5,
        order_type="limit",
        limit_price=310.5,
        time_in_force="gtc",
    )
    client.submit_order(request)
    order = client._trading.last_order
    assert client._trading.called_with_kwargs is True
    assert isinstance(order, LimitOrderRequest)
    assert order.limit_price == 310.5
    assert order.time_in_force == TimeInForce.GTC


def test_submit_limit_order_requires_price():
    client = build_client()
    request = OrderRequest(symbol="MSFT", side="buy", quantity=5, order_type="limit")
    with pytest.raises(ValueError, match="limit_price"):
        client.submit_order(request)
