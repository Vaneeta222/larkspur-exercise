# Client review: Larkspur disruption-care agent

**To:** Room 26  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-17 11:07

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. PITCH.md says 'three local tools' and 12 offered per call, but agent.py declares one EXTRA_TOOLS schema and one LOCAL_TOOLS executor.**

In the diff, fare_rules and next_available_day sit in comment lines inside EXTRA_TOOLS and LOCAL_TOOLS. Only reopen_stats is live. The static scan counts EXTRA_TOOLS declared: 1 and 10 tool schemas against the 9 the pack ships, and PITCH.md's Number line says 'rose from 9 to 12'. tool_list() returns build_tools() + EXTRA_TOOLS + mcp_client.tools(), so the 12 depends on what the MCP client returns, which nothing here shows.

Run python3 run.py --show-tools and paste the full tool list with its count.

**2. The committed trace in readout-trace.json shows 5 tool calls, and fare_rules was called with no schema in EXTRA_TOOLS.**

The tools-called list is lookup_booking, get_flight_status, reopen_stats, check_policy, fare_rules. In agent.py the fare_rules schema is commented out and LOCAL_TOOLS maps only reopen_stats. fare_rules(question) reads data/americas/fare_rules_excerpt.md and returns the whole file whatever the question. The trace has no search_alternatives, hold_seat or next_available_day call, though PITCH.md's Does line says the agent finds alternatives and holds a seat.

Run python3 run.py K7PQ2M --trace and paste the tool-call lines and the final answer.

**3. reopen_stats in agent.py has no recorded count behind it, and its description tells the model to lean toward goodwill on a high rate.**

The function counts rows in transcripts_sample.jsonl matching an origin and cause_code and returns reopened, total and reopen_rate. A sample file can leave total at 3 or 4, and the function returns 0.0 when total is 0, which looks the same as a real zero rate. The description says a high rate should inform 'more goodwill, lower threshold to escalate', and PITCH.md's Next line says you have not tested that it improves escalation guidance. A larger model reading the same sample sees the same denominator.

Paste the reopen_stats return value from the readout-trace.json run, with its total and reopened fields.

**4. The only before-and-after in PITCH.md is a tool count of 9 to 12, and evals/cases.json does not exist in this repository.**

No file here measures an outcome change from any edit. The Number line reports how many tools are offered, which says nothing about answer quality, cost or speed. The committed run shows 23489 tokens in, 855 out and prompt caching at 0 read, 0 written, with no baseline run to compare against. Whatever model Priya's vendor proposes, the repository holds no case it could be scored on.

Run python3 bench.py --label before --stage 1 --runs 3 and python3 bench.py --label after --stage 1 --runs 3, then paste the python3 bench.py --compare before after output.

**5. The stale-date failure in PITCH.md's Still broken line comes from the date format and the fixtures, so a bigger model would meet the same data.**

The diff changes the get_flight_status date description from MM/DD/YYYY to YYYY-MM-DD. PITCH.md says the agent treated the May 2025 booking as an expired rebooking window in a November 2026 run. The fixtures live in data/americas and agent.py never fixes or supplies a date to the model beyond runtime_preamble(). A better model would reason correctly about a date the data already got wrong.

Paste the runtime_preamble() output from the K7PQ2M trace, and say which date the agent was told is today.

## Your four answers

The four lines under `## Priya asked` in your PITCH.md are still empty. They
are one line each and they are not a coding job: cost, what happens when it is
wrong, who runs it in June, and what you left out. Whoever on your side is not
editing agent.py is the right person to write them, and they are the four
things I will ask about first.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (345 lines)`
- `PITCH.md`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`
- given files that differ from the shipped pack: `verify.py`, `eval_harness.py`, `bench.py`, `readout.py`, `setup.py`, `pod_sync.py`, `run.py`, `review.py`, `support/__init__.py`, `support/client.py`, `support/data.py`, `support/models.py`, `support/tools.py`, `support/trace.py`, `support/offline.py`, `support/mock_backend.py`, `support/mcp_client.py`, `support/mcp_server.py`, `support/mcp_selftest.py`, `support/access.py`, `support/keyscan.py`, `support/review.py`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
