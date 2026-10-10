import unittest
from src.gmail_listener import _clean_email_body

class TestGmailListener(unittest.TestCase):
    def test_clean_email_body_with_gmail_quote(self):
        raw_body = "Yes, please process the refund.\n\nOn Mon, Oct 9, 2026 at 10:00 AM, Support <support@pw.live> wrote:\n> We can process your refund. Please confirm."
        cleaned = _clean_email_body(raw_body)
        
        self.assertIn("Yes, please process the refund.", cleaned)
        self.assertIn("--- PREVIOUS THREAD HISTORY ---", cleaned)
        self.assertIn("On Mon, Oct 9, 2026", cleaned)

    def test_clean_email_body_no_history(self):
        raw_body = "Hello, my app is crashing on startup."
        cleaned = _clean_email_body(raw_body)
        
        self.assertEqual(cleaned, "Hello, my app is crashing on startup.")
        self.assertNotIn("--- PREVIOUS THREAD HISTORY ---", cleaned)

    def test_clean_email_body_outlook_style(self):
        raw_body = "I want to transfer my batch.\n\n--- Original Message ---\nFrom: Support\nTo: Student\nSubject: Re: Transfer"
        cleaned = _clean_email_body(raw_body)
        
        self.assertIn("I want to transfer my batch.", cleaned)
        self.assertIn("--- PREVIOUS THREAD HISTORY ---", cleaned)
        self.assertIn("Original Message", cleaned)

if __name__ == "__main__":
    unittest.main()
