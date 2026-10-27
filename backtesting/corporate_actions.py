"""Causal split-unit feature views; raw bars remain execution observations."""

import pandas as pd

from app.ai.features import FeatureConfig, build_features
from backtesting.universe import HistoricalUniverse, UniverseDataError


def split_quantity(quantity: int, new_shares: int, old_shares: int) -> int:
    """Convert an owned position exactly; never round away a fractional claim."""
    shares, remainder = divmod(quantity * new_shares, old_shares)
    if remainder:
        raise UniverseDataError("Split creates fractional owned shares; verified cash-in-lieu handling is required")
    return shares


def feature_views(frame, instrument_id, universe: HistoricalUniverse, periods_per_year, *, reset_indices=()):
    """One view per contiguous history and split regime, adjusted as of that open.

    Future splits never change past decision views. On an effective session,
    rebase only earlier OHLC/volume into the new share units and recompute the
    completed-history features. Dividends remain raw-price signal movements;
    entitlement accounting is separate and cannot double-adjust signal prices.
    Explicit ownership-event resets start a fresh history at that session;
    pre-event observations never supply post-event indicators or warmup.
    """
    active = frame.loc[frame["volume"] > 0]
    lookup, starts = {}, {}
    indices = pd.Series(active.index, index=active.index)
    groups = (indices.diff().ne(1) | indices.isin(reset_indices)).cumsum()
    index_by_date = {t.date().isoformat(): i for i, t in enumerate(universe.dates)}
    splits = sorted((a for a in universe.splits if a.instrument_id == instrument_id), key=lambda a: a.effective_session)
    for _, block in active.groupby(groups):
        first, last = int(block.index[0]), int(block.index[-1])
        boundaries = sorted({first, *(index_by_date[a.effective_session] for a in splits if first < index_by_date[a.effective_session] <= last)})
        for j, begin in enumerate(boundaries):
            stop = boundaries[j + 1] if j + 1 < len(boundaries) else last + 1
            adjusted = block.loc[:stop - 1].copy()
            columns = ["open", "high", "low", "close", "volume"]
            adjusted[columns] = adjusted[columns].astype(float)
            for action in splits:
                effective = index_by_date[action.effective_session]
                if effective > begin:
                    break
                prior = adjusted.index < effective
                adjusted.loc[prior, ["open", "high", "low", "close"]] = adjusted.loc[prior, ["open", "high", "low", "close"]].astype(float) / action.ratio
                adjusted.loc[prior, "volume"] = adjusted.loc[prior, "volume"].astype(float) * action.ratio
            built = build_features(adjusted, config=FeatureConfig(periods_per_year=periods_per_year))
            built.index = adjusted.index
            for index in block.index[(block.index >= begin) & (block.index < stop)]:
                lookup[int(index)] = built
                starts[int(index)] = first
    return lookup, starts
