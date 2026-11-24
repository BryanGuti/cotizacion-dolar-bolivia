import requests

from scraper.config import SOURCES


def inspect_bcb():
    url = SOURCES["bcb"]["url"]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print("=" * 60)
    print("BCB HTTP INSPECTION")
    print("=" * 60)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        print(f"Status code: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Encoding: {response.encoding}")
        print(f"Response size: {len(response.content)} bytes")

        response.raise_for_status()

        print("\n" + "=" * 60)
        print("RESPONSE CONTENT (FIRST 5000 CHARACTERS)")
        print("=" * 60)

        print(response.text[:5000])

    except requests.RequestException as error:
        print(f"\nHTTP request failed: {error}")


if __name__ == "__main__":
    inspect_bcb()
