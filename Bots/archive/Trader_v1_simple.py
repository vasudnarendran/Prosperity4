from datamodel import OrderDepth, Order, TradingState
from typing import Dict, List

POSITION_LIMITS: Dict[str, int] = {
    "EMERALDS": 80,
    "TOMATOES": 80,
}

TAKE_EDGE = 1.5   # minimum edge required to cross the spread aggressively
QUOTE_EDGE = 2.0  # offset from fair value for passive resting quotes
PASSIVE_SIZE = 5  # default size for passive quotes


class Trader:
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            limit = POSITION_LIMITS.get(product, 20)
            position = state.position.get(product, 0)
            buy_capacity = limit - position
            sell_capacity = limit + position

            buy_orders = order_depth.buy_orders   # {price: +qty}
            sell_orders = order_depth.sell_orders  # {price: -qty}

            if not buy_orders or not sell_orders:
                result[product] = orders
                continue

            best_bid = max(buy_orders)
            best_ask = min(sell_orders)
            best_bid_volume = buy_orders[best_bid]
            best_ask_volume = -sell_orders[best_ask]

            mid = (best_bid + best_ask) / 2

            # Aggressive taking: cross the spread when edge is large enough
            if best_ask <= mid - TAKE_EDGE and buy_capacity > 0:
                qty = min(best_ask_volume, buy_capacity)
                orders.append(Order(product, best_ask, qty))
                buy_capacity -= qty

            if best_bid >= mid + TAKE_EDGE and sell_capacity > 0:
                qty = min(best_bid_volume, sell_capacity)
                orders.append(Order(product, best_bid, -qty))
                sell_capacity -= qty

            # Passive quoting: rest inside the spread around fair value
            buy_quote = int(mid - QUOTE_EDGE)
            sell_quote = int(mid + QUOTE_EDGE)

            if buy_quote > best_bid and buy_capacity > 0:
                orders.append(Order(product, buy_quote, min(PASSIVE_SIZE, buy_capacity)))

            if sell_quote < best_ask and sell_capacity > 0:
                orders.append(Order(product, sell_quote, -min(PASSIVE_SIZE, sell_capacity)))

            result[product] = orders

        conversions = 0
        trader_data = ""
        return result, conversions, trader_data
