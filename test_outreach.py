import csv
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import outreach as o


class OutreachTests(unittest.TestCase):
    def setUp(self):
        # Synthetic dashboard exercises the parser without distributing private inputs.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        matrix = Path(folder.name) / "dashboard.csv"
        rows = [[str(rank), "A - fixture", "", "Example provider", "Example category",
                 f"Example offer {rank}", "We identify appropriate prospects for review."]
                for rank in range(1, 16)]
        for name in ("Financial operations & compliance", "Specialty finance origination",
                     "Insurance distribution & risk", "Proprietary acquisition origination"):
            rows.append([name, "", "", "", "", "Example provider", "", "", "Example source pitch"])
        with matrix.open("w", newline="") as file:
            csv.writer(file).writerows(rows)
        matrix_patch = patch.object(o.s, "DEFAULT_MATRIX", matrix)
        matrix_patch.start()
        self.addCleanup(matrix_patch.stop)

    def test_catalog_is_traceable(self):
        offers = o.catalog()
        self.assertEqual(len(offers), 19)
        for offer in offers.values():
            self.assertTrue(offer['source_record'] > 0)
            self.assertTrue(offer['source_offer_text'])

    def test_focus_must_appear_on_site(self):
        found = o.focus_candidates({'E01': {'url': 'https://example.com', 'text': 'Our Payment Gateway serves software platforms.'}})
        self.assertTrue(found)
        for value in found.values():
            self.assertIn(value['literal'], 'Our Payment Gateway serves software platforms.')
            self.assertNotEqual(value['term'], 'private equity')

    def test_copy_is_opener_then_pitch_and_no_dash_punctuation(self):
        draft = o.compose('Ana', 'A-B', 'asset-based lending', 'sales', o.catalog()['lane_specialty_finance'])
        self.assertTrue(draft['outreach_copy'].startswith('Ana,'))
        self.assertEqual(draft['outreach_copy'].split('\n\n')[0], draft['opener'])
        self.assertEqual(draft['outreach_copy'].split('\n\n')[1], draft['service_pitch'])
        self.assertNotIn('-', draft['outreach_copy'])
        self.assertNotIn('–', draft['outreach_copy'])

    def test_wrong_role_never_gets_copy(self):
        state = {'focus_candidates': {'F01': {'term': 'payments'}}}
        answer = {'answers': {'offer': {'choice': 'WRONG_ROLE', 'confidence': .99},
                             'focus': {'choice': 'F01'}, 'role': {'choice': 'technical'}}}
        row = {'screen_source_row': '2'}
        with patch('outreach.state_for', return_value=state), patch('outreach.selection_request', return_value={}), patch('outreach.cached_ask', return_value=(answer, Path('fixture.json'))):
            result = o.draft_one(row, o.catalog(), SimpleNamespace(model='fixture', out=Path('.')))
        self.assertEqual(result['outreach_status'], 'HOLD')
        self.assertNotIn('outreach_copy', result)

    def test_no_supported_offer_never_gets_copy(self):
        state = {'focus_candidates': {'F01': {'term': 'wealth management'}}}
        answer = {'answers': {'offer': {'choice': 'NO_SUPPORTED_OFFER', 'confidence': .99},
                             'focus': {'choice': 'F01'}, 'role': {'choice': 'executive'}}}
        with patch('outreach.state_for', return_value=state), patch('outreach.selection_request', return_value={}), patch('outreach.cached_ask', return_value=(answer, Path('fixture.json'))):
            result = o.draft_one({'screen_source_row': '2'}, o.catalog(), SimpleNamespace(model='fixture', out=Path('.')))
        self.assertEqual(result['outreach_status'], 'HOLD')
        self.assertEqual(result['outreach_reason'], 'NO_SUPPORTED_OFFER')

    def test_failed_draft_check_keeps_copy_blank(self):
        offers = o.catalog()
        state = {'company': {'name': 'Example', 'domain': 'example.com'}, 'job_title': 'CEO', 'rules': o.RULES,
                 'offers': offers, 'focus_candidates': {'F01': {'term': 'embedded payments', 'literal': 'embedded payments', 'url': 'https://example.com', 'excerpt_id': 'E01'}},
                 'website_excerpts': {'E01': {'url': 'https://example.com', 'text': 'We provide embedded payments for software platforms.'}}}
        selection = {'answers': {'offer': {'choice': 'offer_02', 'confidence': .99, 'probabilities': {k: float(k == 'offer_02') for k in offers}},
                                'focus': {'choice': 'F01'}, 'role': {'choice': 'executive'}}}
        qa = {'answers': {k: {'noul': .95} for k in o.QA_MINIMUMS}}
        qa['answers']['business_fit']['noul'] = .3
        row = {'screen_source_row': '2', 'First Name': 'Ana', 'company_name': 'Example'}
        with patch('outreach.state_for', return_value=state), patch('outreach.cached_ask', side_effect=[(selection, Path('selection.json')), (qa, Path('qa.json'))]):
            result = o.draft_one(row, offers, SimpleNamespace(model='fixture', out=Path('.')))
        self.assertEqual(result['outreach_status'], 'HOLD')
        self.assertNotIn('outreach_copy', result)

    def test_approved_questions_and_scoped_review_context(self):
        import json
        revision = json.loads((o.s.ROOT / 'outreach_check_revision.json').read_text())
        state = {'company': {}, 'job_title': 'CEO', 'rules': o.RULES, 'website_excerpts': {},
                 'offers': o.catalog(), 'focus_candidates': {'F01': {'term': 'payments'}}}
        request = o.qa_request(state, 'offer_02', 'F01', {}, 'fixture')
        self.assertEqual(set(request['state']['offers']), {'offer_02'})
        self.assertNotIn('focus_candidates', request['state'])
        for key, text in revision['proposed_questions'].items():
            self.assertEqual(request['questions'][key]['instructions'], 'Apply `rules`. ' + text)


if __name__ == '__main__':
    unittest.main()
