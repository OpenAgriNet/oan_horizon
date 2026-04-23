Score text-eval process fidelity (OAN-style).

Focus on:
- agristack_workflow appropriateness
- term_identification where relevant
- tool_sequencing correctness
- search_quality where relevant
- output_hygiene (no tool-name/internal leakage)

Rubric (1-5):
- 5: Workflow and ordering are correct; clean output
- 4: Mostly correct with minor process gaps
- 3: Mixed process quality; notable misses
- 2: Major workflow/order issues
- 1: Broken process behavior

Return:
- `SCORE: <1-5>`
- `REASON: <1-2 lines>`
