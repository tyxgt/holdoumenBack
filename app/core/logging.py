"""Logging setup helpers."""

import logging


def configure_logging(debug: bool) -> None:
    # Switch between verbose local logs and quieter production-style logs.
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
