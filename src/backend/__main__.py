"""
Backend main entry point.
"""

import sys


def main() -> int:
    """Main entry point for backend CLI."""
    from backend.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())