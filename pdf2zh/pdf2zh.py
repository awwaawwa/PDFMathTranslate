#!/usr/bin/env python3
"""A command line tool for extracting text and images from PDF and
output it to plain text, html, xml or tags.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from pdf2zh.config import ConfigManager
from pdf2zh.config.model import SettingsModel
from pdf2zh.high_level import do_translate_file

logger = logging.getLogger(__name__)


def find_all_files_in_directory(directory_path):
    """
    Recursively search all PDF files in the given directory and return their paths as a list.

    :param directory_path: str, the path to the directory to search
    :return: list of PDF file paths
    """
    directory_path = Path(directory_path)
    # Check if the provided path is a directory
    if not directory_path.is_dir():
        raise ValueError(f"The provided path '{directory_path}' is not a directory.")

    file_paths = []

    # Walk through the directory recursively
    for root, _, files in os.walk(directory_path):
        for file in files:
            # Check if the file is a PDF
            if file.lower().endswith(".pdf"):
                # Append the full file path to the list
                file_paths.append(Path(root) / file)

    return file_paths


async def main() -> int:
    from rich.logging import RichHandler

    logging.basicConfig(level=logging.INFO, handlers=[RichHandler()])

    settings = ConfigManager().initialize_config()
    if settings.basic.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # disable httpx, openai, httpcore, http11 logs
    logging.getLogger("httpx").setLevel("CRITICAL")
    logging.getLogger("httpx").propagate = False
    logging.getLogger("openai").setLevel("CRITICAL")
    logging.getLogger("openai").propagate = False
    logging.getLogger("httpcore").setLevel("CRITICAL")
    logging.getLogger("httpcore").propagate = False
    logging.getLogger("http11").setLevel("CRITICAL")
    logging.getLogger("http11").propagate = False

    print(settings)

    await do_translate(settings)
    return 0


async def do_translate(settings: SettingsModel) -> int:
    assert len(settings.basic.input_files) >= 1, "At least one input file is required"

    for file in list(settings.basic.input_files):
        await do_translate_file(settings, file)

    return 0


def cli():
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli()
