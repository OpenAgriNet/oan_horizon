# Memory Design Proposal

We are splitting the memory into 2 parts - a small "FamerProfile" which has some key estabilshed details about the user, and Episodic memory, which are memories we've decided to keep over various sessions of any important events. 

There is already an implementaiton based on mem0 for this in Mh-dev.

## FarmerProfile

This is already implemeted currently , with 4 potential additions based on recent discussions:

1. **Post-session updates:** Adding new information to the profile moves away from the agent doing it as a part of the agentic setup during human conversation to a dedicated post-*session* call. We can determine when/how often to have this call
2. We define a small schema that contains the key facts of a farmer profile we need to store and force the model to only update for these keys so that profile remains small and constrained
3. **Timestamps:** Every field carries a timestamp so the LLM can judge whether information might be stale.
4. **State tracking:** Values track state over time, allowing us to see how attributes change rather than silently overwriting them.

We can pull this into every session, but we must be strict about writes; only updating it when farmer facts are confirmed with high certainty.

---

## Episodic Memory

### Option 1 — Without Reconciliation

This retains the session-based memory concept, writing session summaries into a vector database ( if a model judges it to be important to save) to be retrieved later.

One possible  change to the current implementation is again shifting execution timing, just like for Farmer Profile.  Writes move to the end of the session (processed post-session alongside `FarmerProfile`) 

---

### Option 2 — With Reconciliation

After a conversation ends, an LLM reviews the session, extracts key facts, and reconciles them with the farmer's existing long-term memory store before saving. New details are either merged directly into existing topic chunks or created as distinct new chunks. 

To elaborate:

1. Topic and fact chunking: Information belongs to either a recognized domain topic (e.g., sowing schedules, pest management)- based again on a (bigger) schema or it could be something the LLM judges as an independently significant fact (e.g. facing drying of his well every June ); just a backup incase schema doesnt cover something important to the farmer.

2. Searchable index headers: Chunks are assigned clear, specific headers (e.g., paddy: pest history, "Distrust of chemical pesticides") to make retrieval and future merging deterministic.

3. In-place updates: The LLM makes a seach on existing chunk and  chunks are updated in place rather than appended, preventing duplicate or disconnected entries for the same topic.

4. Temporal reasoning: Each piece of information is timestamped, enabling the LLM to judge current validity (e.g., treating notes from six months ago differently from recent ones).

5. Flexible indexing: A dedicated searchable index column is an optional alternative to improve lookups; the system can also rely purely on vector search over the generated chunks.

---

## Recall of Memory

`FarmerProfile` can be injected unconditionally as context on every turn.

For **Episodic Memory**, there are two strategies for pulling memory into a conversation:

* **Model-driven tool calls:** The model explicitly decides when to invoke a recall tool based on the conversation context.
* **Unconditional retrieval:** A vector search runs automatically on every turn, injecting any memory above a similarity threshold, the model decides whether to use that info

---

## Next Steps: Empirical Experiments

To determine the best setup, we can run experiments testing combinations of these approaches:

1. **Episodic memory with reconciliation vs. without reconciliation.**
2. **Retrieval on every turn vs. model-driven retrieval.**