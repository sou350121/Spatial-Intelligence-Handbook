"""Maintain only the marked report index in the canonical reports landing page."""
from pathlib import Path
import re

REPO=Path(__file__).resolve().parents[2]
START='<!-- BEGIN PULSAR REPORT INDEX -->'
END='<!-- END PULSAR REPORT INDEX -->'


def render(repo):
    lines=[START,'','## 自动报告目录 (Report Archive)','','| 类型 | 日期 | 报告 |','|---|---|---|']
    for directory,label,limit in [('spatial-daily','日报',14),('weekly','周报',52),('curated-signal','产业信号',7)]:
        files=sorted([p for p in (repo/'reports'/directory).glob('*.md') if re.fullmatch(r'\d{4}-(?:\d{2}-\d{2}|W\d{2})',p.stem)],reverse=True)[:limit]
        for p in files:lines.append(f'| {label} | {p.stem} | [阅读](./{directory}/{p.name}) |')
    lines+=['','完整归档：[GitHub reports](https://github.com/sou350121/Spatial-Intelligence-Handbook/tree/main/reports)。','',END]
    return '\n'.join(lines)


def update(text,block):
    if START not in text and END not in text:return text.rstrip()+'\n\n'+block+'\n'
    if text.count(START)!=1 or text.count(END)!=1 or text.index(START)>text.index(END):raise ValueError('Malformed managed report index markers')
    a=text.index(START);b=text.index(END)+len(END)
    return text[:a]+block+text[b:]


def main():
    p=REPO/'reports/overview.md';old=p.read_text();new=update(old,render(REPO))
    if new!=old:p.write_text(new,encoding='utf-8')
    print('Report archive index synchronized; manual text preserved')


if __name__=='__main__':main()
