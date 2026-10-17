"""Escape generated prose for MDX; preserve fenced and inline code verbatim."""
import re


def safe_markdown(text):
    output=[];fence=None;inline=None;comment=False
    for line in text.splitlines(keepends=True):
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})',line)
        if marker and inline is None and not comment:
            token=marker.group(1)
            if fence is None:fence=token
            elif token[0]==fence[0] and len(token)>=len(fence) and not line[marker.end():].strip():fence=None
            output.append(line);continue
        if fence:
            output.append(line);continue
        parts=re.split(r'(<!--|-->|`+)',line)
        for part in parts:
            if comment:
                output.append(part)
                if part=='-->':comment=False
            elif part=='<!--' and inline is None:
                comment=True;output.append(part)
            elif part and set(part)=={'`'}:
                if inline is None:inline=part
                elif part==inline:inline=None
                output.append(part)
            elif inline:output.append(part)
            else:output.append(part.replace('<','&lt;').replace('{','&#123;').replace('}','&#125;'))
    return ''.join(output)
