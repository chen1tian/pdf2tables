
import sys
import os
import base64
import time
import json

from urllib.parse import urlparse
import traceback
from urllib import request
import base64


class AliyunOcrTableParse:
    def get_img_base64_from_file(self, img_file):
        with open(img_file, 'rb') as infile:
            s = infile.read()
            return self.get_img_base64(s)

    def get_img_base64(self, img_byte):
        byte64 = base64.b64encode(img_byte)
        return str(byte64, encoding="utf-8")

    def predict(self, url, appcode, img_base64, kv_config, old_format):
        if not old_format:
            param = {}
            param['image'] = img_base64
            if kv_config is not None:
                param['configure'] = json.dumps(kv_config)
            body = json.dumps(param)
        else:
            param = {}
            pic = {}
            pic['dataType'] = 50
            pic['dataValue'] = img_base64
            param['image'] = pic

            if kv_config is not None:
                conf = {}
                conf['dataType'] = 50
                conf['dataValue'] = json.dumps(kv_config)
                param['configure'] = conf

            inputs = {"inputs": [param]}
            body = json.dumps(inputs)

        bodyBytes = bytes(body, encoding="utf8")

        headers = {'Authorization': 'APPCODE %s' % appcode}
        requestOjb = request.Request(url=url, headers=headers, data=bodyBytes)
        try:
            response = request.urlopen(requestOjb, timeout=10)
            return response.code, response.headers, response.read()
        except request.HTTPError as e:
            return e.code, e.headers, e.read()

    def parse(self, appcode, img_byte, format='json'):
        url = 'https://form.market.alicloudapi.com/api/predict/ocr_table_parse'
        img_base64data = self.get_img_base64(img_byte)
        # 如果输入带有inputs, 设置为True，否则设为False
        is_old_format = False
        config = {'format': format, 'finance': False, 'dir_assure': False}
        # 如果没有configure字段，config设为None
        # config = None
        stat, header, content = self.predict(
            url, appcode, img_base64data, config, is_old_format)

        contentStr = str(content, 'utf-8')

        if stat != 200:
            err = 'Http status code: ' + str(stat)
            err = err + 'Error msg in header: ' + \
                header['x-ca-error-message'] if 'x-ca-error-message' in header else ''
            err = err + 'Error msg in body: ' + contentStr
            raise Exception(err)
        if is_old_format:
            result_str = json.loads(
                contentStr)['outputs'][0]['outputValue']['dataValue']
        else:
            result_str = contentStr

        return result_str

    # appcode   应用的AppCode
    # img_file  图片路径
    # format    输出的格式 html/json/xlsx
    def extract_tables(self, img_file, **settings):
        appcode = settings.get('aliyun_appcode')

        if appcode is None:
            raise Exception('Aliyun Appcode required')

        format = 'json'
        datas = []

        with open(img_file, 'rb') as infile:
            s = infile.read()
            json_str = self.parse(appcode, s, format)

            json_data = json.loads(json_str)
            # 转化json为list
            for table in json_data['tables']:
                data = []
                for row in table:
                    values = []
                    for col in row:
                        if type(col) is dict:
                            if col['text'] is not None:
                                values.append(col['text'][0])
                            else:
                                values.append('')
                    if len(values) > 0:
                        data.append(values)
                datas.append(data)

        return datas


def extract_tables(img_path, **settings):
    print('extract tables using aliyun ocr...')
    datas = AliyunOcrTableParse().extract_tables(img_path, **settings)
    return datas


if __name__ == "__main__":
    img_path = 'C:/Work/HxProjects/Wpbs/Crawler/pdf2tables/test_data/Jan-2010-page-2-300.png'
    datas = extract_tables(
        img_path, aliyun_appcode='a8f41a5f9b664a45af2bc9f58666a17e')

    for data in datas:
        print('*****************************************')
        for row in data:
            print(row)
