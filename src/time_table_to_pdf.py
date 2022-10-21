import math

from PIL import ImageFont
from fpdf import FPDF
from fpdf.enums import Align


class HebrewTimeTablePDF(FPDF):
    __hebrew_chars = '()אבגדהוזחטיכלמנסעפצקרשתםךףץן '
    __font = ImageFont.truetype("david.ttf", 10)

    def __init__(self, time_table_data, *args, **kwargs):
        super().__init__(*args, orientation='L', **kwargs)
        self.add_page()
        self.add_font("David", "", "david.ttf")
        self.set_font("David", size=10)
        self.set_title("time table")
        self.start_x, self.start_y = self.get_x(), self.get_y()
        self.draw_time_table(time_table_data)

    @staticmethod
    def __hebrew_fixer(text: str, max_width) -> str:
        new_text = []
        for line in text.split('\n'):
            new_text.append('')
            for word in line.split(' '):
                if not new_text[-1]:
                    new_text[-1] = word
                elif HebrewTimeTablePDF.get_width(new_text[-1] + ' ' + word) < max_width:
                    new_text[-1] += ' ' + word
                else:
                    new_text.append(word)

        new_text = [text for text in new_text][::-1]
        text = '\n'.join(new_text)
        if not text:
            return ''
        text = text[::-1]
        text = ''.join([chr(ord('(') + ord(')') - ord(char)) if char in '()' else char for char in text])
        start = 0
        is_hebrew = text[0] in HebrewTimeTablePDF.__hebrew_chars
        end_text = ''
        for index, char in enumerate(text):
            if (char in HebrewTimeTablePDF.__hebrew_chars) != is_hebrew or char == '\n':
                if is_hebrew:
                    end_text += text[start:index]
                else:
                    if start > 0:
                        end_text += text[index - 1:start - 1:-1]
                    else:
                        end_text += text[index - 1::-1]
                if char == '\n':
                    is_hebrew = '\n'
                else:
                    is_hebrew = char in HebrewTimeTablePDF.__hebrew_chars
                start = index
        if is_hebrew:
            end_text += text[start:]
        else:
            if start == 0:
                end_text += text[::-1]
            else:
                end_text += text[:start - 1:-1]
        return end_text

    @staticmethod
    def get_width(text: str) -> float:
        return HebrewTimeTablePDF.__font.getlength(text) / 2.69

    @staticmethod
    def get_days(time_table_data):
        days = [
            "יום ראשון",
            "יום שני",
            "יום שלישי",
            "יום רביעי",
            "יום חמישי",
            "יום שישי"
        ]
        day_indexer = list(range(1, 7))
        new_days = []
        for day_index in range(len(days)):
            if any(time[1] == day_index for time in time_table_data):
                new_days.append(days[day_index])
            else:
                for i in range(day_index, 6):
                    day_indexer[i] -= 1
        return new_days, day_indexer

    def new_cell(self, x, y, w, h, txt='', fill=False, fill_color=0xffffff, heb=True, **kwargs):
        self.set_fill_color((fill_color >> (2 * 8)) & 0xff,
                            (fill_color >> (1 * 8)) & 0xff,
                            (fill_color >> (0 * 8)) & 0xff)
        self.set_xy(x, y)
        if heb:
            txt = self.__hebrew_fixer(txt, w)
        self.cell(w=w, h=h, txt=txt, fill=fill, align=Align.R, **kwargs)

    def new_multi_cell(self, x, y, w, h, txt='', fill=False, fill_color=0xffffff, heb=True, border=1):
        self.set_fill_color((fill_color >> (2 * 8)) & 0xff,
                            (fill_color >> (1 * 8)) & 0xff,
                            (fill_color >> (0 * 8)) & 0xff)
        self.new_cell(x=x, y=y, w=w, h=h, fill=fill, fill_color=fill_color, border=border)
        self.set_xy(x, y)
        if heb:
            txt = self.__hebrew_fixer(txt, w)
        self.multi_cell(w=w, txt=txt, align=Align.R)

    def draw_time_table(self, time_table_data):
        days, day_indexer = self.get_days(time_table_data)
        colum_width = self.epw / (len(days) + 1)
        line_height = self.font_size * 2.5

        # draw columns
        for index, colum in enumerate(["שעות"] + days):
            self.new_cell(x=self.start_x + colum_width * (len(days) - index),
                          y=self.start_y,
                          w=colum_width,
                          h=self.eph,
                          border=1,
                          fill=True,
                          fill_color=0xAAAAAA)
            self.new_cell(x=self.start_x + colum_width * (len(days) - index),
                          y=self.start_y,
                          w=colum_width,
                          h=line_height,
                          txt=colum,
                          border=1,
                          fill=True)

        self.start_y += line_height
        # draw hours
        min_hour = min(int(data[2]) for data in time_table_data)
        max_hour = max(math.ceil(data[3]) for data in time_table_data)
        hour_high = (self.eph - line_height) / (max_hour - min_hour)

        for i in range(max_hour - min_hour):
            self.new_cell(x=self.start_x + len(days) * colum_width,
                          y=self.start_y + i * hour_high,
                          w=colum_width,
                          h=hour_high,
                          fill=True,
                          border=True,
                          heb=False,
                          txt=f'{str(min_hour + i).zfill(2)}:00 - {str(min_hour + i + 1).zfill(2)}:00')

        # draw data
        for my_class in time_table_data:
            self.new_multi_cell(
                x=self.start_x + (len(days) - day_indexer[my_class[1]]) * colum_width,
                y=self.start_y + (my_class[2] - min_hour) * hour_high,
                w=colum_width,
                h=(my_class[3] - my_class[2]) * hour_high,
                border=True,
                fill=True,
                txt=my_class[0] + '\n\n' + my_class[4] + '\n\n' + my_class[5]
            )

    def get_output(self):
        return bytes(super().output())

