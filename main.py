from scripts import quiz, sheath
import pythonbible as bible
import os

def main():
    
    filename =  os.path.dirname(os.path.realpath(__file__))+"\\resources\\verses.csv"
    references = bible.get_references("Matthew 7:1")
    references[0].book.value
    sheath1 = sheath.Sheath(filename)
    sheath1.emptySheath()
    sheath1.addPassages(references)
    sheath1.addPassages(references)
    sheath1.setFavorites(references)
    sheath1.setMemStatus(references,[1])
    quiz.quiz(references)
    return

main()