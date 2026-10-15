"""Audit shipped Python 2/3 source imports against the official ModSDK list.

Only behavior_pack is release code. Host tools and tests may use host libraries.
Tokenization handles Python 2 print syntax, local imports and multiline imports.
"""
import io
import json
from pathlib import Path
import tokenize

ROOT = Path(__file__).resolve().parents[1]
WHITELIST = json.loads((Path(__file__).with_name('modsdk_module_whitelist.json')).read_text(encoding='utf8'))


def imports(source):
    ignored = (tokenize.COMMENT, tokenize.NL, tokenize.INDENT, tokenize.DEDENT)
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type not in ignored]
    found = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == tokenize.NAME and token.string in ('__import__', 'eval', 'exec'):
            found.append((token.start[0], '<dynamic:' + token.string + '>'))
        if token.type != tokenize.NAME or token.string not in ('from', 'import'):
            index += 1
            continue
        line = token.start[0]
        mode = token.string
        index += 1
        if mode == 'from':
            parts = []
            while index < len(tokens) and tokens[index].string != 'import':
                if tokens[index].type == tokenize.NEWLINE:
                    raise ValueError('Incomplete from import at %d' % line)
                parts.append(tokens[index].string)
                index += 1
            found.append((line, ''.join(parts)))
            index += 1
            while index < len(tokens) and tokens[index].type != tokenize.NEWLINE and tokens[index].string != ';':
                index += 1
        else:
            while index < len(tokens):
                parts = []
                while index < len(tokens) and (tokens[index].type == tokenize.NAME or tokens[index].string == '.'):
                    if tokens[index].string == 'as':
                        break
                    parts.append(tokens[index].string)
                    index += 1
                found.append((line, ''.join(parts)))
                if index < len(tokens) and tokens[index].string == 'as':
                    index += 2
                if index >= len(tokens) or tokens[index].string != ',':
                    break
                index += 1
    return found


def audit(folder=ROOT / 'behavior_pack'):
    allowed = set(WHITELIST['modules'])
    custom = set()
    paths = sorted(folder.rglob('*.py'))
    for path in paths:
        parts = path.relative_to(folder).with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        custom.add('.'.join(parts))
    external, violations = {}, []
    for path in paths:
        for line, name in imports(path.read_text(encoding='utf-8-sig')):
            if name.startswith('.') or name in custom:
                continue
            location = '%s:%d' % (path.relative_to(ROOT).as_posix(), line)
            external.setdefault(name, []).append(location)
            if name not in allowed:
                violations.append({'module': name, 'location': location})
    return {'files': len(paths), 'external_modules': external, 'violations': violations,
            'source': WHITELIST['source']}


if __name__ == '__main__':
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report['violations']))
