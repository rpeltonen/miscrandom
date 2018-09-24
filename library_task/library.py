import sys
import os

class Library():
    """Object representation of a library database."""
    
    def __init__(self, library_file=None):
        self.library_file = library_file
        self.books = []
    
    def read_library(self):
        """Read library contents from a file on disk."""
        with open(self.library_file, 'r') as f:
            library_content = f.readlines()
    
        for row in library_content:
            fields = row.split('\t')
            self.add_book(fields[1].strip(), fields[0].strip(), fields[2].strip())
        
        self.sort_books()
    
    def add_book(self, author, title, isbn):
        """Add book to database, check for duplicates."""
        for book in self.books:
            if book['title'] == title and book['author'] == author:
                return False
            
        self.books.append({'author': author, 'title': title, 'isbn': isbn})
        self.sort_books()
        return True
        
    def get_books(self):
        """Return all books in database."""
        return self.books
        
    def get_book(self, title):
        """Find a book by title and return it."""
        for book in self.books:
            if book['title'] == title:
                return book
        return None
    
    def sort_books(self):
        """Sort books by author."""
        self.books = sorted(self.books, key=lambda k: k['author'])

    def list_books(self):
        """Return formatted table of all books in database."""
        row_maxlen = 30
        output = ""
        
        title_row = "%-{maxlen}s%-{maxlen}s%-{maxlen}s\n".format(maxlen=row_maxlen) % ("Title", "Author", "ISBN")
        output += title_row
        output += "".join(["-" for i in range(len(title_row))]) + '\n'
        
        for book in self.books:
            output += "%-{maxlen}s%-{maxlen}s%-{maxlen}s\n".format(maxlen=row_maxlen) % (book['title'], book['author'], book['isbn'])
            
        return output
            
    def save(self):
        """Serialize books database to disk."""
        with open(self.library_file, 'w') as f:
            for book in self.books:
                f.write("%s\t%s\t%s\n" % (book['title'], book['author'], book['isbn']))


def read_input(title):
    """Ask and read input from the user."""
    data = ""
    try:
        while data == "":
            data = raw_input(title)
        return data.replace('\t', '') # sanitize input
    except:
        print "Aborted!\n"

def main(library_file):
    library = Library(library_file)
    library.read_library()
    
    print "Welcome to Library Database!"
    cmd = ""
    while cmd != "Q":
        print "\nOptions:\n1) Add new book to database\n2) List books in database\nQ) Exit\n"
        
        cmd = raw_input("Command: ")
        
        if cmd == "1":
            print "Adding new book to database\n"
            try:
                title = read_input("Title: ")
                author = read_input("Author: ")
                isbn = read_input("ISBN: ")

                if read_input("You are about to enter '%s' by '%s' (ISBN: %s) to the database, are you sure? (Y/N) " 
                              % (title, author, isbn)) in ['y','Y','yes']:
                    if library.add_book(author, title, isbn):
                        library.save()
                    else:
                        print "ERROR: '%s' by '%s' already exists in database." % (title, author)
            except:
                continue
            
        elif cmd == "2":
            print "Listing database contents\n"
            print library.list_books()

if __name__ == '__main__':
    try:
        assert len(sys.argv) > 1, "ERROR: Missing input parameter"
        input_file = sys.argv[1]
        assert os.path.exists(input_file), "ERROR: %s not found" % input_file
    except Exception, ex:
        print str(ex)
        print "\nUsage: python %s <path to library file>" % sys.argv[0]
        sys.exit(1)
    
    main(input_file)
