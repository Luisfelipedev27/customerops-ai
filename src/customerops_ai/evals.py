"""Small behavioral/retrieval regression suite. No LLM-as-judge score is fabricated."""

import json

from sqlalchemy import select

from .agent import run_agent
from .config import ROOT, get_settings
from .db import session_scope
from .models import Action, CRMTask, User
from .security import Principal
from .seed import DEMO_TENANT


def main():
    with session_scope(DEMO_TENANT) as db:
        user = db.scalar(select(User).where(User.tenant_id == DEMO_TENANT, User.role == "admin"))
        if not user:
            raise SystemExit("Run the seed command before evaluations.")
        principal = Principal(user.id, user.tenant_id, user.role, user.email)
    cases = json.loads((ROOT / "evals/cases.json").read_text())
    results = []
    for case in cases:
        output = run_agent(principal, case["question"])
        tools = {c["name"] for c in output["tool_calls"]}
        checks = {
            "tools": set(case["tools"]).issubset(tools),
            "answer": all(term.lower() in output["answer"].lower() for term in case["contains"]),
            "sources": bool(output["sources"]) if case["sources"] else True,
        }
        if "propose_follow_up" in case["tools"]:
            with session_scope(DEMO_TENANT) as db:
                actions = list(db.scalars(select(Action).where(Action.run_id == output["id"])))
                checks["approval_gate"] = bool(actions) and all(
                    a.status == "pending" for a in actions
                )
                checks["no_execution"] = not any(
                    db.scalar(select(CRMTask).where(CRMTask.action_id == a.id)) for a in actions
                )
        results.append(
            {
                "case": case["name"],
                "passed": all(checks.values()),
                "checks": checks,
                "latency_ms": output["latency_ms"],
                "mode": output["mode"],
            }
        )
    report = {
        "suite": "behavioral-regression",
        "mode": get_settings().ai_mode,
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "cases": results,
        "limitations": "Small synthetic dataset. Demo results do not measure real LLM quality.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
