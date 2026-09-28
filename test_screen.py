import copy
import unittest
from unittest.mock import patch

import screen as s


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {"cross_domain_redirect": False, "pages": [{"url": "https://example.com", "text": "We manufacture wooden furniture for homes and hotels. " * 12}]}
        self.request = s.make_request("example.com", ["Example"], self.evidence, {"categories": s.CATEGORIES}, "jev-latest")
        self.response = {"model": "fixture", "answers": {
            "identity": {"type": "noul", "noul": .99},
            "sufficient": {"type": "noul", "noul": .99},
            "outside": {"type": "noul", "noul": .99},
            "category": {"type": "choice", "choice": "NO_MATCH", "confidence": .99,
                         "probabilities": {k: float(k == "NO_MATCH") for k in self.request["questions"]["category"]["criteria"]}},
            "evidence": {"type": "choice", "choice": "E01", "confidence": .99,
                         "probabilities": {k: float(k == "E01") for k in self.request["questions"]["evidence"]["criteria"]}},
        }}

    def test_clear_outside(self):
        s.validate_response(self.response, self.request)
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "OUT_OF_NICHE")

    def test_review_overrides_exclusion(self):
        for key, value in [("identity", .89), ("sufficient", .89), ("outside", .89)]:
            with self.subTest(key=key):
                response = copy.deepcopy(self.response)
                response["answers"][key]["noul"] = value
                self.assertEqual(s.decide(self.evidence, self.request, response)["screen_status"], "REVIEW")
        self.evidence["cross_domain_redirect"] = True
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "REVIEW")

    def test_missing_quote_cannot_exclude(self):
        self.response["answers"]["evidence"]["choice"] = "NONE"
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "REVIEW")

    def test_financial_business_not_excluded(self):
        category = "Banking & Credit Unions"
        answer = self.response["answers"]["category"]
        answer.update(choice=category, probabilities={k: float(k == category) for k in answer["probabilities"]})
        self.response["answers"]["outside"]["noul"] = .01
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "POTENTIAL_FIT")
        self.response["answers"]["outside"]["noul"] = .99
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "REVIEW")

    def test_malformed_response(self):
        self.response["answers"]["identity"]["noul"] = float("nan")
        with self.assertRaises(ValueError):
            s.validate_response(self.response, self.request)

    def test_overlapping_financial_categories_still_retained(self):
        answer = self.response["answers"]["category"]
        answer.update(choice="Banking & Credit Unions", confidence=.4,
                      probabilities={k: 0.0 for k in answer["probabilities"]})
        answer["probabilities"].update({"Banking & Credit Unions": .55, "Payments & Fintech": .4, "REVIEW": .05})
        self.response["answers"]["outside"]["noul"] = .04
        self.assertEqual(s.decide(self.evidence, self.request, self.response)["screen_status"], "POTENTIAL_FIT")

    def test_extract_script_free_source_text(self):
        parser = s.PageParser()
        parser.feed('<html><title>Company</title><script>bad()</script><style>.no {}</style><p>We make chairs &amp; tables.</p><a href="/about">About</a></html>')
        parser.flush()
        self.assertIn("We make chairs & tables.", parser.lines)
        self.assertNotIn("bad()", " ".join(parser.lines))
        self.assertEqual(parser.links, [("/about", "About")])

    def test_normalization_and_private_address_rejection(self):
        self.assertEqual(s.domain_of("https://WWW.example.com/path"), "example.com")
        with patch("screen.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))]):
            with self.assertRaises(ValueError):
                s.public_url("http://example.com")

    def test_cache_changes_with_evidence_and_policy(self):
        old_hash = s.digest(self.request)
        self.request["state"]["policy"] += " New rule."
        self.assertNotEqual(old_hash, s.digest(self.request))
        old_hash = s.digest(self.request)
        self.request["state"]["website_excerpts"]["E01"]["text"] += " New offering."
        self.assertNotEqual(old_hash, s.digest(self.request))


if __name__ == "__main__":
    unittest.main()
