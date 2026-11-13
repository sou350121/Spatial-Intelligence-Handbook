"""Read a complete dated edition from arXiv's official announcement list."""
from datetime import date, datetime
from email.utils import format_datetime
from html import unescape
import re
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo


def _text(html: str) -> str:
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', html)).split())


def announcement_xml(html: str, category: str, expected: date, latest: date | None = None) -> str:
    heading = re.search(r'<h3[^>]*>\s*Showing new listings for ([^<]+)</h3>', html)
    totals = re.findall(r'\(showing (\d+) of (\d+) entries\)', html)
    edition = datetime.strptime(heading[1].strip(), '%A, %d %B %Y').date() if heading else None
    if edition is None or not expected <= edition <= (latest or expected):
        raise ValueError(f'arXiv {category} has no verified edition for {expected}')
    if not totals or any(shown != total for shown, total in totals):
        raise ValueError(f'arXiv {category} edition is incomplete')
    rows = re.findall(r'<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>', html, re.S)
    if not rows or len(rows) != sum(int(total) for _, total in totals):
        raise ValueError(f'arXiv {category} edition row count mismatch')
    root = ET.Element('rss')
    channel = ET.SubElement(root, 'channel')
    timestamp = format_datetime(datetime.combine(edition, datetime.min.time(), ZoneInfo('America/New_York')))
    for label, details in rows:
        identity = re.search(r'''href\s*=\s*["']/abs/(\d{4}\.\d{4,5})["']''', label)
        title = re.search(r'''<div\s+class=["']list-title mathjax["']>\s*<span[^>]*>Title:</span>(.*?)</div>''', details, re.S)
        abstract = re.search(r'''<p\s+class=["']mathjax["']>(.*?)</p>''', details, re.S)
        if not identity or not title or not abstract or not _text(title[1]) or not _text(abstract[1]):
            raise ValueError(f'arXiv {category} edition has an incomplete paper')
        item = ET.SubElement(channel, 'item')
        for tag, value in (
            ('title', _text(title[1])),
            ('link', f'https://arxiv.org/abs/{identity[1]}'),
            ('description', _text(abstract[1])),
            ('pubDate', timestamp),
        ):
            ET.SubElement(item, tag).text = value
    return ET.tostring(root, encoding='unicode')


def fetch_announcement_xml(category: str, expected: date, latest: date | None = None) -> str:
    if not re.fullmatch(r'[A-Za-z-]+(?:\.[A-Z]+)?', category):
        raise ValueError('invalid arXiv category')
    url = f'https://arxiv.org/list/{category}/new?show=2000'
    request = Request(url, headers={'User-Agent': 'Pulsar Spatial arXiv announcements/1.0'})
    with urlopen(request, timeout=12) as response:
        if response.geturl() != url or response.headers.get_content_type() != 'text/html':
            raise ValueError('unexpected arXiv announcement response')
        body = response.read(8_000_001)
    if len(body) > 8_000_000:
        raise ValueError('arXiv announcement page exceeds byte limit')
    return announcement_xml(body.decode('utf-8'), category, expected, latest)
