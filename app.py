"""Compatibility entry point for Contract Builder.

The earlier contract-oriented interface is preserved in advanced_app.py, but
the normal application entry point now exposes only the focused workflow.
"""
from simple_app import main


if __name__ == "__main__":
    main()
