# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A Larkspur disruption chat agent with nine supplied tools and three local tools: fare_rules, next_available_day, and reopen_stats, connected to handbook and fixture data.
Does: Looks up a disrupted booking and flight, checks policy, explains handbook rules, finds alternatives or the next available day, and holds a seat while the customer decides.
Number: Tools offered per API call rose from 9 to 12 after adding three tools, as confirmed by run.py --show-tools.
Safety check: It does not finalize a rebooking without the customer's UI-issued confirmation token; confirm_rebooking requires it, and the K7PQ2M trace made no confirmation call.
Next: Test whether reopen_stats improves escalation guidance across more disruption cases without changing policy entitlements.
Still broken: The fixtures use May 2025 flights; in our November 2026 run, the agent treated the rebooking window as likely expired and asked if that old trip was intended.
Lever: <cost | speed | intelligence>

## Priya asked

Costs:
Wrong:
Runs it:
Left out:
