import pythonbible as bible

class Sheath():

    def __init__(self, filename):
        self.filename = filename

    def setFilename(self, filename):
        self.filename = filename

    def addPassages(self, passages):
        """Accepts list of references and adds them to the sheath"""
        allPassages = self.getPassages()
        fout = open(self.filename,"+a")
        for reference in passages:
            try:
                allPassages.index(reference)
            except ValueError:
                fout.write(",".join([str(reference.book),str(reference.start_chapter),str(reference.start_verse),str(reference.end_chapter),str(reference.end_verse),str(reference.end_book),"0","False"])+"\n")
        fout.close()

    def getPassages(self):
        """Returns list of references currently in the sheath"""
        fin = open(self.filename)
        references = []
        headers = fin.readline()
        for row in fin.readlines():
            row = [(int(item) if item.isnumeric() else item) for item in row.split(",")]
            references.append(bible.NormalizedReference(bible.Book(row[0]),row[1],row[2],row[3],row[4],bible.Book(row[5]) if row[5] is int else None))
        return references
        

    def emptySheath(self):
        """Deletes all references in sheath"""
        fout = open(self.filename,"w+")
        fout.write("Book,StartChapter,StartVerse,EndChapter,EndVerse,EndBook,WIP,Favorite\n")
        fout.close()

    def setFavorites(self,passages):
        """Marks the given passage in the sheath as a favorite"""
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
        """Unmarks the given passage in the sheath as a favorite"""
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
                raise("Reference is not in the sheath.")
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