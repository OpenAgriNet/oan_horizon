Score text-eval response usefulness (OAN-style).

Focus on:
- completeness
- actionability
- context_fit
- clarity
- conversation_closure (where relevant)

Rubric (1-5):
- 5: Complete, practical, clear, context-aware
- 4: Strong response with small gaps
- 3: Useful but partly generic/incomplete
- 2: Low practical utility
- 1: Fails user need

Return:
- `SCORE: <1-5>`
- `REASON: <1-2 lines>`
