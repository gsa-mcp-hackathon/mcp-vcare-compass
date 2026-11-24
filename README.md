# mcp-vcare-compass: VCARE CC Compass MCP Server

A read-only prototype MCP server that helps reviewers check VA Community Care consults for missed steps and high-risk cases. Built for the GSA Model Context Protocol (MCP) Server and AI Agent Government Hackathon on Databricks Apps, from the GSA server template (FastMCP + uv).

**Data statement:** All data used in this prototype are synthetic. The 600 test cases were created from scratch for testing. No real patient, Veteran, provider, or facility data, and no data from any VA clinical system, were used or derived.

No tool makes a clinical decision or certifies compliance. Every result includes a notice saying so.

## The three tools

| Tool | What it does |
| --- | --- |
| `get_consult_pathway_checklist` | Gives the standard review questions and policy references for each consult step (receive, triage, eligibility, authorize, schedule, follow-up, close). |
| `flag_high_risk_case` | Checks one synthetic consult against five rules (RFS timing, urgent or complex coordination, reported death, no action past the time limit, Best Medical Interest) and returns flags, severity, and next steps. |
| `ask_vcare_case_data` | Answers plain-English questions about the 600 synthetic consults through a Databricks Genie agent. Returns the answer, the SQL it used, and up to 20 rows. |

All three tools are read-only.

## How to run it

1. Install [uv](https://docs.astral.sh/uv/).
2. `cp .env.example .env`, then `uv sync`.
3. `uv run python main.py` starts the server for a local MCP client.
4. `uv run pytest tests/ -v` runs the 57 automated tests.

`ask_vcare_case_data` also needs a Genie space ID and Databricks sign-in. The other two tools work offline. Deployment guides are in [deploy/](deploy/).

## Evaluation

We tested the server with 10 gold-standard questions, scored automatically by an AI judge (LLM-as-judge).

* Right tool chosen: 10 out of 10 in every run.
* Answers judged correct: 10 out of 10 on Oct 30 and Nov 3; 5 to 6 out of 10 after the Nov 9 to 10 data update. *(to be updated after the next run)*

Details are in [eval/](eval/).

## License

MIT. See [LICENSE](LICENSE).
