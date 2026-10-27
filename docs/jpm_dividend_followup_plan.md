# JPMorgan: one final bounded evidence follow-up

**Prepared 2026-10-27; not executed.** This is a free public-document plan,
not a backtest, order command or trading configuration. Your instruction to
leave JPMorgan behind if this does not work is recorded in the fallback below.

## What we are trying to establish

JPM is JPMorgan Chase's stock ticker. We need the company's own dividend
announcements to check how much shareholders were entitled to receive and
when payment was due. These are historical accounting facts, not charges to
you, investments or real dividend receipts.

The saved provider data contains 32 dividends with ex-dates in 2016–2023.
Two already have collected primary declarations. The remaining
[30 target rows](research_data/jpm_dividend_followup_targets.csv) include
**16 without a provider payable date**. The other 14 have provider payment
dates but still lack the newly collected issuer confirmation. Provider dates
and amounts in that CSV remain provider claims, not approved issuer facts.

The [machine-readable plan](jpm_dividend_followup_plan.json) pins these inputs
and earlier evidence with SHA-256 hashes. It is a non-executable specification;
it cannot be passed directly to the downloader.

## Preserve the earlier stop

The earlier collection stopped at **HTTP 403** on
`jpmorganchaseco.gcs-web.com/ir/shareholder-information/dividend-history`.
Its [review](pilot_public_source_review.json), source files, request logs and
stop report remain unchanged. That batch made five public discovery calls
and 18 direct GET attempts; its unused budget is not reopened.

This follow-up will use JPMorgan's main issuer site only. It will not retry
the blocked host, use proxies/mirrors, log in or bypass access controls.
An HTTP 403 does not establish that a paid subscription is required.

## One attempt, with fixed limits

| Limit | Maximum |
| --- | --- |
| Public discovery tool calls | 4 |
| Direct public-document GET attempts, including failures and reviewed redirect hops | 8 |
| Elapsed collection time from the first online action, across all queues and reviews | 10 minutes |
| Individual GET timeout | 30 seconds |
| Saved response size | 16 MiB per document |
| Minimum spacing between GET attempts | 1.1 seconds |
| Purchases, broker/account requests, orders, new price requests | **0** |

Stop when any limit is reached; do not begin another request after the time
limit. An in-flight request can take up to its timeout to return. There are no
automatic retries, budget resets or further follow-up batches. All counters
are cumulative, including unsuccessful attempts. Discovery-tool activity and
direct GET attempts have separate counters; discovery tools may perform their
own internal retrievals, so this is not a claim of exactly 12 network packets.

Stop earlier on HTTP 401/402/403/407/429, payment/login/credential demands,
transport failure, or ambiguous/conflicting evidence requiring investigation.
Keep partial successes and the reason for stopping. No paid fallback, trial,
installation or account change is part of this work.

## Collection sequence

1. Read the saved 2016/2021 declarations and issuer indexes offline. Those
   successful earlier downloads do not establish current accessibility.
2. Use up to four public discovery calls restricted to the exact hosts
   `www.jpmorganchase.com` and `jpmorganchase.com`. Start with the issuer news
   archive and links in the cached 2016 news index. Record exact URL provenance.
3. Prioritize issuer tables or documents covering several dividends. Thirty
   separate releases would exceed this budget; complete coverage is not
   promised. Review each exact HTTPS URL before a GET. Do not invent yearly
   archive paths or announcement URLs.
4. Disable automatic redirects. Follow a redirect only after reviewing its
   exact allowed host and target, counting the next GET against the same cap.
5. Save responses, URL queues, request/elapsed-time logs and source hashes in
   a **new** `data/reports/jpm_dividend_followup_v1` directory. Never overwrite
   an existing output directory, the preceding collection or reconciliations.
6. Reconcile exact amounts, share class/basis and stated declaration, record
   and payable dates against each provider event ID. Retain conflicts and
   missing fields. Report complete, partial/stopped and parked outcomes.

Target ex-dates are January 1, 2016 through December 31, 2023. December 2015
declaration metadata is allowed because it may establish a January 2016
dividend. Later contractual payable metadata is allowed where relevant.
**No 2024–2025 candle prices will be read.** Declaration metadata and price
holdouts are separate data scopes.

## What a source can and cannot prove

Each matched target needs the original event ID, exact source URL, saved-byte
hash, retrieval time, common-share amount/basis and stated dates. A document
that omits a term leaves that term unresolved. Do not infer payment dates from
quarterly patterns or processing dates. A current archive is retrospective;
its retrieval does not prove when a historical strategy knew the information.

Even resolving all 30 declaration targets does not certify independent
ex-dates, eligibility to receive dividends, full-period identity/action
completeness, broker-credit timing or strategy performance. Issuer payable
dates are contractual terms, not proof of spendable broker cash. Proposed
knowledge/payment assumptions remain unapproved; scoring stays disabled.

## If JPMorgan remains incomplete: move forward

**Your fallback is accepted:** after this one bounded effort, any unresolved
JPMorgan evidence is marked **parked outside active engineering-pilot work**.
There will be no indefinite JPMorgan search or purchase proposal. A partial
success does not automatically start another batch.

I will continue qualification work on **Apple (AAPL) and CBRE**, with **SPY
as market context only**. They are candidates for engineering checks, not
automatically approved histories. Their remaining work includes independent
Apple ex-date/entitlement and identity checks; CBRE classification/noncash
action completeness; and SPY timing, blank gain cells and precision policy.

Parking JPMorgan does not erase it from the 506-row historical register,
change the registered nine-stock strategy control, alter old results or
replace it with a stock selected for better returns. Any narrower performance
study needs a separately stated, frozen scope and review of data exclusions.
This two-stock engineering sample cannot establish whole-market performance
or meet the existing minimum of five instruments and 30 completed trades.
Those acceptance requirements remain unchanged.

## Your part and what happens next

**You have nothing to configure now:** no card, purchase, credentials or
personal risk-limit changes. This turn only prepares the plan; it makes no
network requests, runs no tests and calculates no strategy returns.

**My next work:** execute this one capped attempt, report what was found and
apply the parking fallback if any JPMorgan targets remain unresolved. Then
continue the other pilot histories. Before any new performance run uses
modeled knowledge/payment timing, you still review section 3 of the
[pilot proposal](free_data_pilot_proposal.md). Paper activation is a later,
separate decision; this plan does not move the bot into paper trading.
