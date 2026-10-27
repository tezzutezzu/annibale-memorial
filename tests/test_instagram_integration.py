import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import integrate_instagram as integration
import fbstore


def post(pid, text, media=None):
    platform = 'instagram' if pid.startswith('ig_') else 'facebook'
    return {'id': pid, 'platform': platform, 'author': pid, 'text': text,
            'permalink': 'https://example.test/' + pid, 'media': media or []}


class IntegrationTests(unittest.TestCase):
    def test_union_preserves_source_versions_ids_files_and_order(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(integration, 'ROOT', Path(folder)):
            Path(folder, 'same.jpg').write_bytes(b'identical')
            Path(folder, 'copy.jpg').write_bytes(b'identical')
            Path(folder, 'other.jpg').write_bytes(b'another photo')
            facebook = post('fb_1', 'Solo una anteprima…', [{'type': 'image', 'local_path': 'same.jpg'}])
            instagram = post('ig_a', 'Solo una anteprima, seguita dal ricordo completo.',
                             [{'type': 'image', 'local_path': 'copy.jpg'},
                              {'type': 'image', 'local_path': 'other.jpg'},
                              {'type': 'video', 'url': 'https://example.test/video.mp4'}])
            original = copy.deepcopy(facebook)
            integration.merge_record(facebook, instagram)
            self.assertEqual(facebook['id'], 'fb_1')
            self.assertEqual(facebook['aliases'], ['ig_a'])
            self.assertEqual(facebook['text'], instagram['text'])
            self.assertEqual(facebook['sources'][0]['text'], original['text'])
            self.assertEqual(facebook['sources'][1]['text'], instagram['text'])
            self.assertEqual([m['type'] for m in facebook['media']], ['image', 'image', 'video'])
            self.assertEqual(facebook['media'][0]['also_from'][0]['post_id'], 'ig_a')

    def test_generic_similar_text_is_not_automatically_merged(self):
        facebook = post('fb_1', 'Un ricordo per Annibale')
        instagram = post('ig_a', facebook['text'])
        review = {'posts': [{'instagram_id': 'ig_a', 'category': 'citazione_correlata_da_non_fondere'}]}
        rows, report = integration.integrate([facebook], [instagram], review)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(report['facebook_merges']), 0)

    def test_repeat_integration_does_not_add_sources_media_or_posts(self):
        facebook = post('fb_1', 'Un ricordo')
        instagram = post('ig_a', 'Un ricordo completo')
        review = {'posts': [{'instagram_id': 'ig_a', 'category': 'testo_parziale_in_comune', 'facebook_id': 'fb_1'}]}
        rows, _ = integration.integrate([facebook], [instagram], review)
        again, report = integration.integrate(rows, [instagram], review)
        self.assertEqual(again, rows)
        self.assertEqual(report['already_present'], ['ig_a'])

    def test_same_instagram_statement_keeps_two_attributions(self):
        first = post('ig_Dev0CHpo0ON', 'Lo stesso comunicato')
        second = post('ig_DevvSZzs54Z', 'Lo stesso comunicato')
        review = {'posts': [{'instagram_id': p['id'], 'category': 'nessuna_corrispondenza_testuale_rilevata'}
                            for p in (first, second)]}
        rows, report = integration.integrate([], [first, second], review)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['sources']), 2)
        self.assertEqual(rows[0]['aliases'], [second['id']])
        self.assertEqual(len(report['instagram_merges']), 1)

    def test_longer_facebook_text_wins(self):
        facebook = post('fb_1', 'La versione completa su Facebook, con ulteriori ricordi e dettagli.')
        text = facebook['text']
        integration.merge_record(facebook, post('ig_a', 'La versione completa su Facebook'))
        self.assertEqual(facebook['text'], text)
        self.assertEqual(len(facebook['sources']), 2)

    def test_generic_import_finds_a_curated_instagram_alias(self):
        facebook = post('fb_1', 'Un ricordo completo per Annibale')
        instagram = post('ig_a', 'Un ricordo completo per Annibale')
        integration.merge_record(facebook, instagram)
        rows = [facebook]
        report = fbstore.merge_posts(rows, [instagram])
        self.assertEqual(report['appended'], 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], 'fb_1')


if __name__ == '__main__':
    unittest.main()
