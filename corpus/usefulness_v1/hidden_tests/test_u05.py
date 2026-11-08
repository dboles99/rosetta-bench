import unittest
from solution import mask_emails


class AcceptanceTests(unittest.TestCase):
    def test_consistent_numbering(self):
        self.assertEqual(mask_emails("a@x.com b@y.org a@x.com"), "<email1> <email2> <email1>")
    def test_no_email(self):
        self.assertEqual(mask_emails("nothing here"), "nothing here")
    def test_plus_and_dots(self):
        self.assertEqual(mask_emails("mail first.last+tag@sub.example.co"), "mail <email1>")
