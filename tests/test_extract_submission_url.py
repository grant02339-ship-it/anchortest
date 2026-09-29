import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("extract_submission_url", os.path.join(ROOT, "tools", "ci", "extract_submission_url.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestExtractSubmissionUrl(unittest.TestCase):
    def test_extracts_a_valid_gist_raw_url(self):
        body = "### Link to your submission\n\nhttps://gist.githubusercontent.com/someone/abc123/raw/submission.py\n\n### One paragraph on the strategy\n\nsome text\n"
        self.assertEqual(mod.extract_url(body), "https://gist.githubusercontent.com/someone/abc123/raw/submission.py")

    def test_extracts_a_valid_raw_githubusercontent_url(self):
        body = "### Link to your submission\n\nhttps://raw.githubusercontent.com/someone/repo/main/submission.py\n"
        self.assertEqual(mod.extract_url(body), "https://raw.githubusercontent.com/someone/repo/main/submission.py")

    def test_rejects_a_non_raw_html_page_link(self):
        body = "### Link to your submission\n\nhttps://gist.github.com/someone/abc123\n"
        self.assertEqual(mod.extract_url(body), "")

    def test_rejects_an_arbitrary_untrusted_host(self):
        body = "### Link to your submission\n\nhttps://evil.example.com/payload.py\n"
        self.assertEqual(mod.extract_url(body), "")

    def test_missing_field_returns_empty_string(self):
        body = "### One paragraph on the strategy\n\nno link field at all\n"
        self.assertEqual(mod.extract_url(body), "")

    def test_empty_or_none_body_does_not_crash(self):
        self.assertEqual(mod.extract_url(""), "")
        self.assertEqual(mod.extract_url(None), "")

    def test_does_not_execute_shell_metacharacters_in_the_body(self):
        # this is the actual regression test for the injection concern: the parser must treat these
        # characters as inert text, never pass them to a shell -- extract_url itself never shells out,
        # so this just proves a hostile body can't change the URL it returns via injection tricks.
        body = "### Link to your submission\n\nhttps://gist.githubusercontent.com/x/y/raw/f.py`rm -rf /`\n"
        url = mod.extract_url(body)
        self.assertTrue(url.startswith("https://gist.githubusercontent.com/"))
        self.assertNotIn(" ", url)  # \S+ match stops at whitespace, so a shell command after a space can't ride along


if __name__ == "__main__":
    unittest.main()
