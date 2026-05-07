"""Точка входа клиента."""

from __future__ import annotations

import argparse
import os
import sys

import flet as ft

from .app import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Hotel Management Flet client")
    parser.add_argument("--web", action="store_true", help="Запустить в браузере (web)")
    parser.add_argument("--port", type=int, default=8550)
    parser.add_argument("--api-url", help="Базовый URL backend (override $HOTEL_API_URL)")
    args, _ = parser.parse_known_args()

    if args.api_url:
        os.environ["HOTEL_API_URL"] = args.api_url

    view = ft.AppView.WEB_BROWSER if args.web else ft.AppView.FLET_APP
    try:
        ft.app(target=build_app, view=view, port=args.port if args.web else 0)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
