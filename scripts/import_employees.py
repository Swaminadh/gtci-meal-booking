"""Import the existing employee Excel file into the Supabase employees table.

Set SUPABASE_URL and SUPABASE_SECRET_KEY in the shell before running.
The secret key is deliberately read only here and must never be copied to web/.
"""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
EMPLOYEE_FILE = PROJECT_DIR / "database" / "employee_db.xlsx"


def request_json(url, method, headers, payload=None):
    request = Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        method=method,
        headers=headers,
    )
    with urlopen(request) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else None


def main():
    project_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ.get("SUPABASE_SECRET_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    users = pd.read_excel(EMPLOYEE_FILE)
    users.columns = [str(column).strip().lower() for column in users.columns]
    required = {"email", "userid", "name"}
    if not required.issubset(users.columns):
        raise ValueError(f"Excel must contain {required}; received {set(users.columns)}")

    records = []
    for user in users.to_dict("records"):
        email = str(user["email"]).strip().lower()
        if not email or email == "nan":
            continue
        records.append({
            "email": email,
            "full_name": str(user["name"]).strip(),
            "role": "admin" if str(user["userid"]).strip().lower() == "admin" else "user",
            "active": True,
        })

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    try:
        request_json(
            f"{project_url}/rest/v1/employees?on_conflict=email",
            "POST",
            {**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
            records,
        )
        existing = request_json(
            f"{project_url}/rest/v1/employees?select=email",
            "GET",
            headers,
        ) or []
        active_emails = {record["email"] for record in records}
        inactive_emails = [row["email"] for row in existing if row["email"] not in active_emails]
        for email in inactive_emails:
            request_json(
                f"{project_url}/rest/v1/employees?email=eq.{quote(email, safe='')}",
                "PATCH",
                {**headers, "Prefer": "return=minimal"},
                {"active": False},
            )
        print(f"Synced {len(records)} employees; deactivated {len(inactive_emails)} removed employees.")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Supabase: {error.reason}") from error


if __name__ == "__main__":
    main()
