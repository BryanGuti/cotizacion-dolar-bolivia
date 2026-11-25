import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.add(element_id)

        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])

        if tag == "script" and attributes.get("src"):
            self.assets.append(attributes["src"])
        elif tag == "link" and attributes.get("href"):
            if attributes.get("rel") in {"stylesheet", "icon"}:
                self.assets.append(attributes["href"])


class TestFrontendContract(unittest.TestCase):
    def parse_page(self, relative_path):
        page = FRONTEND / relative_path
        parser = AssetParser()
        parser.feed(page.read_text(encoding="utf-8"))
        return page, parser

    def test_dashboard_and_compare_assets_exist(self):
        for relative_path in ("index.html", "pages/compare.html"):
            with self.subTest(page=relative_path):
                page, parser = self.parse_page(relative_path)
                for asset in parser.assets:
                    parsed = urlparse(asset)
                    if parsed.scheme or parsed.netloc:
                        continue
                    target = (page.parent / parsed.path).resolve()
                    self.assertTrue(target.is_file(), f"Missing asset: {asset}")

                for link in parser.links:
                    parsed = urlparse(link)
                    if parsed.scheme or parsed.netloc or parsed.path.startswith("#"):
                        continue
                    target = (page.parent / parsed.path).resolve()
                    if not parsed.path:
                        target = page
                    self.assertTrue(target.is_file(), f"Broken local link: {link}")

    def test_compare_script_dom_references_exist(self):
        _, parser = self.parse_page("pages/compare.html")
        script = (FRONTEND / "js/compare.js").read_text(encoding="utf-8")
        referenced_ids = set(re.findall(
            r'getElementById\(["\']([^"\']+)["\']\)',
            script,
        ))
        self.assertTrue(referenced_ids)
        self.assertEqual(referenced_ids - parser.ids, set())

    def test_history_urls_are_relative_to_frontend_data_root(self):
        source = (FRONTEND / "js/data.js").read_text(encoding="utf-8")
        self.assertIn('new URL("../data/current.json", SCRIPT_DIRECTORY)', source)
        self.assertIn('new URL("../data/history/", SCRIPT_DIRECTORY)', source)
        self.assertNotIn('`/data/history/', source)


if __name__ == "__main__":
    unittest.main()
