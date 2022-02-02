from lib.models import session, Disk
from lib.parsers import hosts
import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.utils.cell import get_column_letter

class Inventory():
    def __init__(self):
        self.equipment = session.query(Disk).all()
        self.hosts = hosts()

    def report(self):
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "Инвентаризация жестких дисков"
        head = ('Сервер', 'Имя', 'Объем', 'Описание', 'Производитель', 'Продукт', 'Серийный №')
        sheet.append(head)
        for col in range(len(head)):
            sheet.cell(1, col+1).fill = PatternFill(fgColor="00FF00", fill_type="solid")
            sheet.column_dimensions[get_column_letter(col+1)].width = 20
        row = 2
        for disk in self.equipment:
            sheet.cell(row=row, column=1).value = self.hosts[disk.ip]
            col = 2
            for param in ('name', 'size', 'description', 'vendor', 'product', 'serial'):
                sheet.cell(row=row, column=col).value = getattr(disk, param)
                col += 1
            row += 1
        book.save("reports/inventory.xlsx")