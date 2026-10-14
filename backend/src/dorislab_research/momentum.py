"""Monthly positive momentum, long plus cash; completed closes only, next-bar execution."""

from decimal import ROUND_DOWN, Decimal

from doribt import Context

from .backtest_request import BacktestRequest


class MonthlyMomentum:
    def __init__(self, request: BacktestRequest) -> None:
        self.request = request
        self.month = ""

    def __call__(self, ctx: Context) -> None:
        request = self.request
        if ctx.session < request.start or ctx.session >= request.end:
            return
        month = ctx.session.strftime("%Y-%m")
        if month == self.month:
            return
        self.month = month
        parameters = request.parameters
        momentum = {}
        for symbol in ctx.symbols:
            history = ctx.history(symbol, bars=parameters.lookback + 1)
            momentum[symbol] = float(history[-1] / history[0] - 1)
        selected = [
            s for s in sorted(momentum, key=lambda s: (-momentum[s], s)) if momentum[s] > 0
        ][: parameters.top_n]
        weights = {
            s: (parameters.max_exposure / len(selected)).quantize(
                Decimal("0.000001"), rounding=ROUND_DOWN
            )
            for s in selected
        }
        ctx.target_weights(weights, rebalance=True)
