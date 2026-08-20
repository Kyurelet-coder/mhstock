import json
import re
from pathlib import Path
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE_URL = 'https://mhcollector.com/category/characters/ghouls/'
OUT_JSON = Path('ghouls_catalog.json')


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def extract_release_info(title: str, character: str):
    text = normalize_text(title)
    if not text:
        return None

    # Remove trailing year/flags like (2013), (B), (E), (R)
    cleaned = re.sub(r'\s*\((?:B|E|R|\d{4})\)', '', text)
    cleaned = re.sub(r'\s*\(\d{4}\)', '', cleaned)
    cleaned = cleaned.strip()

    # Try to split the collection prefix from the rest using the known character name
    if character and cleaned.lower().startswith(character.lower()):
        collection = ''
        name = character
    else:
        collection = ''
        name = character

    # If the title includes a dash or en dash before the character name, use the prefix as collection
    needle = character
    if needle and needle.lower() in cleaned.lower():
        idx = cleaned.lower().find(needle.lower())
        prefix = cleaned[:idx].strip(' –-')
        if prefix:
            collection = prefix
            name = character
        else:
            collection = ''
            name = character
    else:
        collection = ''
        name = character

    return {
        'title': text,
        'collection': collection,
        'name': name,
    }


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        page.goto(BASE_URL, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(2000)

        character_links = []
        for el in page.locator('h3 a[href]').element_handles():
            href = el.get_attribute('href') or ''
            text = normalize_text(el.inner_text())
            if href and text:
                character_links.append({'character': text, 'href': href})

        results = []
        for item in character_links:
            character = item['character']
            href = item['href']
            page.goto(href, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(1500)
            headings = page.locator('h3').all_text_contents()
            releases = []
            for heading in headings:
                cleaned = normalize_text(heading)
                if not cleaned:
                    continue
                if cleaned.lower().startswith('releases'):
                    continue
                if cleaned.lower().startswith(character.lower()):
                    continue
                if 'monster high' in cleaned.lower():
                    continue
                if cleaned.count('(') and 'https://' not in cleaned:
                    info = extract_release_info(cleaned, character)
                    if info:
                        releases.append(info)
            results.append({'character': character, 'href': href, 'releases': releases})

        OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Wrote {len(results)} characters to {OUT_JSON}', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
