import pythonbible as bible
import csv

class Sheath():

    def __init__(self, filename):
        self.filename = filename

    def setFilename(self, filename):
        """Sets the filename of the csv file associated with the sheath."""
        self.filename = filename

    def addPassages(self, passages):
        """Adds new passages if not already present."""
        allPassages = self.getPassages()
        with open(self.filename, "a", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            for reference in passages:
                if reference not in allPassages:
                    writer.writerow([
                        reference.book,
                        reference.start_chapter,
                        reference.start_verse,
                        reference.end_chapter,
                        reference.end_verse,
                        reference.end_book,
                        0, "False"
                    ])

    def removePassages(self, passages):
        rows = []
        for item in passages:
            if item is int:
                rows.append(item)
            else:
                rows.append(self.findPassages([item])[0]+1)
        
        with open(self.filename, 'r') as file:
            lines = file.readlines()

        rows = sorted(set(rows))
        c = 0
        for i in range(len(rows)):
            lines.pop(rows[i-c])
            c += 1

        with open(self.filename, 'w') as file:
            file.writelines(lines)
        

    def getPassages(self):
        """Returns a list of references currently in the sheath."""
        references = []
        with open(self.filename, newline="", encoding="utf-8") as fin:
            reader = csv.reader(fin)
            headers = next(reader, None)  # skip header
            for row in reader:
                row = [(int(item) if item.isnumeric() else item) for item in row]
                references.append(
                    bible.NormalizedReference(
                        bible.Book(row[0]),
                        row[1], row[2], row[3], row[4],
                        bible.Book(row[5]) if isinstance(row[5], int) else None
                    )
                )
        return references  

    def emptySheath(self):
        """Deletes all references in the sheath and resets header."""
        with open(self.filename, "w", newline="", encoding="utf-8") as fout:
            fout.write("Book,StartChapter,StartVerse,EndChapter,EndVerse,EndBook,WIP,Favorite\n")

    def setFavorites(self,passages):
        """Marks the given passages as favorites"""
        rows = []
        for item in passages:
            if item is int:
                rows.append(item)
            else:
                rows.append(self.findPassages([item])[0]+1)

        with open(self.filename, 'r') as file:
            lines = file.readlines()

        for row in rows:
            line = lines[row].split(",")
            line[7] = "True"
            lines[row] = ",".join(line)+"\n"

        with open(self.filename, 'w') as file:
            file.writelines(lines)

    def unsetFavorites(self,passages):
        """Unmarks the given passages as favorites"""
        rows = []
        for item in passages:
            if item is int:
                rows.append(item)
            else:
                rows.append(self.findPassages([item])[0]+1)

        with open(self.filename, 'r') as file:
            lines = file.readlines()

        for row in rows:
            line = lines[row].split(",")
            line[7] = "False"
            lines[row] = ",".join(line)+"\n"

        with open(self.filename, 'w') as file:
            file.writelines(lines)
        

    def findPassages(self,passages):
        """Returns the row numbers of the given list of passages in the sheath"""
        allPassages = self.getPassages()
        rows = []
        for passage in passages:
            try:
                rows.append(allPassages.index(passage))
            except ValueError:
                raise ValueError("Reference is not in the sheath.")
        return rows

    def setMemStatus(self,passages,statuses):
        """Sets the memorization status of the given passages in the sheath.
        Accepts list of statuses either one for each passage or a single one for all passages."""
        rows = []
        for item in passages:
            if item is int:
                rows.append(item)
            else:
                rows.append(self.findPassages([item])[0]+1)

        with open(self.filename, 'r') as file:
            lines = file.readlines()

        if len(statuses) == len(passages):
            for i in range(len(rows)):
                line = lines[rows[i]].split(",")
                line[6] = str(statuses[i])
                lines[rows[i]] = ",".join(line)
        else:
            for row in rows:
                line = lines[row].split(",")
                line[6] = str(statuses[0])
                lines[row] = ",".join(line)

        with open(self.filename, 'w') as file:
            file.writelines(lines)