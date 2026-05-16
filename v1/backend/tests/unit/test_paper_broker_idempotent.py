import asyncio
from decimal import Decimal

from app.brokers.paper import PaperBroker
from app.domain.order import OrderIntent, OrderSide


def test_resubmit_same_client_order_id_returns_same_order():
    async def run():
        b = PaperBroker()
        b.set_last_price("AAPL", Decimal("100"))
        intent = OrderIntent(symbol="AAPL", side=OrderSide.BUY, qty=Decimal("1"))
        o1 = await b.submit_order(intent)
        o2 = await b.submit_order(intent)
        assert o1.client_order_id == o2.client_order_id
        assert o1 is o2

    asyncio.run(run())
