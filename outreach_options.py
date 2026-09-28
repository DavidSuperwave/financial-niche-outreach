"""Explicit B2B adaptations of dashboard motions; not additional proven capabilities.

These fill coverage gaps between broad category membership and the dashboard's
top-15 examples. TypeSafe still has to establish business, role and source fit.
"""
import csv
from pathlib import Path


def expand_catalog(offers, matrix_path):
    with Path(matrix_path).open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.reader(file))
    matches = [(i, row[0]) for i, row in enumerate(rows, 1) if row and
               all(word in row[0].lower() for word in ('b2b', 'referral', 'partnership', 'software-sales'))]
    if len(matches) != 1:
        raise ValueError('Expanded offers require the dashboard introduction describing B2B outreach motions')
    record, source = matches[0]
    additions = {
        'adapt_mortgage_software': (
            'Mortgage technology buyer pipeline',
            'Software or workflow providers explicitly selling to mortgage lenders, brokers or loan officers. Not a lender seeking consumer borrowers.',
            'mortgage lenders and brokerages reviewing their borrower engagement or loan workflow',
            'We could help identify mortgage lenders and brokerages whose workflows fit your platform, qualify the relevant team and timing, and arrange product conversations.'),
        'adapt_brokerage_api': (
            'Brokerage platform partnership outreach',
            'Brokerage or trading infrastructure providers explicitly offering APIs, integrations or a platform partner program to other businesses. Not solely a retail brokerage.',
            'trading platforms evaluating brokerage infrastructure or a new integration',
            'We could help identify trading platforms that fit your API or integration model, qualify the use case and partnership owner, and arrange introductory calls.'),
        'adapt_financial_software': (
            'Financial software buyer pipeline',
            'B2B software companies explicitly selling a financial workflow to banks, lenders, investment firms, advisers or finance teams. Not consumer financial advice or investing.',
            'financial firms evaluating a workflow your software supports',
            'We could help identify financial firms whose workflows fit your software, qualify the use case, decision maker and timing, and arrange product conversations.'),
        'adapt_business_payments': (
            'Business payments customer pipeline',
            'Payment processors, card issuing platforms, merchant services or business payments providers explicitly serving businesses. Not required to be an embedded-payments or payfac platform.',
            'businesses reviewing payment processing or card programs that fit your offering',
            'We could help identify businesses that fit your payment offering, qualify the payment use case and decision maker, and arrange commercial conversations.'),
        'adapt_referral_partners': (
            'Professional referral partner outreach',
            'A financial provider whose own website explicitly describes professional referral relationships, intermediaries, introducers or a referral partner program. Consumer service alone is insufficient.',
            'professional partners aligned with the referral relationships described on your site',
            'We could help identify professional partners that fit your referral model, qualify the relationship fit, and arrange introductory conversations.'),
        'adapt_business_benefits': (
            'Employer benefits pipeline',
            'Benefits advisers, retirement plan providers or brokers explicitly selling benefit or retirement solutions to employers. Not individual retirement planning alone.',
            'employers reviewing the benefits or retirement programs you support',
            'We could help identify employers that fit your benefits offering, qualify the HR or finance owner and review timing, and arrange introductory conversations.'),
        'adapt_commercial_insurance': (
            'Commercial insurance prospecting',
            'Insurance agencies or brokers explicitly serving businesses with commercial coverage or employee benefits. Not personal insurance alone and not software sold to insurers.',
            'businesses in your target classes approaching a coverage or benefits review',
            'We could help identify businesses inside your target classes, qualify coverage fit and review timing, and arrange producer conversations.'),
        'adapt_deal_advisory': (
            'Business owner origination',
            'M&A advisers, business brokers or investment banks explicitly advising business owners on acquisitions or exits. Not general wealth advice, VC investing or public securities trading.',
            'business owners whose company size and sector fit your transaction focus',
            'We could help identify owner led companies inside your transaction focus, qualify ownership and interest in a conversation, and arrange direct owner introductions.'),
    }
    result = dict(offers)
    for key, (name, business, opportunity, pitch) in additions.items():
        result[key] = {'name': name, 'prospect_business': business, 'opportunity': opportunity,
                       'pitch': pitch, 'source_record': record, 'source_niche': 'B2B outreach motions',
                       'source_offer_text': source, 'adaptation': True,
                       'basis': 'Proposed application of the dashboard outreach motion; specific scope must match website evidence.'}
    return result
