"""PDF report generator via WeasyPrint."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from europulse.reporting.html_generator import generate_html_report

try:
    import weasyprint
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "weasyprint is required for PDF generation. Install it with: pip install weasyprint"
    ) from exc


def generate_pdf_report(
    output_path: str,
    db_path: str | None = None,
    title: str = "EuroPulse Intelligence Report",
) -> str:
    """Generate a PDF report and write it to *output_path*.

    Returns the output path.
    """
    kwargs = {"title": title}
    if db_path is not None:
        kwargs["db_path"] = db_path

    html = generate_html_report(**kwargs)
    pdf = weasyprint.HTML(string=html).write_pdf()
    Path(output_path).write_bytes(pdf)
    return output_path
