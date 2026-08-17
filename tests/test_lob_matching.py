from market.lob import LimitOrder, LimitOrderBook


def test_price_time_priority_and_partial_fills():
    book = LimitOrderBook()
    first = LimitOrder("a1", "sell", 100.0, 2, timestamp=1)
    second = LimitOrder("a2", "sell", 100.0, 3, timestamp=2)
    better = LimitOrder("a3", "sell", 99.5, 1, timestamp=3)
    book.add_limit_order(first)
    book.add_limit_order(second)
    book.add_limit_order(better)

    fills = book.match_market_order("taker", "buy", 4, timestamp=4)

    assert [(f.maker_agent_id, f.price, f.quantity) for f in fills] == [
        ("a3", 99.5, 1),
        ("a1", 100.0, 2),
        ("a2", 100.0, 1),
    ]
    assert book.best_ask() == 100.0
    assert book.depth("sell", levels=1) == [(100.0, 2)]


def test_cancel_agent_orders_removes_both_sides():
    book = LimitOrderBook()
    book.add_limit_order(LimitOrder("mm", "buy", 99.0, 1, 1))
    book.add_limit_order(LimitOrder("mm", "sell", 101.0, 1, 1))
    book.add_limit_order(LimitOrder("other", "sell", 102.0, 1, 1))

    removed = book.cancel_agent_orders("mm")

    assert removed == 2
    assert book.best_bid() is None
    assert book.best_ask() == 102.0


def test_crossing_limit_order_executes_immediately_and_rests_residual():
    book = LimitOrderBook()
    book.add_limit_order(LimitOrder("maker", "sell", 100.0, 2, 1))

    order_id, fills = book.submit_limit_order(LimitOrder("taker", "buy", 101.0, 3, 2))

    assert order_id is not None
    assert [(fill.maker_agent_id, fill.taker_agent_id, fill.price, fill.quantity) for fill in fills] == [
        ("maker", "taker", 100.0, 2)
    ]
    assert book.best_bid() == 101.0
    assert book.depth("buy") == [(101.0, 1)]


def test_stale_order_cancel_and_snapshot():
    book = LimitOrderBook()
    book.seed_liquidity_around_mid(100.0, timestamp=1, levels=2, quantity=5)

    snapshot = book.snapshot(timestamp=1)
    removed = book.cancel_stale_orders(now=10, max_age_steps=2, agent_id="external_liquidity")

    assert snapshot.bid_depth > 0
    assert snapshot.ask_depth > 0
    assert snapshot.spread is not None
    assert removed == 4
    assert book.best_bid() is None
