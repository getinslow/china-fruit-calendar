# SPDX-License-Identifier: MIT
"""Regression checks for data mistakes and unsafe time interpretation."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from dataset import csv_bytes, load, ROOT, select_records, validate_inputs, validate_records


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = load(ROOT)
        cls.row = copy.deepcopy(cls.inputs['records-full.json'][0])

    def test_snapshot_is_valid(self):
        self.assertEqual(validate_inputs(self.inputs), [])

    def test_invalid_months_and_duplicate_ids_are_rejected(self):
        for months in ([0], [13], [True], [6, 6], '6', [None]):
            row = dict(self.row, months=months)
            self.assertTrue(validate_records([row]), repr(months))
        self.assertTrue(validate_records([self.row, self.row]))

    def test_annual_observation_requires_year(self):
        row = dict(self.row, harvestWindow='annual-observation')
        row.pop('year', None)
        self.assertTrue(validate_records([row]))

    def test_dates_must_be_real_and_in_documented_window(self):
        for value in ('2024-02-30', '2024-2-3', '2024-12-01'):
            row = dict(self.row, months=[11], year=2024, startDate=value)
            self.assertTrue(validate_records([row]), value)

    def test_profile_reference_cannot_dangle(self):
        inputs = copy.deepcopy(self.inputs)
        inputs['origin-profiles.json']['missing-id'] = next(iter(inputs['origin-profiles.json'].values()))
        self.assertTrue(any('unknown record id' in e for e in validate_inputs(inputs)))

    def test_partial_publication_dates_keep_their_precision(self):
        for value in ('2007', '2007-05'):
            self.assertEqual(validate_records([dict(self.row, sourceDate=value)]), [])
        self.assertTrue(validate_records([dict(self.row, sourceDate='2007-13')]))

    def test_revision_must_survive_snapshot(self):
        inputs = copy.deepcopy(self.inputs)
        rid = inputs['season-revisions.json'][0]['id']
        next(r for r in inputs['records-full.json'] if r['id'] == rid)['months'] = [6]
        self.assertTrue(any('snapshot differs' in e for e in validate_inputs(inputs)))

    def test_source_credentials_are_rejected(self):
        inputs = copy.deepcopy(self.inputs)
        inputs['records-full.json'][0]['url'] = 'https://example.com/?access_token=secret'
        self.assertTrue(validate_inputs(inputs))

    def test_annual_records_do_not_recur_and_unknown_windows_do_not_match(self):
        rows = [dict(self.row, id='annual', months=[11], year=2024),
                dict(self.row, id='unknown', months=[]),
                dict(self.row, id='reference', months=[11])]
        rows[1].pop('year', None)
        rows[2].pop('year', None)
        self.assertEqual([r['id'] for r in select_records(rows, 11, 2026)], ['reference'])
        with self.assertRaises(ValueError):
            select_records(rows, month=11)

    def test_split_windows_keep_the_gap(self):
        row = dict(self.row, months=[11, 12, 1, 5], year=2024)
        self.assertEqual(select_records([row], 3, 2024), [])
        self.assertEqual(len(select_records([row], 1, 2024)), 1)

    def test_csv_neutralizes_formula_cells_and_preserves_chinese(self):
        raw = csv_bytes([dict(self.row, title='=HYPERLINK("https://example.com")')])
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        self.assertIn("'=HYPERLINK", raw.decode('utf-8-sig'))
        self.assertIn(self.row['fruit'], raw.decode('utf-8-sig'))


if __name__ == '__main__':
    unittest.main()
