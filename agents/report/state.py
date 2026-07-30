from typing import TypedDict


class ReportState(TypedDict):

    # Input
    decision: dict

    # Markdown report
    report: str

    # Saved markdown file
    output_file: str

    # Execution status
    status: str

    # Error message
    error: str