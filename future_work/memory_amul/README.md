# Amul conversational memory

Current design, reviewed with Gautam on 9 September 2026. Implementation is local
in `amul-memory` and the `memory_v0` branch of `amul-oan-api`. These documents do
not claim that the reviewed changes have been deployed or evaluated on live users.

Start with [Memory in brief](memory-in-brief.md) for the three levels, an example,
and how the background agent works. [The full design](memory-overview.md) gives more detail. The
[decision review](design-review-2026-09-09.md) distinguishes agreed choices,
repairs, and outstanding work. [API and integration](api-and-integration.md)
explains the code and contracts; [technical decisions](memory-design-decisions.md)
records the main tradeoffs.

[Log findings](log-findings.md) preserves the original examples and their evidence.
Those examples motivate the system; they do not define a mandatory taxonomy.
[Demo plan](demo-plan.md) and [backtesting plan](backtesting-plan.md) describe the
remaining validation. Earlier versions of these design documents remain in git
history; their statements about unbuilt features and category filters are superseded.

The completed one-farmer observations and limitations are in [the demo review](demo-review-2026-09-09.md).

The [20-farmer backtest review](backtest-review-2026-09-09.md) records the paired
with/without-memory replay and links the scored CSV.

The [retention and follow-up review](followup-review-2026-09-09.md) records the
revised usefulness rule, skipped-conversation audit, 15 real follow-up pairs and
the 10/5/3-turn batch-size experiment. It includes failures as well as improvements.

The [synthetic diagnostic plan](synthetic-test-plan-2026-09-09.md) defines the
balanced fresh-chat test and dev-Qdrant connection status for the supplied test user.
