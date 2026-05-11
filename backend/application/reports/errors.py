"""Report generation errors."""

from __future__ import annotations


class ReportGenerationError(RuntimeError):
    """Raised when report generation is not allowed by product policy."""
