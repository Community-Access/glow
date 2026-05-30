"""CLI-only entry point: never launches the GUI."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from quill_glow_core import configure_default_services as _configure_shared_core_default

        _configure_shared_core_default()
    except Exception:
        pass

    from acb_large_print.cli import main as cli_main

    sys.exit(cli_main(force_cli=True))


if __name__ == "__main__":
    main()
