import unittest
from pathlib import Path
import sys

# Ensure backend path is in sys.path
backend_dir = Path('d:/RAGENG/files (1)/backend').resolve()
sys.path.append(str(backend_dir))

from llm_eval import _keyword_match

class TestKeywordMatch(unittest.TestCase):
    def test_stopword_filtering(self):
        kws = ["the", "air", "supply", "of", "scoping"]
        ans = "scoping air supply"
        self.assertTrue(_keyword_match(kws, ans))

    def test_all_keywords_present(self):
        kws = ["van", "dam", "seyedeh", "sheida", "hosseini"]
        ans = "van dam seyedeh sheida hosseini"
        self.assertTrue(_keyword_match(kws, ans))

    def test_missing_keyword(self):
        kws = ["microjets", "provide", "circulation", "control", "using"]
        ans = "microjets provide"
        self.assertFalse(_keyword_match(kws, ans))

if __name__ == '__main__':
    unittest.main()
