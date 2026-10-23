"""Additive assistance module contract: native schema and canonical vectors."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'taut' / 'src'))
from taut.ir.load import load_schema
from taut.ir.validate import validate_or_raise
from taut.corpus import synth, kit

class AssistanceContract(unittest.TestCase):
    def test_versioned_envelopes_have_canonical_vectors(self):
        schema = load_schema(Path(__file__).resolve().parents[1] / 'ir/assistance.taut.py')
        validate_or_raise(schema)
        vectors = kit.build_corpus(schema, dict(synth.synth_values(schema)))
        self.assertEqual(set(vectors), {'AssistanceIdentity', 'AssistanceAdvertisement', 'AssistanceRequest', 'AssistanceResult'})

if __name__ == '__main__':
    unittest.main()
