"""Read legacy and MDX-compatible metadata without changing its five-axis payload."""
import re

MARKER='<!-- ontology-5axis'
END='-->'
_HEADER=re.compile(r'^\s*(?:(?P<ref>\[//\]: # )(?P<quote>["\']))?(?P<block><!-- ontology-5axis[\s\S]*?-->)(?(ref)(?P=quote))')


def get_header_block(text):
    match=_HEADER.match(text)
    return match.group('block') if match else None


def without_header(text):
    match=_HEADER.match(text)
    return text[match.end():] if match else text


def format_header(block):
    if not block.startswith(MARKER) or not block.endswith(END):raise ValueError('Invalid metadata block')
    quote='"' if '"' not in block else "'" if "'" not in block else None
    if quote is None:raise ValueError('Metadata contains conflicting reference-title delimiters')
    return '[//]: # '+quote+block+quote
