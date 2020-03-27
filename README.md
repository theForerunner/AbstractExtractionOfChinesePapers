# 中文论文概要提取
## 项目目录结构
- data PDF原文件数据集(需单独下载，不进行同步)
- input: 文件输入
- output: 文件输出
- header_format.json: 论文抽取格式
- ip_pool.csv: 爬虫的代理IP池
- multi_thread_pdf_downloader.py 多线程PDF下载爬虫
- pdf_parser.py: pdf解析器

## 任务说明
- 看懂 pdf_parser.py 的逻辑(目前算法写得有些暴力，请见谅)
- 根据以下要求，优化算法逻辑或者另寻其他解决方案：
    - 测试代码在数据集上的效果
    - 根据不同年份修改处理逻辑
    - 设计实现过滤表格/图片内容的算法
- 可选任务:
    - reference部分的细分提取
    - 提升代码逻辑的简洁性和通用性

## 目前PDF提取的局限性
- 无法处理表格/图片
- 存在部分汉字, 如'最'无法正常提取(提取后缺失)

## Git 使用规范

1. 分支说明
- master分支：稳定的开发分支，切忌**直接往master提交代码**
- develop/***：每个人的开发分支。**请只在自己的功能分支下工作**

2. 初次使用clone仓库
```
git clone git@github.com:theForerunner/AbstractExtractionOfChinesePapers.git
```
3. 在master分支的基础上创建新的开发分支develop/X

```
git checkout master

git checkout -b develop/X
```

4. develop/X开发完成，首先要更新本地master分支
```
git checkout master
git pull origin master
```
5. 切换到develop/X分支，进行rebase操作
```
git checkout develop/X
git rebase master（如果这时候有冲突，只能联系写这部分代码的人，手动合并。）
```
6. 将develop/X推入Github
```
git push origin develop/X
```