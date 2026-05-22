"""cost — show cost of resources matching a tag, over the last N days.

WHAT YOU MUST BUILD
-------------------
A function that:
  1. Queries Cost Explorer (`ce.get_cost_and_usage`) for the last N days
  2. Filters by a tag (e.g. Application=HealthBot)
  3. Groups by SERVICE dimension
  4. Sums per-service costs across the date range
  5. Prints services sorted descending by cost, plus a TOTAL row

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)             # "Application=HealthBot" -> tuple

AWS APIS YOU'LL NEED
--------------------
ce = boto3.client("ce")
ce.get_cost_and_usage(
    TimePeriod={"Start": "YYYY-MM-DD", "End": "YYYY-MM-DD"},
    Granularity="DAILY",
    Metrics=["UnblendedCost"],
    Filter={"Tags": {"Key": "<tag_key>", "Values": ["<tag_value>"]}},
    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
)

The response has `ResultsByTime` (one entry per day), each with `Groups` —
each group has `Keys=[service_name]` and `Metrics={"UnblendedCost":{"Amount":"1.23"}}`.

EXPECTED OUTPUT FORMAT
----------------------
        Cost for Application=HealthBot over last 7 days (2026-05-14 -> 2026-05-21):
    ------------------------------------------------------------
      Amazon Elastic Compute Cloud - Compute        $    8.42
      Amazon Relational Database Service             $    5.18
      ...
    ------------------------------------------------------------
      TOTAL                                          $   13.80

GOTCHAS
-------
- Cost data lags 8–24h. If --days 1 returns nothing, try --days 7.
- Tag filter requires that you have ACTIVATED cost allocation tags in Billing.
- Amount field is a STRING in the response — cast to float before summing.

VERIFY MANUALLY (no test file for this command)
-----------------------------------------------
    ./costctl.py cost --tag Application=<your-app> --days 7

The first time you run this, double-check against the AWS Console
(Cost Management → Cost Explorer → filter by same tag + same range).
Output should match within a few cents.
"""
import boto3
from collections import defaultdict
from datetime import date, timedelta
from botocore.exceptions import ClientError
import sys

from commands._common import parse_kv


def run(args):
    """Entry point.

    Args set by argparse:
        args.tag   — "key=value" string (REQUIRED)
        args.days  — int, default 7
    """
    # Keep output ASCII-friendly for Windows PowerShell redirection.
    # (Using Unicode arrows often produces mojibake when redirected to a file.)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    tag_key, tag_val = parse_kv(args.tag)
    days = int(args.days or 7)
    if days <= 0:
        days = 7

    end = date.today()
    start = end - timedelta(days=days)

    # Cost Explorer is a global-ish endpoint; boto3 commonly requires us-east-1.
    ce = boto3.client("ce", region_name="us-east-1")

    totals = defaultdict(float)
    try:
        resp = ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            Filter={"Tags": {"Key": tag_key, "Values": [tag_val]}},
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
    except ClientError as e:
        err = e.response.get("Error", {})
        code = err.get("Code", "Unknown")
        msg = err.get("Message", str(e))
        print(f"AWS error [{code}]: {msg}")
        return

    for day in resp.get("ResultsByTime", []):
        for group in day.get("Groups", []):
            service = (group.get("Keys") or ["Unknown"])[0]
            amount_s = (
                group.get("Metrics", {})
                .get("UnblendedCost", {})
                .get("Amount", "0")
            )
            try:
                amount = float(amount_s)
            except ValueError:
                amount = 0.0
            totals[service] += amount

    end_inclusive = end - timedelta(days=1)
    print(
        f"Cost for {tag_key}={tag_val} over last {days} days ({start.isoformat()} -> {end_inclusive.isoformat()}):"
    )
    print("-" * 60)

    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    total_cost = 0.0
    for service, amount in items:
      total_cost += amount
      print(f"  {service:<45} $ {amount:8.2f}")

    print("-" * 60)
    print(f"  {'TOTAL':<45} $ {total_cost:8.2f}")
