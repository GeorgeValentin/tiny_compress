# -*- coding: utf-8 -*-
import sys
import pickle
import logging
import datetime
import copy
from optparse import OptionParser
import glob
import os

import tinify #pip install --upgrade tinify

def  init_log():
    #设置一下log的配置
    now = datetime.datetime.now()
    #打印到目录下的log文件
    logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='tiny_%s.log'%now.strftime('%Y-%m-%d_%H:%M:%S'),
                    filemode='w'
                    )
    #打印到终端
    #定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def compress_img(path_to_img):
    #将指定的绝对路径的图片压缩至指定目录
    try:
        # Use the Tinify API client.
        source = tinify.from_file(path_to_img)
        source.to_file(path_to_img)
        compressed_img_list.append(path_to_img)
        logging.info("Image compressed:%s remaining %d"%(path_to_img, len(all_img_list) - len(compressed_img_list)))
    except tinify.AccountError, e:
        #print "The error message is: %s" % e.message
        # Verify your API key and account limit.
        logging.warning("Verify your API key and account limit: %s The error message is:%s"%(tinify.key, e.message))
        api_key_dict[tinify.key] = False
    except tinify.ClientError, e:
        # Check your source image and request options.
        logging.warning("Check your source image and request options. %s The error message is:%s"%(path_to_img, e.message))
    except tinify.ServerError, e:
        # Temporary issue with the Tinify API.
        logging.warning("Temporary issue with the Tinify API. The error message is:%s"%e.message)
    except tinify.ConnectionError, e:
        # A network connection error occurred.
        logging.warning("A network connection error occurred. The error message is:%s"%e.message)
    except Exception, e:
        # Something else went wrong, unrelated to the Tinify API.
        logging.warning("Something else went wrong, unrelated to the Tinify API. The error message is:%s"%e.message)

def validate(key):
    #验证API是否可以使用
    try:
        tinify.key = key
        tinify.validate
        return True
    except tinify.Error, e:
        # Validation of API key failed.
        logging.warning("Validation of API key failed: %s"%key)
        return False

def get_imgs_to_compress(root_path):
    #遍历根目录，获取所有图片
    for fn in glob.glob(root_path + os.sep + '*'):
        if os.path.isdir(fn):
                get_imgs_to_compress(fn)
        else:
            if os.path.splitext(fn)[1].lower() in ['.png', '.jpg']:
                all_img_list.append(fn)

def init_parser():
    #设置命令解析需要的参数
    parser = OptionParser(usage="usage:%prog [optinos] ")
    parser.add_option("-n", "--new",
                    action = "store_true",
                    dest = "new",
                    default = False,
                    help="use -n for a new compressing ......"
                    )
    parser.add_option("-r", "--restore",
                    action = "store_true",
                    dest = "restore",
                    default = False,
                    help = "use -r to restart the last compressing, load last compresse data from data.pkl"
                    )
    return parser



api_key_dict = {#去https://tinypng.com申请 API key一个每月最多压500图，多申请几个
    "your tinypng api key":True,
    }

all_img_list = [] #所有需要压缩的图
compressed_img_list = [] #已经压缩过的图
root_path = os.path.abspath('.') #当前目录的绝对路径

if __name__ == '__main__':
    init_log()#初始化log
    parser = init_parser()#初始化命令行解析
    if len(sys.argv) < 2:#如果没有接收到参数,打印使用帮助
      parser.print_help()
      sys.exit(0)

    (options, args) = parser.parse_args()#解析命令行参数

    get_imgs_to_compress(root_path)#递归获取目录下所有图片

    if options.new:#开始一次新的压缩
        compressed_img_list = []
        logging.info("Start a new compressing. All %d images to be compressed."%len(all_img_list))
    elif options.restore:#从上一次压缩中断处继续开始压缩
        if not os.path.exists('data.pkl'):
            pickle.dump([], open('data.pkl', 'wb'))
        pkl_file = open('data.pkl', 'rb')
        compressed_img_list = pickle.load(pkl_file)
        logging.info("Restart last compressing........")
        logging.info("Aleady compressed images number: %d"%len(compressed_img_list))
        logging.info("Need to be compressed images number: %d"%(len(all_img_list) - len(compressed_img_list)))
    else:
        sys.exit(0)
    
    
    try:
        dict_copy = copy.deepcopy(api_key_dict)
        for key, value in dict_copy.iteritems():#循环API key
            if validate(key):#如果tinyPNG网站验证可以使用
                if not api_key_dict[key]:#如果已经超过可以使用的最大压缩图数, 试试下一个API key
                    continue
                img_list = list(set(all_img_list) - set(compressed_img_list)) #过滤掉已经压缩过的图片
                for img in img_list:
                    compress_img(img)
                    if not api_key_dict[key]:#如果已经超过可以使用的最大压缩图数, 试试下一个API key
                        break

        rest_img_list = list(set(all_img_list) - set(compressed_img_list))#循环结束，判断是否有未曾压缩的图片，压缩过程有可能遇到 API key达到最大次数限制，服务器错误，客户端错误，遇到这种情况下次执行命令 -r
        if rest_img_list:
            logging.warning("Image rest to be compressed:%s"%str(rest_img_list))

    except Exception, e:
        logging.warning("Something else went wrong. The error message is:%s"%e.message)
    finally:
        #最后存档已经压缩过的图片，防止下次又要压一遍
        output = open('data.pkl', 'wb')
        pickle.dump(compressed_img_list, output)
        output.close()