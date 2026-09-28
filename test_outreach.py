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

    def test_business_sentence_available_without_glossary_match(self):
        text = 'Embedded AI workflows, tools and insights for homebuyers & loan officers.'
        found = o.focus_candidates({'E01': {'url': 'https://example.com', 'text': text}})
        self.assertTrue(any(v['literal'] == text and v.get('kind') == 'sentence' for v in found.values()))
        self.assertTrue(all(v['literal'] in text for v in found.values()))

    def test_selection_payload_preserves_candidates_without_duplication(self):
        text = 'Embedded AI workflows, tools and insights for homebuyers and loan officers.'
        state = {'offers': o.catalog(), 'focus_candidates': {
            'F01': {'term': text, 'literal': text, 'context': text, 'excerpt_id': 'E01'}},
            'company': {'name': 'Example'}, 'job_title': 'CEO', 'website_excerpts': {}, 'rules': o.RULES}
        request = o.selection_request(state, 'fixture')
        self.assertEqual(request['state']['focus_candidates']['F01']['text'], text)
        self.assertEqual(set(request['questions']['focus']['criteria']), {'F01', 'NONE'})
        self.assertNotIn(text, request['questions']['focus']['criteria']['F01'])
        self.assertEqual(request['state']['offers']['offer_02']['pitch'], state['offers']['offer_02']['pitch'])

    def test_expanded_offers_require_explicit_source_scope(self):
        from outreach_options import expand_catalog
        with self.assertRaises(ValueError):
            expand_catalog(o.catalog(), o.s.DEFAULT_MATRIX)
        with o.s.DEFAULT_MATRIX.open('a', newline='') as file:
            csv.writer(file).writerow(['A B2B referral, partnership, or software-sales offer.'])
        expanded = expand_catalog(o.catalog(), o.s.DEFAULT_MATRIX)
        self.assertEqual(len(expanded), 27)
        self.assertTrue(expanded['adapt_mortgage_software']['adaptation'])
        self.assertIn('B2B', expanded['adapt_mortgage_software']['source_offer_text'])

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
        self.assertTrue(result['outreach_candidate_copy'])
        self.assertEqual(result['outreach_qa_business_fit'], .3)

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

    def test_ambiguous_offer_stays_held_even_if_copy_checks_pass(self):
        offers = o.catalog()
        state = {'company': {'name': 'Example', 'domain': 'example.com'}, 'job_title': 'CEO', 'rules': o.RULES,
                 'offers': offers, 'focus_candidates': {'F01': {'term': 'embedded payments', 'literal': 'embedded payments',
                    'url': 'https://example.com', 'excerpt_id': 'E01'}},
                 'website_excerpts': {'E01': {'url': 'https://example.com', 'text': 'We provide embedded payments.'}}}
        selection = {'answers': {'offer': {'choice': 'offer_02', 'confidence': .4,
                     'probabilities': {'offer_02': .6, 'NO_SUPPORTED_OFFER': .4}},
                     'focus': {'choice': 'F01'}, 'role': {'choice': 'executive'}}}
        qa = {'answers': {key: {'noul': .99} for key in o.QA_MINIMUMS}}
        with patch('outreach.state_for', return_value=state), patch('outreach.cached_ask',
                side_effect=[(selection, Path('selection.json')), (qa, Path('qa.json'))]):
            result = o.draft_one({'screen_source_row': '2', 'First Name': 'Ana', 'company_name': 'Example'},
                                 offers, SimpleNamespace(model='fixture', out=Path('.')))
        self.assertEqual(result['outreach_status'], 'HOLD')
        self.assertIn('offer_match', result['outreach_reason'])
        self.assertNotIn('outreach_copy', result)
        self.assertTrue(result['outreach_candidate_copy'])

    def test_concurrent_identical_requests_share_one_saved_response(self):
        import concurrent.futures
        import os
        import time
        request = {'model': 'fixture', 'state': {}, 'questions': {'check': {'type': 'noul', 'instructions': 'Fixture?'}}}
        response = {'model': 'fixture', 'answers': {'check': {'type': 'noul', 'noul': .95}}}
        def provider(*args):
            time.sleep(.02)
            return response
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'TYPESAFE_API_KEY': 'fixture-only'}), \
                patch('outreach.s.ask', side_effect=provider) as ask:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: o.cached_ask(request, Path(folder)), range(8)))
            self.assertEqual(ask.call_count, 1)
            self.assertTrue(all(result[0] == response for result in results))


if __name__ == '__main__':
    unittest.main()
