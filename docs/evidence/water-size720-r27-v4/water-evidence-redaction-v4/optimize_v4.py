"""Generate an inspectable optimized copy; preserve the slow original driver."""
from pathlib import Path


HERE = Path(__file__).resolve().parent
source = (HERE / 'package_v4.py').read_text(encoding='utf8')
source = source.replace('secrets = set()\n', 'secrets = set()\nSECRET_PATTERN = None\n')
source = source.replace(
    '        for secret in sorted(secrets, key=len, reverse=True):\n'
    '            for encoded in {secret, json.dumps(secret, ensure_ascii=True)[1:-1]}:\n'
    '                if encoded in value:\n'
    "                    found.append(location + ':exact')\n"
    "                    value = value.replace(encoded, '[REDACTED]')\n",
    "        if SECRET_PATTERN.search(value):\n"
    "            found.append(location + ':exact')\n"
    "            value = SECRET_PATTERN.sub('[REDACTED]', value)\n")
source = source.replace(
    "            value = PATTERN.sub('[REDACTED]', value)\n",
    "            value = PATTERN.sub('[REDACTED]', value)\n"
    "        unescaped = unescape(value)\n"
    "        if unescaped != value:\n"
    "            revised = sanitize(unescaped, found, location + ':unescaped', depth + 1)\n"
    "            if revised != unescaped:\n"
    "                value = revised\n")
helper = r'''

def unescape(value):
    value = re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                   lambda match: chr(int(match[1] or match[2], 16)), value)
    return value.replace('\\"', '"').replace("\\'", "'")


def compile_secret_pattern(values):
    """Exact match using a prefix trie, without repeatedly sorting 972 registries."""
    trie = {}
    for value in values:
        for variant in {value, json.dumps(value, ensure_ascii=True)[1:-1]}:
            node = trie
            for char in variant:
                node = node.setdefault(char, {})
            node[None] = True

    def expression(node):
        parts = [re.escape(char) + expression(child)
                 for char, child in sorted(node.items(), key=lambda row: row[0] or '')
                 if char is not None]
        result = parts[0] if len(parts) == 1 else '(?:' + '|'.join(parts) + ')'
        if None in node:
            return '(?:' + result + ')?' if parts else ''
        return result

    return re.compile(expression(trie) if values else r'(?!)')


def exact_credentials(raw):
    """Same decoded JSON/base64/escape views as root scanner; exact checks batched."""
    seen = set()
    found = False

    def visit(data, depth=0):
        nonlocal found
        assert depth < 48
        fingerprint = sha(data)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        text = data.decode('utf8')
        if SECRET_PATTERN.search(text):
            found = True
        try:
            value = json.loads(text)
        except ValueError:
            value = None
        if isinstance(value, (dict, list)):
            walk(value, depth + 1)
        if len(text) >= 32 and len(text) % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', text):
            try:
                visit(base64.b64decode(text, validate=True), depth + 1)
            except UnicodeDecodeError:
                pass
        revised = unescape(text)
        if revised != text:
            visit(revised.encode('utf8'), depth + 1)

    def walk(value, depth):
        assert depth < 48
        if isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str):
            visit(value.encode('utf8'), depth + 1)

    visit(raw)
    return ['exact local credential'] if found else []


def combined_credentials(scanner, raw):
    # Original independent scanner remains unchanged for JSON/pattern/escape checks.
    # The exact credential comparison is performed over the same decoded views
    # with a compiled prefix trie rather than N membership loops per JSON leaf.
    return sorted(set(scanner.credentials(raw) + exact_credentials(raw)))
'''
source = source.replace('\ndef main():\n', helper + '\n\ndef main():\n    global SECRET_PATTERN\n')
source = source.replace(
    '    secret_bytes = tuple(secret.encode(\'utf8\') for secret in secrets)\n',
    "    SECRET_PATTERN = compile_secret_pattern(secrets)\n"
    "    print(json.dumps({'phase': 'preflight', 'inputs': len(inputs), 'credential_values': len(secrets)}), flush=True)\n")
source = source.replace('scanner.credentials(clean, secret_bytes)', 'combined_credentials(scanner, clean)')
source = source.replace(
    '    sanitized = {}\n    for label, path in inputs.items():\n',
    '    sanitized = {}\n    for ordinal, (label, path) in enumerate(inputs.items(), 1):\n'
    "        if ordinal % 25 == 0:\n"
    "            print(json.dumps({'phase': 'preflight', 'checked': ordinal}), flush=True)\n")
source = source.replace(
    "    inputs[WORK.name + '/' + Path(__file__).name] = Path(__file__)\n",
    "    for script in ('package_v4.py', 'package_v4_optimized.py', 'optimize_v4.py', 'aborted-slow-preflight.json', 'test_optimized_scanner.py', 'optimized-scanner-controls-v1.json'):\n"
    "        inputs[WORK.name + '/' + script] = WORK / script\n"
    "    next_a = WORK.with_name('water-next-A-workflow-v1')\n"
    "    for path in next_a.iterdir():\n"
    "        if path.is_file():\n"
    "            inputs[next_a.name + '/' + path.name] = path\n")
source = source.replace(
    "        original_v3_preserved=True, original_raws_modified=False)\n",
    "        original_v3_preserved=True, original_raws_modified=False,\n"
    "        scanner_exact_optimization='prefix-trie over the same JSON/base64/unescape decoded views; root original scanner unchanged for other checks')\n")
assert 'for secret in sorted(secrets' not in source
assert 'secret_bytes' not in source
compile(source, str(HERE / 'package_v4_optimized.py'), 'exec')
(HERE / 'package_v4_optimized.py').write_text(source, encoding='utf8', newline='\n')
print('Generated inspectable optimized driver; original preserved.')
