import os
from dataclasses import dataclass

import camelot
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image
from enum import Enum


@dataclass
class PageTable:
    '''
    表格抽取结果类
    '''

    # 页数
    page: int
    # 数据列表
    datas: []
    # 本页文本
    text: str


class ImgOcrType(Enum):
    '''
    图片Ocr类型
    '''

    # 阿里云
    Pytesseract = 1
    Aliyun = 2


def get_page_img_path(pdf: pdfplumber.PDF, page_number: str):
    '''
    : 得到pdf页面转换为图片的路径
    '''
    page_num_str = str(page_number)
    pdf_path = pdf.stream.name
    basename = os.path.basename(pdf_path)
    root_name, ext = os.path.splitext(basename)
    img_path = os.getcwd() + '/tmp/' + root_name + \
        '-page-' + page_num_str + '.png'

    img_path = img_path.replace('\\\\', '/')

    # 目录不存在则建立
    img_dir = os.path.dirname(img_path)
    if os.path.exists(img_dir) == False:
        os.makedirs(img_dir)

    return img_path


def merge_table(all_tables: [PageTable], page_number: int, data, text: str):
    '''
    : 合并表格数据
    '''
    same_tables = [
        table for table in all_tables if table.page == page_number]
    if same_tables:
        same_table = same_tables[0]
        same_table.datas.append(data)
        same_table.text = text
    else:
        all_tables.insert(
            page_number - 1, PageTable(page_number, [data], text))


def merge_tables(all_tables, page_number, other_tables):
    for t in other_tables:
        for data in t.datas:
            merge_table(all_tables, page_number, data, t.text)


def extract_imgbase(pdf: pdfplumber.PDF, page_number: int, flavor: str, lang: str, filter=None, **imgOcrSettings):
    '''
    : 抽取基于图片的pdf
    '''
    print('use ocr extract page {page_number} tables'.format(
        page_number=page_number))

    # 保存图片
    page_img_path = get_page_img_path(pdf, page_number)

    page = pdf.pages[page_number - 1]
    page_img = page.to_image(resolution=300)
    page_img.save(page_img_path, format='PNG')

    page_text = pytesseract.image_to_string(
        page_img_path, lang=lang, config='--psm 11 --dpi 300', nice=1)

    if filter is not None:
        needExtract = filter(page_text, page_number, page_img_path)
        if needExtract == False:
            print('不符合过滤条件，略过')
            return None

    # 处理配置 根据ocr类型，删除无关的配置项
    img_ocr_type = imgOcrSettings.get(
        'img_ocr_type', ImgOcrType.Pytesseract)

    ocr_type_name = img_ocr_type.name

    setting_keys = [k for k in imgOcrSettings.keys(
    ) if k[0: len(ocr_type_name)].lower() != ocr_type_name.lower()]

    for key in setting_keys:
        del imgOcrSettings[key]

    # 得到图片列表处理者
    imgtable = None
    if img_ocr_type == ImgOcrType.Pytesseract:
        import pdf2tables.image_tables as imgtable

    if img_ocr_type == ImgOcrType.Aliyun:
        import pdf2tables.aliyun_tables as imgtable

    datas = imgtable.extract_tables(page_img_path, **imgOcrSettings)

    tables = []
    tables.append(PageTable(page_number, datas, page_text))

    # 删除临时的pdf页面图片
    os.remove(page_img_path)

    return tables


def extract(pdf_path: str, filter=None, flavor='lattice', lang: str = 'eng', **imgOcrSettings):
    '''
    : 抽取pdf中的表格数据
    '''
    pdf = pdfplumber.from_path(pdf_path)
    total_page = len(pdf.pages)

    tables: [PageTable] = []

    # 使用camelot抽取表格
    print('use camelot extract tables')
    camelot_tables = camelot.read_pdf(pdf_path, pages='all',
                                      flavor=flavor, suppress_stdout=False)

    for t in camelot_tables:
        text = pdf.pages[t.page - 1].extract_text()
        merge_table(tables, t.page, t.data, text)

    # 如果抽取完成则返回
    if len(tables) == total_page:
        return tables

    # 否则使用ocr抽取其他页面的表格
    extract_pages = [t.page for t in tables]

    total_page_set = set(range(1, total_page + 1))
    extracted_pages_set = set(extract_pages)

    other_pages = list(total_page_set.difference(extracted_pages_set))

    for page_number in other_pages:
        other_tables = extract_imgbase(
            pdf, page_number, flavor, lang, filter, **imgOcrSettings)

        if other_tables is not None:
            merge_tables(tables, page_number, other_tables)

    pdf.close()

    return tables


def test_filter(page_text, page_number, page_img_path):
    text_arr = [t for t in page_text.split('\n',) if t]
    return text_arr[0].upper() == 'Report of Sugar Export'.upper() and text_arr[1].upper() == 'JANUARY 2010'.upper()


if __name__ == '__main__':

    imgOcrSettings = {
        'pytesseract_kernel': np.ones((4, 4), np.uint8),
        'pytesseract_bin_threshold': 127,
        'pytesseract_iterations': 1,
        'pytesseract_areaRange': [10000, 100000],
        'pytesseract_isDebug': False,
        'pytesseract_border': 10,
        'img_ocr_type': ImgOcrType.Pytesseract,
        'aliyun_appcode': 'a8f41a5f9b664a45af2bc9f58666a17e'
    }

    tables = extract(
        'C:/Work/HxProjects/Wpbs/Crawler/pdf2tables/test_data/Jan-2010.pdf', lang='eng+tha', filter=test_filter, ** imgOcrSettings)

    for t in tables:
        print("page", t.page)
        for i in range(len(t.datas)):
            print('data' + str(i),
                  '************************************************************')
            data = t.datas[i]
            for row in data:
                print(row)
