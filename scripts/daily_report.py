"""Standalone daily report generator with DB logging."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from europulse.config import DATA_DIR, DB_PATH
from europulse.ingestion.db import create_schema, get_conn, log_report_run
from europulse.reporting.html_generator import generate_html_report
from europulse.reporting.pdf_generator import generate_pdf_report

REPORTS_DIR = DATA_DIR / "reports"


def main() -> int:
    parser = argparse.ArgumentParser(description="EuroPulse Daily Report")
    parser.add_argument(
        "--format",
        choices=["html", "pdf"],
        default="html",
        help="Report output format",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPORTS_DIR),
        help="Directory to write reports to",
    )
    parser.add_argument(
        "--title",
        default="EuroPulse Daily Intelligence Report",
        help="Report title",
    )
    args = parser.parse_args()

    load_dotenv()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"report_{ts}.{args.format}"

    conn = get_conn()
    create_schema(conn)

    start_ms = int(time.time() * 1000)
    status = "success"
    try:
        if args.format == "html":
            generate_html_report(
                output_path=str(output_path),
                db_path=DB_PATH,
                title=f"{args.title} — {ts}",
            )
        else:
            generate_pdf_report(
                output_path=str(output_path),
                db_path=DB_PATH,
                title=f"{args.title} — {ts}",
            )
        print(f"Report written to {output_path}")
    except Exception as exc:
        status = "failed"
        print(f"Report generation failed: {exc}", file=sys.stderr)
    finally:
        duration = int(time.time() * 1000) - start_ms
        log_report_run(
            conn,
            format=args.format,
            output_path=str(output_path),
            status=status,
            duration_ms=duration,
        )
        conn.close()

    return 0 if status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
