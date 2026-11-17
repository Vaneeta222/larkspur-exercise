"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.
DATA_DIR = Path(__file__).resolve().parent / "data" / "americas"

TONE_ADDENDUM = """

Difficult customers:
- Insults or abuse: acknowledge the frustration once, briefly and calmly. Do not repeat the apology, do not match the tone, and do not lecture the customer about it.
- Legal threats (a lawyer, suing, legal action) or threats to harm anyone: do not argue, do not give the usual rundown of entitlements, and do not point them to a refund. Say you are passing the case to a person, call escalate_to_human with the reason, and stop there.
- Requests you cannot handle (groups, refunds, anything out of scope): call escalate_to_human and tell the customer it has been passed on. Never promise what the human team will do: do not say they will rebook, refund, compensate or keep a group together.
- In every case, promise nothing that a tool result has not confirmed.
"""                                      # ✏️ Build 4, step 4.1, intelligence goal
EXTRA_TOOLS: List[Dict[str, Any]] = [   # ✏️ Build 2, step 2.1: schemas for the tools you add
    # {
    #     "name": "fare_rules",
    #     "description": (
    #         "Retrieve the Larkspur handbook text to explain a general fare or disruption "
    #         "rule, such as why an overnight weather disruption does not qualify for a hotel. "
    #         "Use this when the customer asks what the handbook says or why a rule applies. "
    #         "This does not decide what a specific booking is owed; use check_policy for "
    #         "that booking-specific decision."
    #     ),
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "question": {
    #                 "type": "string",
    #                 "description": "The customer's question about the general handbook rule to explain.",
    #             },
    #         },
    #         "required": ["question"],
    #     },
    # },
    # {
    #     "name": "next_available_day",
    #     "description": (
    #         "Answer 'when is the first day I can fly?': returns the earliest date that "
    #         "still has an open seat on a Larkspur flight between two airports, on or after "
    #         "a given date. Use it when the customer asks about the soonest day they can "
    #         "travel, or when search_alternatives found nothing suitable and you need to tell "
    #         "them the first possible day. Take origin, dest and cabin from the segment "
    #         "returned by lookup_booking; never guess them. Returns one date (YYYY-MM-DD), or "
    #         "null if there is no open seat. It only gives the day: to offer specific flights, "
    #         "use search_alternatives."
    #     ),
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "origin": {"type": "string", "description": "Departure airport, 3-letter IATA code from the booking segment (e.g. DEN)."},
    #             "dest": {"type": "string", "description": "Arrival airport, 3-letter IATA code from the booking segment (e.g. AUS)."},
    #             "date": {"type": "string", "description": "First date to consider, YYYY-MM-DD, usually the original flight date from the booking segment."},
    #             "cabin": {"type": "string", "enum": ["Y", "J"], "description": "Cabin from the booking segment: Y for economy, J for business. Defaults to Y."},
    #         },
    #         "required": ["origin", "dest", "date"],
    #     },
    # },
    {
        "name": "reopen_stats",
        "description": (
            "Look up how often disruptions with this cause code at this origin airport "
            "have come back within 72 hours, based on past transcripts. Returns the reopen "
            "rate (reopened / total, e.g. 0.4 for 40%) plus the raw counts behind it. Call "
            "this before check_policy so a high reopen rate can inform the policy decision "
            "(e.g. more goodwill, lower threshold to escalate) -- do not call it after."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport code, e.g. DEN",
                },
                "cause_code": {
                    "type": "string",
                    "enum": ["WX", "ATC", "MX", "CREW", "SEC"],
                },
            },
            "required": ["origin", "cause_code"],
        },
    },
]


def fare_rules(question: str) -> str:
    handbook = Path("data/americas/fare_rules_excerpt.md")
    return handbook.read_text(encoding="utf-8")


def reopen_stats(origin: str, cause_code: str) -> Dict[str, Any]:
    """Count disruptions at an origin/cause that reopened within 72 hours."""
    flight_origin = {}
    with open(DATA_DIR / "flights.csv", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            flight_origin[row["flight_no"]] = row["origin"]

    total = 0
    reopened = 0
    with open(DATA_DIR / "transcripts_sample.jsonl", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            disruption = record["disruption"]
            if (flight_origin.get(disruption["flight_no"]) != origin
                    or disruption["cause_code"] != cause_code):
                continue
            total += 1
            if record.get("reopened_within_72h"):
                reopened += 1

    return {
        "origin": origin,
        "cause_code": cause_code,
        "total": total,
        "reopened": reopened,
        "reopen_rate": round(reopened / total, 2) if total else 0.0,
    }


LOCAL_TOOLS: Dict[str, Any] = {          # ✏️ Build 2, step 2.1: the functions behind them
    # "fare_rules": fare_rules,
    # "next_available_day": next_available_day,
    "reopen_stats": reopen_stats,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    answer = ""
    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        answer = text_of(response)
        turns += 1

    return answer


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS + mcp_client.tools()


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": "Find alternative flights for the disrupted segment on this booking: "
                "other departures on the same route with seats available for the whole "
                "party. Use it when the customer's flight is cancelled or badly delayed "
                "and they need to get there another way, after you have looked up the "
                "booking and checked the flight status. The route, date and cabin are "
                "read from the booking, so send only the PNR. Returns option ids you can "
                "pass to hold_seat.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string", "description": "Confirmation code from the booking, e.g. K7PQ2M"},
                },                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
