import os
import re
import json
import string
import numbers

from tika import parser

par_dir = os.getcwd()
input_path = os.path.join(par_dir, 'input')
output_path = os.path.join(par_dir, 'output')
header_format_path = os.path.join(par_dir, 'header_format.json')

journal_list = ['journal_of_software', 'journal_of_computers']
journal_name = journal_list[0]
file_name = 'sample_2.pdf'

pdf_path = os.path.join(input_path, journal_name, file_name)
txt_name = file_name.replace('.pdf', '.txt')
json_name = file_name.replace('.pdf', '.json')
txt_path = os.path.join(output_path, journal_name, txt_name)
json_path = os.path.join(output_path, journal_name, json_name)

punc = string.punctuation + '，。、【 】 “”：；（）《》‘’{}？！⑦()、%^>℃：.”“^-——=&#@￥'


def pdf2text(path, target_path):
    # 使用 tika 将 pdf 提取为 txt

    def clean_line(text):
        # 过滤一行中的非法字符
        return re.sub(u'[^0-9a-zA-Z\u4e00-\u9fa5{}]+'.format(punc), '', text)

    def clean_image(page):
        #过滤图片
        page.reverse()
        isimage = False
        haveimage = False
        index = 0
        while index < (len(page)):
            if (page[index].endswith('. \n')):
                isimage = False
            if (isimage):
                # 删除图片上文字
                del page[index]
                index -= 1
            if (page[index].startswith('Fig')):
                # 删除图片标题英文行
                del page[index]
                # 删除图片标题中文行
                del page[index - 1]
                index -= 2
                isimage = True
                haveimage = True
            index += 1
        page.reverse()
        if (haveimage):
            if not (page[0] == '\n'):
                page.insert(0, '\n')
        return page

    def check_if_header(line):
        # 检测一行是否为页眉

        def get_eval_without_exception(string):
            try:
                return eval(string)
            except Exception:
                None

        try:
            if isinstance(get_eval_without_exception(line[:4]), numbers.Integral) and '软件学报' in line:
                return True
            # 2017 修改 页码可能为2/3/4位数
            if (isinstance(get_eval_without_exception(line.rstrip()[-2:]), numbers.Integral) and line.rstrip()[-3] == ' ') or \
                    (isinstance(get_eval_without_exception(line.rstrip()[-3:]), numbers.Integral) and line.rstrip()[-4] == ' ') or \
                    (isinstance(get_eval_without_exception(line.rstrip()[-4:]), numbers.Integral) and line.rstrip()[-5] == ' '):
                return True
            return False
        except IndexError:
            return False

    raw = str(parser.from_file(pdf_path)['content'].encode('utf-8', errors='ignore').decode())
    # lines = [line + '\n' for line in raw.split('\n')]
    lines = [line + '\n' for line in list(filter(lambda line: line, [clean_line(line) for line in raw.split('\n')]))]

    pages = []
    new_lines = []
    for line in lines:
        if check_if_header(line):
            pages.append(new_lines)
            new_lines = []
        else:
            new_lines.append(line)
    pages.append(new_lines)

    content = ''

    # 通过分页的方式, 去除论文第一页下方的注释
    for index, page in enumerate(pages):
        sections = []
        temp_lines = []
        page = clean_image(page)
        for line in page[1:]:
            if not line.strip():
                if temp_lines:
                    sections.append(''.join(temp_lines))
                    temp_lines = []
            else:
                temp_lines.append(line)
        if index == 0:
            sections = sections[1:-1]
        content += ''.join(sections)
        # content += '{}\n'.format('-'*100)

    with open(target_path, 'w', encoding='utf-8') as fw:
        fw.write(content)
        # fw.writelines([line + '\n' for line in raw.split('\n')])


def txt_parser(path, target_path, header_format_path):
    # 从txt中提取论文内容

    # 加载论文抽取格式, 其中每一项的 'content' 为该项在文本中的开头, 'length'为开头的长度即需要去掉的长度
    def header_format_loader(path):
        with open(path, 'r', encoding='utf-8') as fp:
            header_mapper = eval(''.join(fp.readlines()))
        return header_mapper

    headers = header_format_loader(header_format_path)
    header_key_list = list(headers.keys())
    info = {}

    # 读取 PDF 提取结果
    with open(path, 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    line_ptr = 0
    line_count = len(lines)

    citation_url = ''
    content_start = 0

    # 分别提取各部分信息
    info['title'] = lines[0].strip()
    info['authors'] = re.sub('[0-9,]+', ' ', re.sub(r'[\s]+', '', ''.join(lines[1:3]))).split()
    for index, key in enumerate(header_key_list):
        while not lines[line_ptr].startswith(headers[key]['content']):
            line_ptr += 1
        line_start = line_ptr
        try:
            if key == 'citation_en':
                # 由于与中文的引用一样, 以 URL 结尾, 检测完整URL是否存在
                while not ''.join(lines[line_start:line_ptr]).replace('\n', '').strip()[-len(citation_url):] == citation_url:
                    line_ptr += 1
            elif key == 'keywords_en':
                # 由于英文的关键词在中文正文的最上方, 因此检测下一行是否有中文(过滤掉英文及标点符号后不为空)
                while not re.sub(r'[0-9a-zA-Z:;\-\s]+', '', lines[line_ptr]):
                    line_ptr += 1
                content_start = line_ptr
            elif key == 'references':
                # 由于reference紧跟正文内容, 因此检测到 "References" 后提取正文, 剩下的部分目前都归到 references 中
                info['content'] = ''.join([re.sub(r'[\s]+', '', line) for line in lines[content_start:line_ptr]])
                line_ptr = line_count + 1
            else:
                while not lines[line_ptr].startswith(headers[header_key_list[index + 1]]['content']):
                    line_ptr += 1
        except IndexError:
            line_ptr += 1
        info[key] = ''.join([line.strip() for line in lines[line_start:line_ptr]])[headers[key]['length']:]
        if key == 'citation':
            # 提取中文引用中的 url
            citation_url = info[key][info[key].find('http'):]
        elif key in ['keywords', 'keywords_en']:
            # 切分关键词
            info[key] = info[key].replace('; ', ';').split(';')

    with open(target_path, 'w', encoding='utf-8') as fw:
        json.dump(info, fw, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    pdf2text(pdf_path, txt_path)
    txt_parser(txt_path, json_path, header_format_path)
