# coding:utf-8
'''
表格生成线条坐标
'''
import cv2
import numpy as np
import os
import pytesseract
import uuid

# 图像切割模块


class cutImage(object):
    def __init__(self, img, **settings):
        '''
        :param img: 输入图像
        :param bin_threshold: 二值化的阈值大小
        :param kernel: 形态学kernel
        :param iterations: 迭代次数
        :param areaRange: 面积范围 单元格的面积大小 此参数决定哪些是单元格，例如:[9000, 100000]
        :param border: 留边大小
        :param show: 是否显示结果图，默认是显示
        :param write: 是否把结果写到文件，默认是写入
        :param lang:ocr识别的语言，例如：'eng+tha'
        '''
        self.img = img

        self.bin_threshold = settings.get('pytesseract_bin_threshold', 127)
        self.kernel = settings.get(
            'pytesseract_kernel', np.ones((4, 4), np.uint8))
        self.iterations = settings.get('pytesseract_iterations', 1)
        self.areaRange = settings.get('pytesseract_areaRange', [10000, 100000])
        self.border = settings.get('pytesseract_border', 10)
        self.isDebug = settings.get('pytesseract_isDebug', False)
        self.lang = settings.get('pytesseract_lang', 'eng')

    def hitTest(self, p, x, y, w, h):
        '''
        : 得到包含在面里的点数组元素
        ：x y w h构成一个面
        '''
        x1 = x
        x2 = x + w
        y1 = y
        y2 = y + h

        px = p['x'] + p['w'] / 2
        py = p['y'] + p['h'] / 2

        return (px >= x1 and px <= x2) and (py >= y1 and py <= y2)

    def draw_points(self, img, pointArr):
        # 在坐标点上画点
        for point in pointArr:
            cv2.circle(
                img, (point['x'] + int(point['w'] / 2), point['y'] + int(point['h'] / 2)), 1, (0, 0, 255), 10)

        # cv2.imshow('point', img)
        cv2.imwrite('bitwiseAnd_point.png', img)
        # cv2.waitKey()

    def get_text(self):
        # 得到mask图和网格图
        mask, joint = detect_table(self.img)
        # 得到交叉点坐标
        pointArr = find_joint_points(joint)
        if pointArr is None:
            return None

        if self.img.shape[2] == 1:  # 灰度图
            img_gray = self.img
        elif self.img.shape[2] == 3:
            img_gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(
            img_gray, self.bin_threshold, 255, cv2.THRESH_BINARY_INV)  # 二值化
        img_erode = cv2.dilate(thresh, self.kernel, iterations=self.iterations)

        contours, hierarchy = cv2.findContours(
            img_erode, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        result = {}
        area_coord_roi = []

        npPointArr = np.array(pointArr)
        row, col = npPointArr.shape
        data = np.empty((row, col), dtype=object)

        for i in range(len(contours)):
            cnt = contours[i]
            area = cv2.contourArea(cnt)
            if area > self.areaRange[0] and area < self.areaRange[1]:
                x, y, w, h = cv2.boundingRect(cnt)
                roi = self.img[y+self.border:(y+h)-self.border,
                               x+self.border:(x+w)-self.border]
                area_coord_roi.append((area, (x, y, w, h), roi))

                text = None
                if self.isDebug == False:
                    text = pytesseract.image_to_string(
                        roi, lang=self.lang, config='--dpi 300')  # 读取文字
                    print('tesseract cell text:', text)

                if self.isDebug:
                    cv2.rectangle(
                        self.img, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # cv2.imshow('cut_img', roi)
                # cv2.waitKey()

                # 根据坐标，将表格值写入数组中
                for row in pointArr:
                    pList = [p for p in row if self.hitTest(p, x, y, w, h)]
                    if len(pList) > 0:
                        firtP = pList[0]
                        cx = firtP['arrX']
                        cy = firtP['arrY']
                        data[cx][cy] = text

                        # None为''
                        for p in pList[1:]:
                            cx = p['arrX']
                            cy = p['arrY']
                            data[cx][cy] = ''

                        # 画点用来debug
                        if self.isDebug:
                            for point in pList:
                                cv2.circle(
                                    self.img, (point['x'] + int(point['w'] / 2), point['y'] + int(point['h'] / 2)), 1, (0, 0, 255), 10)

        if self.isDebug:
            cv2.imshow("marked-image-debug", self.img)
            cv2.imwrite("marked-image-debug.png", self.img)
            cv2.waitKey()

        return data.tolist()


def detect_table(img):
    '''
    : 探测表格，得到网格图和网格坐标点图
    : parame: src_img 原始图像
    : 返回：
    :   mask_img 网格图，由横线和竖线交叉得到的网格图片
    :   joints_img 坐标点图，网格的交点图片
    '''
    if len(img.shape) == 2:  # 灰度图
        gray_img = img
    elif len(img.shape) == 3:
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh_img = cv2.adaptiveThreshold(
        ~gray_img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    h_img = thresh_img.copy()
    v_img = thresh_img.copy()
    scale = 15
    h_size = int(h_img.shape[1] / scale)

    if h_size == 0:
        return None, None

    h_structure = cv2.getStructuringElement(
        cv2.MORPH_RECT, (h_size, 1))  # 形态学因子
    h_erode_img = cv2.erode(h_img, h_structure, 1)

    h_dilate_img = cv2.dilate(h_erode_img, h_structure, 1)
    # cv2.imshow("h_erode",h_dilate_img)
    v_size = int(v_img.shape[0] / scale)
    if v_size == 0:
        return None, None

    v_structure = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, v_size))  # 形态学因子
    v_erode_img = cv2.erode(v_img, v_structure, 1)
    v_dilate_img = cv2.dilate(v_erode_img, v_structure, 1)

    mask_img = h_dilate_img+v_dilate_img
    joints_img = cv2.bitwise_and(h_dilate_img, v_dilate_img)

    # cv2.imshow("joints", joints_img)
    # cv2.imshow("mask", mask_img)
    return mask_img, joints_img


def find_table(img, mask_img, save=False, save_dir=None):
    '''
    : 查找表格
    : parame: img 图片
    : parame: contours
    : 返回 表格数组:
    : x 表格左上顶点的x值
    : y 表格坐上顶点的y值
    : w 表格宽度
    : h 表格高度
    '''
    contours, hierarchy = cv2.findContours(
        mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    tables = []
    for i in range(len(contours)):
        area0 = cv2.contourArea(contours[i])
        if area0 < 20:
            continue

        # =======================查找每个表的关节数====================
        epsilon = 0.1 * cv2.arcLength(contours[i], True)
        approx = cv2.approxPolyDP(contours[i], epsilon, True)  # 获取近似轮廓
        x, y, w, h = cv2.boundingRect(approx)

        table_path = None
        # 保存文件
        if save == True:
            table_img = img[y: y + h, x: x + w]
            if save_dir is None:
                save_dir = os.getcwd() + '/tmp/tables'
            # 临时文件夹不存在则创建
            if os.path.exists(save_dir) == False:
                os.makedirs(save_dir)
            uuid_id = uuid.uuid1()
            table_path = save_dir + '/' + str(uuid_id) + '.png'

            cv2.imwrite(table_path, table_img)

        tables.append({'x': x, 'y': y, 'w': w, 'h': h,
                       'table_path': table_path})

    return tables


def find_joint_points(joint):
    '''
    : 根据joint得到网格图信息
    ：parame: joint 坐标点图片数据
    ：返回：
    ：pointArr：包含坐标点信息的数组
    ：      arrX: 数组中的行索引
    :       arrY: 数组中的列索引
    :       x: x坐标
    :       y: y坐标
    :       w: 宽度
    :       h: 高度
    '''
    ys, xs = np.where(joint > 0)

    if len(xs) == 0 or len(ys) == 0:
        return None

    mylisty = []  # 纵坐标
    mylistx = []  # 横坐标

    # 通过排序，获取跳变的x和y的值，说明是交点，否则交点会有好多像素值值相近，我只取相近值的最后一点
    # 这个10的跳变不是固定的，根据不同的图片会有微调，基本上为单元格表格的高度（y坐标跳变）和长度（x坐标跳变）
    i = 0
    myxs = np.sort(xs)
    for i in range(len(myxs)-1):
        if(myxs[i+1]-myxs[i] > 10):
            mylistx.append(myxs[i])
        i = i+1
    mylistx.append(myxs[i])  # 要将最后一个点加入

    i = 0
    myys = np.sort(ys)
    # print(np.sort(ys))
    for i in range(len(myys)-1):
        if(myys[i+1]-myys[i] > 10):
            mylisty.append(myys[i])
        i = i+1
    mylisty.append(myys[i])  # 要将最后一个点加入

    pointArr = []

    # 循环y坐标，x坐标分割表格
    for i in range(len(mylisty) - 1):
        rowArr = []

        for j in range(len(mylistx) - 1):

            x1 = mylistx[j]
            x2 = mylistx[j + 1]
            y1 = mylisty[i]
            y2 = mylisty[i + 1]

            rowArr.append({'arrX': i, 'arrY': j, "x": x1, "y": y1,
                           'w': x2 - x1, 'h': y2-y1})
            j = j + 1

        pointArr.append(rowArr)
        i = i+1
    return pointArr


def extract_tables(img_path, **settings):
    '''
    抽取表格
    '''
    tables = []

    # 读取图片
    img = cv2.imread(img_path)

    mask, joints = detect_table(img)
    if mask is None or joints is None:
        return []

    # 寻找表格并且保存为图片
    table_images = find_table(img, mask, save=True)

    # 对表格图片进行分割并使用ocr得到文本
    kernel = np.ones((4, 4), np.uint8)

    # 循环表格抓取数据
    for tImg in table_images:
        table_path = tImg['table_path']

        # 切图并识别成表格
        table_img = cv2.imread(table_path)
        data = cutImage(table_img, **settings).get_text()

        if data is not None:
            tables.append(data)

        # 删除临时文件
        os.remove(table_path)

    return tables


if __name__ == '__main__':
    img_path = 'C:/Work/HxProjects/Wpbs/Crawler/pdf2tables/test_data/Jan-2010-page-2-300.png'

    isDebug = False
    # 切图并识别成表格
    settings = {
        'pytesseract_kernel': np.ones((4, 4), np.uint8),
        'pytesseract_bin_threshold': 127,
        'pytesseract_iterations': 1,
        'pytesseract_areaRange': [10000, 100000],
        'pytesseract_isDebug': isDebug,
        'pytesseract_border': 10
    }

    tables = extract_tables(
        img_path, **settings)

    print(len(tables))

    if isDebug == False:
        for data in tables:
            for row in data:
                print(row)
            print('*********************************************************************')
