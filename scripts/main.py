import quiz
import pythonbible as bible

def main():
    
    references = bible.get_references("Matthew 7:1")
    quiz.quiz(references)
    return  


main()