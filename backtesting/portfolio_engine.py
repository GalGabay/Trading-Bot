"""Offline, shared-cash backtester for daily stock bars.

No broker client or order endpoint is imported here. Historical daily bars
are treated as completed only when their session ends; signals fill at the
following session's open. Entry limits are research approximations, not an
implementation of the complete paper-trading risk policy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import floor, isfinite

import pandas as pd

from app.ai.features import FeatureConfig, build_features
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles
from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.engine import BacktestConfig, BacktestPortfolio, SimulatedFill
from backtesting.protective_exits import (
    ProtectiveExitConfig, initial_stop, raised_stop, stop_reference,
)
from backtesting.research_policy import AllocationPolicy, HaltPolicy, ResearchHaltState
from backtesting.holding_policy import HoldingEntry, HoldingPolicy
from backtesting.universe import HistoricalUniverse, UniverseDataError
from backtesting.corporate_actions import feature_views, split_quantity


@dataclass(frozen=True)
class ResearchPortfolioLimits:
    """Configurable entry and loss gates; these do not approve paper trading."""

    max_portfolio_exposure: float = 0.70
    max_single_position: float = 0.10
    max_positions: int = 7
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.10

    def __post_init__(self) -> None:
        for name in ("max_portfolio_exposure", "max_single_position", "max_daily_loss", "max_drawdown"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be a finite fraction in (0, 1]")
        if self.max_single_position > self.max_portfolio_exposure:
            raise ValueError("max_single_position cannot exceed max_portfolio_exposure")
        if type(self.max_positions) is not int or self.max_positions < 1:
            raise ValueError("max_positions must be a positive integer")


@dataclass(frozen=True)
class PortfolioEquityPoint:
    timestamp: pd.Timestamp
    cash: float
    equity: float
    gross_exposure: float
    position_count: int
    drawdown: float
    dividend_receivable: float = 0.0


@dataclass(frozen=True)
class PortfolioBacktestResult:
    costs: BacktestConfig
    limits: ResearchPortfolioLimits
    buy_priority: str
    signals: tuple[Signal, ...]
    fills: tuple[SimulatedFill, ...]
    equity_curve: tuple[PortfolioEquityPoint, ...]
    events: tuple[str, ...]
    final_positions: dict[str, int]
    final_closes: dict[str, float]
    final_stops: dict[str, float]
    halted_at: str | None
    risk_events: tuple[dict, ...] = ()
    blocked_sessions_at_open: int = 0
    permanent_halt_reason: str | None = None
    halt_active_at_end: bool = False
    holding_reviews: tuple[dict, ...] = ()
    buy_decisions: tuple[dict, ...] = ()
    cash_settlements: tuple[dict, ...] = ()
    universe_metadata: dict | None = None
    share_actions: tuple[dict, ...] = ()
    dividend_entitlements: tuple[dict, ...] = ()
    dividend_payments: tuple[dict, ...] = ()
    final_dividend_receivables: tuple[dict, ...] = ()


@dataclass(frozen=True)
class _PendingOrder:
    signal: Signal
    planned_quantity: int | None = None
    stop_price: float | None = None
    execute_index: int = 0
    allocation_fraction: float | None = None


@dataclass(frozen=True)
class _ActiveStop:
    price: float
    armed_at: pd.Timestamp


class PortfolioBacktestEngine:
    """Run one rule across symbols with shared cash and synchronized sessions."""

    def __init__(
        self, strategy: Strategy, *, costs: BacktestConfig | None = None,
        limits: ResearchPortfolioLimits | None = None, buy_priority: str = "alphabetical",
        protection: ProtectiveExitConfig | None = None,
        reentry_cooldown_sessions: int = 0, execution_delay_sessions: int = 1,
        allocation: AllocationPolicy | None = None, halt_policy: HaltPolicy | None = None,
        restart_review: dict[pd.Timestamp, bool] | None = None,
        holding_policy: HoldingPolicy | None = None,
        holding_market_review: dict[pd.Timestamp, bool] | None = None,
        record_decisions: bool = False,
    ) -> None:
        if buy_priority not in {"alphabetical", "reverse"}:
            raise ValueError("buy_priority must be alphabetical or reverse")
        self.strategy = strategy
        self.costs = costs or BacktestConfig()
        self.limits = limits or ResearchPortfolioLimits()
        self.buy_priority = buy_priority
        self.protection = protection
        self.holding_policy = holding_policy
        self.holding_market_review = dict(holding_market_review or {})
        if holding_policy is not None and holding_policy.mode == "continuation" and holding_market_review is None:
            raise ValueError("Continuation holding policy requires exact-date market context")
        if any(type(value) is not bool for value in self.holding_market_review.values()):
            raise ValueError("Holding market context values must be boolean")
        if type(record_decisions) is not bool:
            raise ValueError("record_decisions must be boolean")
        self.record_decisions = record_decisions
        self.allocation = allocation or AllocationPolicy()
        self.halt_policy = halt_policy or HaltPolicy()
        if self.halt_policy.daily_pause_sessions is not None and restart_review is None:
            raise ValueError("A prior-session restart_review series is required for daily pauses")
        if restart_review is not None and any(type(value) is not bool for value in restart_review.values()):
            raise ValueError("Every restart_review value must be a boolean")
        self.restart_review = dict(restart_review or {})
        if type(reentry_cooldown_sessions) is not int or reentry_cooldown_sessions < 0:
            raise ValueError("reentry_cooldown_sessions must be a nonnegative integer")
        if type(execution_delay_sessions) is not int or execution_delay_sessions < 1:
            raise ValueError("execution_delay_sessions must be a positive integer")
        self.reentry_cooldown_sessions = reentry_cooldown_sessions
        self.execution_delay_sessions = execution_delay_sessions
        if protection is not None and (
            self.costs.slippage_bps + self.costs.spread_bps / 2 + protection.extra_stop_slippage_bps >= 10_000
        ):
            raise ValueError("Combined protective-stop selling costs must stay below 100%")

    def run(
        self, datasets: dict[str, pd.DataFrame], *, trade_start: pd.Timestamp,
        trade_end: pd.Timestamp,
        signal_datasets: dict[str, pd.DataFrame] | None = None,
        universe: HistoricalUniverse | None = None,
    ) -> PortfolioBacktestResult:
        """Use execution OHLC for fills and optional separate bars for signals.

        Separate signal data must have exactly the same symbols and timestamps.
        Signal prices plan quantities/stops; execution prices mark holdings and
        constrain fills. This isolates feed effects without filling gaps.

        Optional historical-universe mode uses stable IDs and the supplied
        calendar, with actual sparse observations only. It never infers IPOs
        or delisting proceeds. Separate signal feeds are not supported in
        this mode until their dated corporate-action conventions are audited.
        """
        start = self._utc_bound(trade_start)
        end = self._utc_bound(trade_end)
        if start >= end:
            raise ValueError("trade_start must precede trade_end")
        if not datasets:
            raise ValueError("At least one symbol dataset is required")
        if signal_datasets is not None and set(signal_datasets) != set(datasets):
            raise ValueError("Signal and execution dataset symbols must match")
        if universe is not None:
            if signal_datasets is not None:
                raise UniverseDataError("Historical-universe mode requires one audited execution/signal convention")
            if set(datasets) != universe.instrument_ids:
                raise UniverseDataError("Datasets must retain every declared stable instrument ID, including empty histories")

        bars: dict[str, pd.DataFrame] = {}
        features: dict[str, pd.DataFrame] = {}
        dates: pd.Series | None = None if universe is None else universe.dates
        segment_starts: dict[str, dict[int, int]] = {}
        feature_lookup: dict[str, dict[int, pd.DataFrame]] = {}
        for symbol, source in sorted(datasets.items()):
            if not symbol or symbol != symbol.strip().upper() or symbol in bars:
                raise ValueError("Dataset keys must be unique uppercase symbols")
            if universe is not None:
                frame = universe.prepare(symbol, source)
                bars[symbol] = frame
                feature_lookup[symbol], segment_starts[symbol] = feature_views(frame, symbol, universe, self.costs.periods_per_year)
                continue
            validate_candles(source)
            frame = source.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
            frame = frame.sort_values("timestamp", ignore_index=True)
            if set(frame["symbol"].astype(str).str.upper().str.strip()) != {symbol}:
                raise ValueError(f"{symbol}: dataset symbol differs from its key")
            if dates is None:
                dates = frame["timestamp"]
            elif not dates.equals(frame["timestamp"]):
                raise ValueError(f"{symbol}: session timestamps do not match the other datasets; no prices are filled")
            bars[symbol] = frame
            signal_frame = frame
            if signal_datasets is not None:
                validate_candles(signal_datasets[symbol])
                signal_frame = signal_datasets[symbol].loc[:, CANONICAL_CANDLE_COLUMNS].copy()
                signal_frame["timestamp"] = pd.to_datetime(signal_frame["timestamp"], utc=True)
                signal_frame = signal_frame.sort_values("timestamp", ignore_index=True)
                if set(signal_frame["symbol"].astype(str).str.upper().str.strip()) != {symbol}:
                    raise ValueError(f"{symbol}: signal dataset symbol differs from its key")
                if not frame["timestamp"].equals(signal_frame["timestamp"]):
                    raise ValueError(f"{symbol}: signal and execution session timestamps must match")
            features[symbol] = build_features(
                signal_frame, config=FeatureConfig(periods_per_year=self.costs.periods_per_year)
            )
        assert dates is not None
        indices = [index for index, timestamp in enumerate(dates) if start <= timestamp < end]
        if not indices:
            raise ValueError("No sessions fall in the requested trading window")
        symbols = sorted(bars)
        cash = self.costs.initial_cash
        positions: dict[str, int] = {}
        entries: dict[str, HoldingEntry] = {}
        holding_reviews: list[dict] = []
        buy_decisions: list[dict] = []
        stops: dict[str, _ActiveStop] = {}
        pending: dict[str, _PendingOrder] = {}
        next_entry_index: dict[str, int] = {}
        fills: list[SimulatedFill] = []
        signals: list[Signal] = []
        points: list[PortfolioEquityPoint] = []
        events: list[str] = []
        cash_settlements: list[dict] = []
        share_actions: list[dict] = []
        dividend_entitlements: list[dict] = []
        dividend_payments: list[dict] = []
        receivables: dict[str, dict] = {}
        peak = cash
        previous_close_equity = cash
        halt = ResearchHaltState(self.halt_policy, self.limits.max_daily_loss, self.limits.max_drawdown)
        multiplier = (self.costs.slippage_bps + self.costs.spread_bps / 2) / 10_000

        def journal(symbol, phase, status, blockers=(), *, order=None, quantity=None, constraints=None):
            if not self.record_decisions:
                return
            marks = open_prices if phase == "open" else close_prices
            value = cash + sum(item["amount"] for item in receivables.values()) + sum(qty * marks[name] for name, qty in positions.items())
            buy_decisions.append({
                "timestamp": timestamp.isoformat(), "symbol": symbol, "phase": phase,
                "status": status, "blockers": list(blockers), "cash": cash, "equity": value,
                "position_count": len(positions), "held_ages": {name: index - entry.session_index + 1 for name, entry in entries.items()},
                "signal_timestamp": None if order is None else pd.Timestamp(order.signal.timestamp).isoformat(),
                "planned_quantity": None if order is None else order.planned_quantity,
                "quantity": quantity, "quantity_constraints": constraints or {},
            })

        def observe_loss(phase: str, value: float, index: int, timestamp: pd.Timestamp) -> None:
            prior_date = dates.iloc[index - 1] if index > 0 else None
            changes = halt.observe(
                index=index, timestamp=timestamp.isoformat(), phase=phase,
                equity=value, previous_close=previous_close_equity, peak=peak,
                review_ready=bool(self.restart_review.get(prior_date, False)),
            )
            for change in changes:
                if change["kind"] == "restart":
                    events.append(f"{timestamp.isoformat()}: research daily halt resumed after prior-session review")
                else:
                    events.append(f"{timestamp.isoformat()}: entry halt at {phase}: {change['reason']}; SELLs remain permitted")

        for index in indices:
            timestamp = dates.iloc[index]
            available_symbols = symbols if universe is None else [s for s in symbols if index in feature_lookup[s]]
            if universe is not None:
                for symbol in available_symbols:
                    features[symbol] = feature_lookup[symbol][index]
            open_prices = {symbol: float(bars[symbol].loc[index]["open"]) for symbol in available_symbols}
            low_prices = {symbol: float(bars[symbol].loc[index]["low"]) for symbol in available_symbols}
            close_prices = {symbol: float(bars[symbol].loc[index]["close"]) for symbol in available_symbols}
            signal_closes = {symbol: float(features[symbol].loc[index]["close"]) for symbol in available_symbols}
            due = {symbol: order for symbol, order in pending.items() if order.execute_index == index}
            pending = {symbol: order for symbol, order in pending.items() if order.execute_index > index}

            if universe is not None:
                for action in universe.splits_at(timestamp):
                    symbol = action.instrument_id
                    quantity = positions.get(symbol, 0)
                    new_quantity = split_quantity(quantity, action.new_shares, action.old_shares)
                    if quantity:
                        positions[symbol] = new_quantity
                        entries[symbol] = replace(entries[symbol], quantity=new_quantity)
                    if symbol in stops:
                        stops[symbol] = replace(stops[symbol], price=stops[symbol].price / action.ratio)
                    for orders in (pending, due):
                        if symbol in orders:
                            order = orders[symbol]
                            orders[symbol] = replace(
                                order,
                                planned_quantity=None if order.planned_quantity is None else order.planned_quantity * action.new_shares // action.old_shares,
                                stop_price=None if order.stop_price is None else order.stop_price / action.ratio,
                            )
                    share_actions.append({
                        "timestamp": timestamp.isoformat(), "event_id": action.event_id, "instrument_id": symbol,
                        "old_quantity": quantity, "new_quantity": new_quantity, "new_shares": action.new_shares,
                        "old_shares": action.old_shares, "source": action.source,
                    })
                # Ordinary ex-date entitlement belongs to prior holders, before
                # today's discretionary sales/buys. Same-day splits apply first.
                for dividend in universe.dividends_at(timestamp):
                    quantity = positions.get(dividend.instrument_id, 0)
                    if quantity:
                        claim = {"timestamp": timestamp.isoformat(), "event_id": dividend.event_id,
                                 "instrument_id": dividend.instrument_id, "quantity": quantity,
                                 "cash_per_share": dividend.cash_per_share, "amount": quantity * dividend.cash_per_share,
                                 "pay_session": dividend.pay_session, "source": dividend.source}
                        receivables[dividend.event_id] = claim
                        dividend_entitlements.append(dict(claim))
                for event_id, claim in list(receivables.items()):
                    if claim["pay_session"] == timestamp.date().isoformat():
                        cash += claim["amount"]
                        dividend_payments.append({**claim, "timestamp": timestamp.isoformat()})
                        del receivables[event_id]
                for outcome in universe.outcomes_at(timestamp):
                    symbol = outcome.instrument_id
                    pending.pop(symbol, None)
                    due.pop(symbol, None)
                    quantity = positions.pop(symbol, 0)
                    stops.pop(symbol, None)
                    if quantity:
                        entry = entries.pop(symbol)
                        proceeds = quantity * outcome.cash_per_share
                        cash += proceeds
                        cash_settlements.append({
                            "timestamp": timestamp.isoformat(), "event_id": outcome.event_id,
                            "instrument_id": symbol, "quantity": quantity,
                            "cash_per_share": outcome.cash_per_share, "total_cash": proceeds,
                            "realized_pnl": proceeds - entry.cost_basis,
                            "known_at": outcome.known_at, "source": outcome.source,
                        })
                        events.append(f"{timestamp.isoformat()} {symbol}: verified terminal cash payment {proceeds:g}; not a trade fill")
                unavailable_held = set(positions) - set(available_symbols)
                if unavailable_held:
                    raise UniverseDataError(
                        f"{timestamp.isoformat()}: held instruments lack a positive-volume bar or verified cash payment: "
                        f"{sorted(unavailable_held)}. No stale mark, invented sale or assumed zero recovery is permitted."
                    )
                for symbol in sorted(set(due) - set(available_symbols)):
                    events.append(f"{timestamp.isoformat()} {symbol}: expired {due[symbol].signal.action.value}; scheduled execution session unavailable")
                    due.pop(symbol)

            exited_by_stop: set[str] = set()
            if self.protection is not None:
                # These stops were armed no later than the preceding close.
                # Opening gaps are resolved before queued trend exits/buys.
                for symbol in sorted(stops):
                    state = stops[symbol]
                    triggered = stop_reference(open_prices[symbol], low_prices[symbol], state.price)
                    if triggered is None or open_prices[symbol] > state.price:
                        continue
                    quantity = positions.pop(symbol)
                    entries.pop(symbol)
                    fill = self._stop_fill(
                        timestamp, symbol, quantity, state, open_prices[symbol], triggered[0], triggered[1]
                    )
                    cash += quantity * fill.fill_price - fill.commission
                    fills.append(fill)
                    exited_by_stop.add(symbol)
                    next_entry_index[symbol] = index + self.reentry_cooldown_sessions + 1
                    pending.pop(symbol, None)
                    events.append(f"{timestamp.isoformat()} {symbol}: protective stop at open, level={state.price:g}, fill={fill.fill_price:g}")
                for symbol in exited_by_stop:
                    del stops[symbol]

            # Orders originated at the previous completed close. Release cash
            # from all exits before considering competing entries.
            for symbol in sorted(due):
                signal = due[symbol].signal
                if signal.action != SignalAction.SELL:
                    continue
                if symbol in exited_by_stop:
                    continue
                quantity = positions.pop(symbol, 0)
                if not quantity:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped SELL; no position")
                    continue
                entries.pop(symbol)
                stops.pop(symbol, None)
                price = open_prices[symbol] * (1 - multiplier)
                cash += quantity * price - self.costs.commission_per_order
                fills.append(self._fill(timestamp, signal, quantity, open_prices[symbol], price))
                next_entry_index[symbol] = index + self.reentry_cooldown_sessions + 1

            claim_value = sum(item["amount"] for item in receivables.values())
            open_equity = cash + claim_value + sum(quantity * open_prices[symbol] for symbol, quantity in positions.items())
            if open_equity <= 0:
                raise ValueError("Portfolio equity became nonpositive at an open")
            observe_loss("open", open_equity, index, timestamp)
            halt.blocked_at_open += int(halt.blocked)
            if halt.blocked and self.halt_policy.daily_pause_sessions is not None:
                pending = {symbol: order for symbol, order in pending.items() if order.signal.action != SignalAction.BUY}

            buy_symbols = sorted(due, reverse=self.buy_priority == "reverse")
            for symbol in buy_symbols:
                order = due[symbol]
                signal = order.signal
                if signal.action != SignalAction.BUY:
                    continue
                if halt.blocked:
                    journal(symbol, "open", "blocked", ("entry_halt",), order=order)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; entry halt active")
                    continue
                if symbol in positions:
                    journal(symbol, "open", "blocked", ("already_held",), order=order)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; position already open")
                    continue
                if index < next_entry_index.get(symbol, 0):
                    journal(symbol, "open", "blocked", ("cooldown",), order=order)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; reentry cooldown")
                    continue
                if len(positions) >= self.limits.max_positions:
                    journal(symbol, "open", "blocked", ("position_count",), order=order)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; position-count limit")
                    continue
                equity = cash + claim_value + sum(quantity * open_prices[name] for name, quantity in positions.items())
                gross = sum(quantity * open_prices[name] for name, quantity in positions.items())
                price = open_prices[symbol] * (1 + multiplier)
                stop = order.stop_price
                if self.protection is not None and (stop is None or open_prices[symbol] <= stop or price <= stop):
                    journal(symbol, "open", "blocked", ("stop_at_or_above_open",), order=order)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; open is at or below planned stop")
                    continue
                budget = min(
                    self.costs.position_fraction * equity,
                    self.limits.max_single_position * equity,
                    self.limits.max_portfolio_exposure * equity - gross,
                    cash - self.costs.commission_per_order,
                )
                if order.allocation_fraction is not None:
                    budget = min(budget, order.allocation_fraction * equity)
                # The signal-close quantity is a ceiling: a favorable next
                # open cannot enlarge an order using information unavailable
                # when the order was planned. Gaps can reduce or reject it.
                quantity = min(order.planned_quantity or 0, floor(max(0.0, budget) / price))
                constraints = {
                    "planned_quantity": order.planned_quantity or 0,
                    "single_position_value": floor(min(self.costs.position_fraction, self.limits.max_single_position) * equity / price),
                    "portfolio_exposure": floor(max(0, self.limits.max_portfolio_exposure * equity - gross) / price),
                    "cash_after_commission": floor(max(0, cash - self.costs.commission_per_order) / price),
                }
                if order.allocation_fraction is not None:
                    constraints["volatility_sizing"] = floor(order.allocation_fraction * equity / price)
                if self.protection is not None:
                    assert stop is not None
                    risk_quantity = floor(
                        self.protection.max_risk_per_trade * equity / (price - stop)
                    )
                    quantity = min(quantity, risk_quantity)
                    constraints["stop_risk"] = risk_quantity
                if quantity < 1:
                    journal(symbol, "open", "blocked", tuple(name for name, cap in constraints.items() if cap < 1), order=order, quantity=0, constraints=constraints)
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; cash, exposure, or stop-risk limit")
                    continue
                journal(symbol, "open", "filled", order=order, quantity=quantity, constraints=constraints)
                cash -= quantity * price + self.costs.commission_per_order
                positions[symbol] = quantity
                entries[symbol] = HoldingEntry(index, quantity, quantity * price + self.costs.commission_per_order)
                if self.protection is not None:
                    stops[symbol] = _ActiveStop(stop, pd.Timestamp(signal.timestamp))
                fills.append(self._fill(timestamp, signal, quantity, open_prices[symbol], price))

            if self.protection is not None:
                # A stop armed before this session can be touched after the
                # open, including on the session in which the BUY filled.
                for symbol in sorted(stops):
                    state = stops[symbol]
                    triggered = stop_reference(open_prices[symbol], low_prices[symbol], state.price)
                    if triggered is None:
                        continue
                    quantity = positions.pop(symbol)
                    entries.pop(symbol)
                    fill = self._stop_fill(
                        timestamp, symbol, quantity, state, open_prices[symbol], triggered[0], triggered[1]
                    )
                    cash += quantity * fill.fill_price - fill.commission
                    fills.append(fill)
                    next_entry_index[symbol] = index + self.reentry_cooldown_sessions + 1
                    pending.pop(symbol, None)
                    events.append(f"{timestamp.isoformat()} {symbol}: protective stop touched, level={state.price:g}, fill={fill.fill_price:g}")
                    del stops[symbol]
            if cash < -1e-6 or len(positions) > self.limits.max_positions:
                raise ValueError("Shared cash or position-count invariant failed")

            equity = cash + claim_value + sum(quantity * close_prices[symbol] for symbol, quantity in positions.items())
            if equity <= 0:
                raise ValueError("Portfolio equity became nonpositive at a close")
            peak = max(peak, equity)
            gross_close = sum(quantity * close_prices[symbol] for symbol, quantity in positions.items())
            points.append(PortfolioEquityPoint(
                timestamp=timestamp, cash=cash, equity=equity,
                gross_exposure=gross_close / equity, position_count=len(positions),
                drawdown=equity / peak - 1,
                dividend_receivable=claim_value,
            ))
            observe_loss("close", equity, index, timestamp)
            if halt.blocked and self.halt_policy.daily_pause_sessions is not None:
                pending = {symbol: order for symbol, order in pending.items() if order.signal.action != SignalAction.BUY}
            previous_close_equity = equity

            if self.protection is not None:
                for symbol in sorted(stops):
                    state = stops[symbol]
                    atr = float(features[symbol].loc[index]["atr_14"])
                    next_stop = raised_stop(state.price, signal_closes[symbol], atr, self.protection)
                    if next_stop > state.price:
                        stops[symbol] = _ActiveStop(next_stop, timestamp)
                        events.append(f"{timestamp.isoformat()} {symbol}: trailing stop raised to {next_stop:g}")

            # Every strategy call receives only that symbol's completed bars.
            for symbol in available_symbols:
                history = features[symbol].loc[:index]
                if universe is not None:
                    history = history.loc[segment_starts[symbol][index]:]
                available = (
                    features[symbol].loc[[index]] if self.strategy.latest_row_only
                    else history
                )
                signal = self.strategy.generate_signal(
                    available, BacktestPortfolio(cash, positions.get(symbol, 0), equity)
                )
                if signal.symbol.strip().upper() != symbol or pd.Timestamp(signal.timestamp) != timestamp:
                    raise ValueError(f"{symbol}: strategy returned a mismatched signal")
                pending_sell = symbol in pending and pending[symbol].signal.action == SignalAction.SELL
                if self.holding_policy is not None and symbol in positions and signal.action != SignalAction.SELL and not pending_sell:
                    market_on = True
                    if self.holding_policy.mode == "continuation":
                        if timestamp not in self.holding_market_review:
                            raise ValueError(f"Missing exact-date holding market context: {timestamp}")
                        market_on = self.holding_market_review[timestamp]
                    review = self.holding_policy.review(
                        history, entries[symbol], index,
                        market_on=market_on, sale_multiplier=multiplier,
                        sale_commission=self.costs.commission_per_order,
                    )
                    if review is not None:
                        holding_reviews.append(review)
                        if review["decision"] == "exit":
                            signal = Signal(symbol, SignalAction.SELL, 1.0, review["reason"], timestamp.to_pydatetime(), self.strategy.name)
                signals.append(signal)
                if signal.action in {SignalAction.BUY, SignalAction.SELL}:
                    if symbol in pending:
                        continue  # Keep one pending order and its original quantity.
                    planned_quantity = None
                    stop_price = None
                    fraction = None
                    if signal.action == SignalAction.BUY:
                        if universe is not None and len(history) < 200:
                            journal(symbol, "close", "blocked", ("historical_universe_200_session_warmup",))
                            events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; 200 continuous tradable sessions required")
                            continue
                        if halt.blocked and self.halt_policy.daily_pause_sessions is not None:
                            journal(symbol, "close", "blocked", ("entry_halt",))
                            events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY planning; entry halt active")
                            continue
                        fraction = self.allocation.fraction(
                            min(self.costs.position_fraction, self.limits.max_single_position),
                            float(features[symbol].loc[index]["historical_volatility_20"]),
                        )
                        if fraction is None:
                            journal(symbol, "close", "blocked", ("missing_volatility",))
                            events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; valid completed volatility unavailable")
                            continue
                        planned_budget = fraction * equity
                        if self.protection is not None:
                            atr = float(features[symbol].loc[index]["atr_14"])
                            stop_price = initial_stop(signal_closes[symbol], atr, self.protection)
                            if stop_price is None:
                                journal(symbol, "close", "blocked", ("missing_atr_stop",))
                                events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; valid ATR stop unavailable")
                                continue
                            planned_entry = signal_closes[symbol] * (1 + multiplier)
                            planned_budget = min(
                                planned_budget,
                                self.protection.max_risk_per_trade * equity
                                * planned_entry / (planned_entry - stop_price),
                            )
                        planned_quantity = floor(
                            planned_budget / (signal_closes[symbol] * (1 + multiplier))
                        )
                        if planned_quantity < 1:
                            journal(symbol, "close", "blocked", ("planned_sizing_below_one_share",), quantity=0)
                            events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; planned stop-risk size below one share")
                            continue
                        journal(symbol, "close", "queued", quantity=planned_quantity)
                    pending[symbol] = _PendingOrder(
                        signal, planned_quantity, stop_price, index + self.execution_delay_sessions,
                        fraction if self.allocation.annualized_risk_contribution is not None else None,
                    )

        for symbol, order in sorted(pending.items()):
            signal = order.signal
            events.append(f"{symbol}: unfilled {signal.action.value} signal at {signal.timestamp.isoformat()}; no next session")
        if self.protection is not None and set(stops) != set(positions):
            raise ValueError("Every open position must have exactly one active protective stop")
        return PortfolioBacktestResult(
            costs=self.costs, limits=self.limits, buy_priority=self.buy_priority,
            signals=tuple(signals), fills=tuple(fills), equity_curve=tuple(points),
            events=tuple(events), final_positions=dict(sorted(positions.items())),
            final_closes=close_prices,
            final_stops={symbol: state.price for symbol, state in sorted(stops.items())},
            halted_at=halt.first_halted_at, risk_events=tuple(halt.events),
            blocked_sessions_at_open=halt.blocked_at_open,
            permanent_halt_reason=halt.permanent_reason, halt_active_at_end=halt.blocked,
            holding_reviews=tuple(holding_reviews), buy_decisions=tuple(buy_decisions),
            cash_settlements=tuple(cash_settlements),
            universe_metadata=None if universe is None else universe.metadata(),
            share_actions=tuple(share_actions), dividend_entitlements=tuple(dividend_entitlements),
            dividend_payments=tuple(dividend_payments), final_dividend_receivables=tuple(receivables.values()),
        )

    def _loss_breach(self, equity: float, prior_close: float, peak: float) -> str | None:
        if equity <= peak * (1 - self.limits.max_drawdown):
            return "maximum drawdown reached"
        if equity <= prior_close * (1 - self.limits.max_daily_loss):
            return "daily loss limit reached"
        return None

    def _fill(
        self, timestamp: pd.Timestamp, signal: Signal, quantity: int,
        reference_open: float, price: float,
    ) -> SimulatedFill:
        return SimulatedFill(
            timestamp=timestamp, symbol=signal.symbol, side=signal.action,
            quantity=quantity, reference_open=reference_open, fill_price=price,
            commission=self.costs.commission_per_order,
            signal_timestamp=pd.Timestamp(signal.timestamp), signal_reason=signal.reason,
        )

    def _stop_fill(
        self, timestamp: pd.Timestamp, symbol: str, quantity: int,
        state: _ActiveStop, open_price: float, reference_price: float, gap: bool,
    ) -> SimulatedFill:
        assert self.protection is not None
        multiplier = (
            self.costs.slippage_bps + self.costs.spread_bps / 2
            + self.protection.extra_stop_slippage_bps
        ) / 10_000
        reason = "PROTECTIVE_STOP_GAP_OPEN" if gap else "PROTECTIVE_STOP_TOUCH"
        signal = Signal(
            symbol=symbol, action=SignalAction.SELL, confidence=1.0,
            reason=f"{reason}: active stop {state.price:g}",
            timestamp=state.armed_at.to_pydatetime(), strategy=self.strategy.name,
        )
        return self._fill(
            timestamp, signal, quantity, reference_open=open_price,
            price=reference_price * (1 - multiplier),
        )

    @staticmethod
    def _utc_bound(value: pd.Timestamp) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            raise ValueError("Trading-window bounds must be timezone-aware")
        return timestamp.tz_convert("UTC")


def summarize_portfolio(result: PortfolioBacktestResult) -> dict[str, object]:
    """Summarize a continuous account, including realized and open P&L."""
    points = result.equity_curve
    if not points:
        raise ValueError("No equity observations")
    annual_returns: dict[str, float] = {}
    prior_year_end = result.costs.initial_cash
    yearly_last: dict[int, float] = {}
    for point in points:
        year = point.timestamp.tz_convert("America/New_York").year
        yearly_last[year] = point.equity
    for year, equity in sorted(yearly_last.items()):
        annual_returns[str(year)] = equity / prior_year_end - 1
        prior_year_end = equity

    entries: dict[str, SimulatedFill] = {}
    realized: dict[str, float] = {}
    profits: list[float] = []
    durations: list[float] = []
    settlement_profits: list[float] = []
    ledger = [(fill.timestamp, 1, i, fill) for i, fill in enumerate(result.fills)]
    ledger += [(pd.Timestamp(item["timestamp"]), 0, i, item) for i, item in enumerate(result.cash_settlements)]
    ledger += [(pd.Timestamp(item["timestamp"]), -2, i, item) for i, item in enumerate(result.share_actions)]
    ledger += [(pd.Timestamp(item["timestamp"]), -1, i, item) for i, item in enumerate(result.dividend_entitlements)]
    claims: dict[str, dict] = {}
    for _, kind, _, fill in sorted(ledger, key=lambda item: item[:3]):
        if kind == -2:
            symbol = fill["instrument_id"]
            entry = entries.get(symbol)
            if (0 if entry is None else entry.quantity) != fill["old_quantity"]:
                raise ValueError("Split ledger does not match owned shares")
            expected = split_quantity(fill["old_quantity"], fill["new_shares"], fill["old_shares"])
            if expected != fill["new_quantity"]:
                raise ValueError("Split ledger has an inconsistent share conversion")
            if entry is not None:
                entries[symbol] = replace(entry, quantity=expected, fill_price=entry.fill_price * fill["old_shares"] / fill["new_shares"])
            continue
        if kind == -1:
            entry = entries.get(fill["instrument_id"])
            if entry is None or entry.quantity != fill["quantity"] or fill["event_id"] in claims:
                raise ValueError("Dividend entitlement does not match prior owned shares or is duplicated")
            if abs(fill["amount"] - entry.quantity * fill["cash_per_share"]) > 1e-6:
                raise ValueError("Dividend entitlement amount differs from its share rate")
            claims[fill["event_id"]] = fill
            continue
        if kind == 0:
            symbol = fill["instrument_id"]
            entry = entries.pop(symbol, None)
            if entry is None or entry.quantity != fill["quantity"]:
                raise ValueError("Terminal cash settlement does not resolve its exact entry")
            profit = entry.quantity * fill["cash_per_share"] - entry.quantity * entry.fill_price - entry.commission
            if abs(profit - fill["realized_pnl"]) > 1e-6 or abs(fill["total_cash"] - entry.quantity * fill["cash_per_share"]) > 1e-6:
                raise ValueError("Terminal cash settlement accounting differs from its entry")
            settlement_profits.append(profit)
            realized[symbol] = realized.get(symbol, 0.0) + profit
            continue
        if fill.side == SignalAction.BUY:
            if fill.symbol in entries:
                raise ValueError(f"{fill.symbol}: overlapping BUY fills")
            entries[fill.symbol] = fill
        else:
            entry = entries.pop(fill.symbol, None)
            if entry is None or entry.quantity != fill.quantity:
                raise ValueError(f"{fill.symbol}: SELL does not close its BUY")
            profit = fill.quantity * (fill.fill_price - entry.fill_price) - entry.commission - fill.commission
            profits.append(profit)
            realized[fill.symbol] = realized.get(fill.symbol, 0.0) + profit
            durations.append((fill.timestamp - entry.timestamp).total_seconds() / 86400)
    if set(entries) != set(result.final_positions):
        raise ValueError("Open fills do not match final positions")
    if result.final_stops and set(result.final_stops) != set(entries):
        raise ValueError("Protective stops do not match final positions")
    for payment in result.dividend_payments:
        claim = claims.pop(payment["event_id"], None)
        if claim is None or claim["amount"] != payment["amount"] or pd.Timestamp(payment["timestamp"]).date().isoformat() != claim["pay_session"]:
            raise ValueError("Dividend payment has no matching unpaid entitlement/date")
    if claims != {item["event_id"]: item for item in result.final_dividend_receivables}:
        raise ValueError("Outstanding dividend receivables do not reconcile")
    if abs(sum(item["amount"] for item in claims.values()) - points[-1].dividend_receivable) > 1e-6:
        raise ValueError("Dividend receivables differ from final equity mark")
    open_positions = {
        symbol: {
            "quantity": entry.quantity,
            "last_close": result.final_closes[symbol],
            "stop_price": result.final_stops.get(symbol),
            "marked_unrealized_pnl": entry.quantity * (result.final_closes[symbol] - entry.fill_price) - entry.commission,
        }
        for symbol, entry in sorted(entries.items())
    }
    dividend_income = sum(item["amount"] for item in result.dividend_entitlements)
    accounted_profit = dividend_income + sum(realized.values()) + sum(
        position["marked_unrealized_pnl"] for position in open_positions.values()
    )
    if abs(accounted_profit - (points[-1].equity - result.costs.initial_cash)) > 1e-6:
        raise ValueError("Realized plus marked P&L does not reconcile to final equity")
    if result.universe_metadata is not None:
        reconstructed_cash = result.costs.initial_cash + sum(
            (-1 if fill.side == SignalAction.BUY else 1) * fill.quantity * fill.fill_price - fill.commission
            for fill in result.fills
        ) + sum(item["total_cash"] for item in result.cash_settlements) + sum(item["amount"] for item in result.dividend_payments)
        if abs(reconstructed_cash - points[-1].cash) > 1e-6:
            raise ValueError("Cash, trade fills and corporate-action payments do not reconcile")
    max_exposure = max(point.gross_exposure for point in points)
    stop_fills = [
        fill for fill in result.fills
        if fill.side == SignalAction.SELL and fill.signal_reason.startswith("PROTECTIVE_STOP_")
    ]
    metrics = {
        "initial_cash": result.costs.initial_cash,
        "final_equity": points[-1].equity,
        "total_return": points[-1].equity / result.costs.initial_cash - 1,
        "annual_returns": annual_returns,
        "max_drawdown": min(point.drawdown for point in points),
        "max_observed_gross_exposure": max_exposure,
        "max_observed_positions": max(point.position_count for point in points),
        "completed_trades": len(profits),
        "protective_stop_exits": len(stop_fills),
        "gap_open_stop_exits": sum(
            fill.signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN") for fill in stop_fills
        ),
        "winning_trades": sum(profit > 0 for profit in profits),
        "win_rate": sum(profit > 0 for profit in profits) / len(profits) if profits else None,
        "profit_factor": sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0))
        if any(p < 0 for p in profits) else None,
        "average_holding_days": sum(durations) / len(durations) if durations else None,
        "realized_pnl_by_symbol": dict(sorted(realized.items())),
        "open_positions": open_positions,
        "fill_count": len(result.fills),
        "entry_halted_at": result.halted_at,
        "event_count": len(result.events),
    }
    if result.universe_metadata is not None:
        metrics.update(
            cash_settlement_count=len(result.cash_settlements),
            cash_settlement_realized_pnl=sum(settlement_profits),
            resolved_positions_including_settlements=len(profits) + len(settlement_profits),
            trade_metrics_exclude_cash_settlements=True,
            split_event_count=len(result.share_actions), dividend_income_earned=dividend_income,
            dividend_cash_received=sum(item["amount"] for item in result.dividend_payments),
            dividend_receivable=sum(item["amount"] for item in result.final_dividend_receivables),
        )
    return metrics
