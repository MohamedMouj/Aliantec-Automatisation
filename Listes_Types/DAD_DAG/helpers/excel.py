import openpyxl


class excel:
    def _init_(self, filename):
        self.filename=filename
    


    def load(self):
        self.wb=openpyxl.load_workbook(self.filename)
        