import unittest
import library

class TestLibrary(unittest.TestCase):

    def setUp(self):
        self.library = library.Library()

    def test_add_book(self):
        self.assertTrue(self.library.add_book("Test author","Test book","12345"))
        self.assertEquals(self.library.get_book("Test book")['author'], "Test author")

    def test_add_duplicate(self):
        self.assertTrue(self.library.add_book("Test author","Test book","12345"))
        self.assertFalse(self.library.add_book("Test author","Test book","12345"))

    def test_books_are_sorted(self):
        self.library.add_book("Test author B","Test book 2","12345")
        self.library.add_book("Test author A","Test book 1","12345")
        self.assertEquals(self.library.get_books()[0]['author'], "Test author A")
        
    def test_list_books(self):
        self.library.add_book("Test author","Test book","12345")
        self.assertIn("Test book", self.library.list_books())

if __name__ == "__main__":
    unittest.main()