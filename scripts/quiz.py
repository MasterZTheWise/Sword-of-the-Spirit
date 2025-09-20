import pythonbible as bible
import re
from pythonbible import Version
from difflib import SequenceMatcher


def quiz(references):
    for reference in references:
        verse = bible.get_verse_text(bible.get_verse_id(reference.book, reference.start_chapter, reference.start_verse))
        verse = re.sub(r'[^\w\s]', '', verse)

    response = input("What is the verse: ")
    response = re.sub(r'[^\w\s]', '', response)
    similarity = SequenceMatcher(None, verse, response).ratio()
    print(f"Similarity: {similarity:.3f}")