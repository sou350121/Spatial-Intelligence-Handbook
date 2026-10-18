"""Escape generated prose for MDX; preserve fenced and inline code verbatim."""
import re


def compatible_comments(text):
    """Hide standalone metadata in standard Markdown reference titles.

    Keep the original HTML markers inside the title so existing metadata readers
    and source-ID deduplication still see exactly the same payload.
    """
    result=[];plain=[];fence=None
    def flush():
        block=''.join(plain)
        def convert(match):
            indent,comment,tail=match.groups()
            quote='"' if '"' not in comment else "'" if "'" not in comment else None
            if quote is None or re.search(r'\n\s*\n',comment):
                return match.group(0)  # CI's real MDX compiler rejects unsupported output.
            return indent+'[//]: # '+quote+comment+quote+tail
        result.append(re.sub(r'^( {0,3})(<!--[\s\S]*?-->)([ \t]*)$',convert,block,flags=re.M));plain.clear()
    for line in text.splitlines(keepends=True):
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if marker:
            flush();token=marker.group(1)
            if fence is None:fence=token
            elif token[0]==fence[0] and len(token)>=len(fence) and not line[marker.end():].strip():fence=None
            result.append(line)
        elif fence:result.append(line)
        else:plain.append(line)
    flush();return ''.join(result)


def safe_markdown(text):
    output=[];fence=None;inline=None;comment=False;math=None
    for line in text.splitlines(keepends=True):
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if marker and inline is None and not comment:
            token=marker.group(1)
            if fence is None:fence=token
            elif token[0]==fence[0] and len(token)>=len(fence) and not line[marker.end():].strip():fence=None
            output.append(line);continue
        if fence:
            output.append(line);continue
        parts=re.split(r'(<!--|-->|`+|\${1,2})',line)
        for part in parts:
            if comment:
                output.append(part)
                if part=='-->':comment=False
            elif part=='<!--' and inline is None:
                comment=True;output.append(part)
            elif part in {'$','$$'} and inline is None:
                if math is None:math=part
                elif math==part:math=None
                output.append(part)
            elif math:output.append(part)
            elif part and set(part)=={'`'}:
                if inline is None:inline=part
                elif part==inline:inline=None
                output.append(part)
            elif inline:output.append(part)
            else:
                for piece in re.split(r'(<(?:br|hr)\s*/?>)',part,flags=re.I):
                    if re.fullmatch(r'<(?:br|hr)\s*/?>',piece,flags=re.I):
                        output.append(re.sub(r'\s*/?>$',' />',piece))
                    else:output.append(piece.replace('<','&lt;').replace('{','&#123;').replace('}','&#125;'))
    return compatible_comments(''.join(output))
