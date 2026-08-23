#!/usr/bin/env python3
"""
Steam Game Information Fetcher

Fetches game information and thumbnails from Steam's API and converts
the description to BBCode format.
"""
import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from html2phpbbcode.parser import HTML2PHPBBCode
from unidecode import unidecode

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_appid_from_url(url_or_appid: str) -> str:
    """
    Extract Steam app ID from URL or return the ID if already provided.

    Args:
        url_or_appid: Steam URL or app ID

    Returns:
        The extracted app ID

    Raises:
        ValueError: If the input format is invalid
    """
    if "steam" in url_or_appid.lower():
        match = re.search(r"/app/(\d+)", url_or_appid)
        if match:
            return match.group(1)
        raise ValueError(
            "Invalid Steam URL format. Expected format: "
            "https://store.steampowered.com/app/APPID/..."
        )

    # Validate that it's a numeric app ID
    if not url_or_appid.isdigit():
        raise ValueError(
            f"Invalid app ID: '{url_or_appid}'. Must be numeric or a valid Steam URL."
        )

    return url_or_appid


def fetch_game_data(appid: str, language: str = "english") -> dict:
    """
    Fetch game data from Steam API.

    Args:
        appid: Steam app ID
        language: Language code for the description

    Returns:
        Game data dictionary

    Raises:
        ValueError: If the API request fails or returns invalid data
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "l": language}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch game data: {e}")

    try:
        data = response.json()
    except ValueError as e:
        raise ValueError(f"Invalid JSON response: {e}")

    if appid not in data:
        raise ValueError(f"App ID {appid} not found in response")

    if not data[appid].get("success", False):
        raise ValueError(
            f"Steam API returned unsuccessful response for app ID {appid}. "
            "The game may not exist or may be region-locked."
        )

    if "data" not in data[appid]:
        raise ValueError("No game data in API response")

    return data[appid]["data"]


def convert_description_to_bbcode(
    html_description: str, language: str = "english"
) -> str:
    """
    Convert HTML description to BBCode format.

    Args:
        html_description: HTML-formatted game description
        language: Language code (used to determine if unidecode should be applied)

    Returns:
        BBCode-formatted description
    """
    parser = HTML2PHPBBCode()

    # Apply unidecode only for English to normalize special characters
    if language == "english":
        html_description = unidecode(html_description)

    return parser.feed(html_description)


def download_thumbnail(
    appid: str, language: str = "english", output_path: Path = Path("thumbnail.jpg")
) -> bool:
    """
    Download game thumbnail from Steam.

    Args:
        appid: Steam app ID
        language: Language code for localized thumbnail
        output_path: Path where the thumbnail should be saved

    Returns:
        True if download was successful, False otherwise
    """
    # Try language-specific thumbnail first
    urls = [
        f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/library_600x900_{language}_2x.jpg",
        f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/library_600x900_2x.jpg",
        f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/library_capsule_{language}_2x.jpg",
        f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/library_capsule_2x.jpg",
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
                logger.info(f"Thumbnail saved to: {output_path}")
                return True
        except requests.RequestException as e:
            logger.debug(f"Failed to download from {url}: {e}")
            continue

    logger.warning("Could not download thumbnail from any source")
    return False


def format_output(appid: str, bbcode_description: str) -> str:
    """
    Format the final output with BBCode description and source link.

    Args:
        appid: Steam app ID
        bbcode_description: BBCode-formatted description

    Returns:
        Formatted output string
    """
    steam_url = f"https://store.steampowered.com/app/{appid}/"
    source_line = f"\n[From [url={steam_url}]Steam[/url]]"
    bbcode_description = re.sub(r"\n{2,}", "\n\n", bbcode_description.strip())

    return bbcode_description + source_line


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch game information and thumbnail from Steam",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 730
  %(prog)s https://store.steampowered.com/app/730/CounterStrike_2/
  %(prog)s 730 --lang japanese --output game_info.txt
        """,
    )
    parser.add_argument("appid", type=str, help="Steam app ID or full Steam store URL")
    parser.add_argument(
        "--lang",
        type=str,
        default="english",
        help="Language for game description (default: english)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for the BBCode description (default: stdout)",
    )
    parser.add_argument(
        "--thumbnail",
        type=Path,
        default=Path("thumbnail.jpg"),
        help="Output path for thumbnail (default: thumbnail.jpg)",
    )
    parser.add_argument(
        "--no-thumbnail", action="store_true", help="Skip downloading the thumbnail"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


def main() -> int:
    """Main execution function."""
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Extract app ID from URL if necessary
        appid = extract_appid_from_url(args.appid)
        # logger.info(f"Fetching data for Steam app ID: {appid}")

        # Fetch game data
        game_data = fetch_game_data(appid, args.lang)

        # Get and convert description
        html_description = game_data.get("about_the_game", "")
        if not html_description:
            logger.debug("No API game description found")
            # html_description = "No description available."
            r = requests.get(f"https://store.steampowered.com/app/{appid}/")
            s = BeautifulSoup(r.text, "html.parser")
            d = s.find("div", {"class": "game_area_description"})
            if not d:
                html_description = "No description available."
            else:
                h2 = d.find("h2")
                if h2:
                    h2.extract()
                html_description = (
                    "".join(str(i) for i in d.contents) or "No description available."
                )

        bbcode_description = convert_description_to_bbcode(html_description, args.lang)

        # Format final output
        output = format_output(appid, bbcode_description)

        # Write output
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            logger.info(f"Output saved to: {args.output}")
        else:
            print(output)

        # Download thumbnail
        # if not args.no_thumbnail:
        #     download_thumbnail(appid, args.lang, args.thumbnail)

        return 0

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
