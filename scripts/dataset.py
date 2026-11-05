# SPDX-License-Identifier: MIT
"""Offline validation, deterministic exports and queries; Python standard library only."""
import argparse
from collections import Counter
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('records-full.json', 'origin-profiles.json', 'search-aliases.json',
          'product-scope.json', 'scope-exclusions.json', 'season-revisions.json')
KINDS = {'采收', '食用', '赏花', '赏果', '产地'}
WINDOWS = {'annual-observation', 'opening-only', 'seasonal-reference'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def valid_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in {'http', 'https'} and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and not any(k.lower() in {'token', 'access_token', 'secret', 'signature',
                                          'password', 'api_key'}
                            for k, _ in parse_qsl(parsed.query)))
    except ValueError:
        return False


def walk(value, path=''):
    """Yield leaf paths without discarding nested source references."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f'{path}/{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f'{path}/{index}')
    else:
        yield path, value


def validate_records(rows):
    errors, ids = [], set()
    if not isinstance(rows, list) or not rows:
        return ['records-full.json must be a non-empty array']
    for index, row in enumerate(rows):
        label = f'record[{index}]'
        if not isinstance(row, dict):
            errors.append(f'{label}: expected object')
            continue
        label = str(row.get('id', label))
        for key in ('id', 'fruit', 'province', 'place', 'kind', 'note', 'sourceTitle', 'url'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f'{label}: {key} must be a non-empty string')
        record_id = row.get('id')
        if isinstance(record_id, str):
            if record_id in ids:
                errors.append(f'{label}: duplicate id')
            ids.add(record_id)
        months = row.get('months')
        valid_months = (isinstance(months, list)
                        and all(type(m) is int and 1 <= m <= 12 for m in months))
        if not valid_months or (valid_months and len(set(months)) != len(months)):
            errors.append(f'{label}: months must contain unique integers from 1 to 12')
        if not isinstance(row.get('kind'), str) or row['kind'] not in KINDS:
            errors.append(f'{label}: unsupported kind')
        if 'year' in row and (type(row['year']) is not int or not 1 <= row['year'] <= 9999):
            errors.append(f'{label}: year must be a valid integer year')
        if 'harvestWindow' in row and (not isinstance(row['harvestWindow'], str) or row['harvestWindow'] not in WINDOWS):
            errors.append(f'{label}: unsupported harvestWindow')
        if row.get('harvestWindow') == 'annual-observation' and 'year' not in row:
            errors.append(f'{label}: annual observation requires year')
        dates = {}
        for key in ('startDate', 'endDate', 'sourceDate', 'checkedAt', 'observedDate'):
            if key not in row:
                continue
            try:
                value = row[key]
                # A source may only identify a publication month/year. Do not invent a day.
                if key == 'sourceDate' and isinstance(value, str) and re.fullmatch(r'\d{4}(?:-\d{2})?', value):
                    date.fromisoformat(value + ('-01-01' if len(value) == 4 else '-01'))
                    continue
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError('expected YYYY-MM-DD')
                dates[key] = date.fromisoformat(value)
            except (ValueError, TypeError):
                errors.append(f'{label}: invalid {key}')
        for key in ('startDate', 'endDate'):
            if key in dates:
                if valid_months and dates[key].month not in months:
                    errors.append(f'{label}: {key} is outside months')
                if 'year' in row and dates[key].year != row['year']:
                    errors.append(f'{label}: {key} conflicts with year')
        if 'startDate' in dates and 'endDate' in dates and dates['startDate'] > dates['endDate']:
            errors.append(f'{label}: endDate precedes startDate')
        if 'forecastMonths' in row and (not isinstance(row['forecastMonths'], list)
                or any(type(m) is not int or not 1 <= m <= 12 for m in row['forecastMonths'])):
            errors.append(f'{label}: invalid forecastMonths')
    return errors


def validate_inputs(inputs):
    errors = validate_records(inputs['records-full.json'])
    rows = inputs['records-full.json']
    if errors:
        return errors
    ids = {r['id'] for r in rows}
    profiles = inputs['origin-profiles.json']
    if not isinstance(profiles, dict):
        return errors + ['origin-profiles.json must be an object']
    for rid, profile in profiles.items():
        if rid not in ids:
            errors.append(f'profile {rid}: unknown record id')
        if not isinstance(profile, dict) or not isinstance(profile.get('fields'), dict) or not profile['fields']:
            errors.append(f'profile {rid}: non-empty fields object required')
            continue
        if not all(isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
                   for k, v in profile['fields'].items()):
            errors.append(f'profile {rid}: fields must map names to non-empty strings')
        if not profile.get('source') and not profile.get('sources'):
            errors.append(f'profile {rid}: source required')
    aliases = inputs['search-aliases.json']
    if not isinstance(aliases, dict) or not isinstance(aliases.get('groups'), list) or not isinstance(aliases.get('sources'), dict):
        return errors + ['search-aliases.json requires groups array and sources object']
    group_ids = set()
    for group in aliases['groups']:
        if not isinstance(group, dict) or not isinstance(group.get('id'), str):
            errors.append('alias group requires a string id')
            continue
        gid = group['id']
        if gid in group_ids:
            errors.append(f'alias {gid}: duplicate id')
        group_ids.add(gid)
        for key in ('aliases', 'fruitNames', 'identityTerms', 'recordIds', 'sourceIds'):
            if not isinstance(group.get(key), list) or not all(isinstance(v, str) for v in group[key]):
                errors.append(f'alias {gid}: {key} must be an array of strings')
        for rid in group.get('recordIds', []) if isinstance(group.get('recordIds'), list) else []:
            if rid not in ids:
                errors.append(f'alias {gid}: unknown record id {rid}')
        for sid in group.get('sourceIds', []) if isinstance(group.get('sourceIds'), list) else []:
            if sid not in aliases['sources']:
                errors.append(f'alias {gid}: unknown source id {sid}')
    revisions = inputs['season-revisions.json']
    if not isinstance(revisions, list):
        errors.append('season-revisions.json must be an array')
    else:
        by_id = {r['id']: r for r in rows}
        for revision in revisions:
            if not isinstance(revision, dict) or revision.get('id') not in ids or not isinstance(revision.get('patch'), dict):
                errors.append('invalid season revision or unknown record id')
                continue
            for key, value in revision['patch'].items():
                if by_id[revision['id']].get(key) != value:
                    errors.append(f"revision {revision['id']}: snapshot differs for {key}")
    for name in ('product-scope.json', 'scope-exclusions.json'):
        if not isinstance(inputs[name], dict):
            errors.append(f'{name} must be an object')
    for name, obj in inputs.items():
        for path, value in walk(obj):
            if isinstance(value, str):
                if value.startswith(('http://', 'https://')) and not valid_url(value):
                    errors.append(f'{name}{path}: malformed URL or credential-bearing URL')
                if re.match(r'^[A-Za-z]:[\\/]', value) or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', value):
                    errors.append(f'{name}{path}: local path or private key')
                if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})', value):
                    errors.append(f'{name}{path}: possible GitHub token')
    for row in rows:
        if not valid_url(row['url']):
            errors.append(f"{row['id']}: invalid main source URL")
    return errors


def source_index(inputs):
    indexed = {}
    for name, obj in inputs.items():
        for pointer, value in walk(obj):
            if not isinstance(value, str) or not value.startswith(('http://', 'https://')):
                continue
            entry = indexed.setdefault(value, {'url': value, 'references': []})
            ref = {'file': f'data/{name}', 'pointer': pointer}
            if name == 'records-full.json':
                ref['recordId'] = obj[int(pointer.split('/')[1])]['id']
            elif name == 'origin-profiles.json':
                ref['recordId'] = pointer.split('/')[1]
            entry['references'].append(ref)
    return [indexed[url] for url in sorted(indexed)]


def csv_bytes(rows):
    output = io.StringIO(newline='')
    fields = ('id', 'fruit', 'title', 'province', 'place', 'kind', 'months', 'year',
              'harvestWindow', 'sourcePeriod', 'startDate', 'endDate', 'observedDate',
              'sourceDate', 'checkedAt', 'note', 'sourceTitle', 'url')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        projected = {key: row.get(key, '') for key in fields}
        projected['months'] = '|'.join(map(str, row['months']))
        # Prevent spreadsheet formulas when users add source text later.
        for key, value in projected.items():
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                projected[key] = "'" + value
        writer.writerow(projected)
    return ('\ufeff' + output.getvalue()).encode('utf-8')


def artifacts(inputs):
    rows = inputs['records-full.json']
    return {'data/sources.json': json_bytes(source_index(inputs)),
            'exports/records.csv': csv_bytes(rows),
            'exports/fruit-seasons.csv': csv_bytes([r for r in rows if r['months']])}


def manifest(root, inputs, generated):
    rows = inputs['records-full.json']
    content = {f'data/{name}': (root / 'data' / name).read_bytes() for name in INPUTS}
    content.update(generated)
    return {
        'schemaVersion': 1, 'snapshotDate': '2026-11-05',
        'baseline': 'Independent data snapshot; no application or photo dependencies',
        'statistics': {'records': len(rows), 'withMonths': sum(bool(r['months']) for r in rows),
                       'withoutMonths': sum(not r['months'] for r in rows),
                       'rawFruitLabels': len({r['fruit'] for r in rows}),
                       'rawProvinceLabels': len({r['province'] for r in rows}),
                       'profiles': len(inputs['origin-profiles.json']),
                       'sourceUrls': len(source_index(inputs)),
                       'kinds': dict(sorted(Counter(r['kind'] for r in rows).items()))},
        'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                  for name, raw in sorted(content.items())}}


def load(root):
    return {name: read_json(root / 'data' / name) for name in INPUTS}


def select_records(rows, month=None, year=None, fruit=None):
    if month is not None and year is None:
        raise ValueError('--month requires --year to avoid mixing annual observations')
    return [r for r in rows if (month is None or month in r['months'])
            and (year is None or 'year' not in r or r['year'] == year)
            and (fruit is None or fruit in r['fruit'] or fruit in r.get('title', ''))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('validate', 'build', 'query'))
    parser.add_argument('--month', type=int, choices=range(1, 13))
    parser.add_argument('--year', type=int, choices=range(1, 10000))
    parser.add_argument('--fruit', help='Literal substring of fruit/title, not synonym expansion')
    args = parser.parse_args()
    inputs = load(ROOT)
    errors = validate_inputs(inputs)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.command == 'query':
        try:
            rows = select_records(inputs['records-full.json'], args.month, args.year, args.fruit)
        except ValueError as error:
            parser.error(str(error))
        sys.stdout.buffer.write(json_bytes(rows))
        return 0
    generated = artifacts(inputs)
    expected_manifest = json_bytes(manifest(ROOT, inputs, generated))
    generated['manifest.json'] = expected_manifest
    if args.command == 'build':
        for name, raw in generated.items():
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    else:
        for name, expected in generated.items():
            path = ROOT / name
            if not path.is_file() or path.read_bytes() != expected:
                errors.append(f'{name}: missing or stale; review input changes then run build')
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps({'status': 'ok', 'command': args.command,
                      'statistics': manifest(ROOT, inputs, artifacts(inputs))['statistics']},
                     ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
