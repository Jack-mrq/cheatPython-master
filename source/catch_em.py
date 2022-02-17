# -*- coding: utf-8 -*-
import docx
import os
import jieba
import time
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import prettytable as pt
from scipy.stats import kstest
from docx import Document
from io import StringIO
from io import open
from win32com import client as wc
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFResourceManager, process_pdf
 

def read_docx(file_dir):
    """
    file_dir:文档路径
    读文件, 返回文档字典，格式 文本名字 :内容"
    """
    files_dic = {}
    #key为文件名，value为文件内容
    for root, dirs, files in os.walk(file_dir):
        if len(files) < 2:
            print("Must specify at least 2 files.")
            os._exit(0)
            #退出程序
        for file in files:
            print(file)
            if os.path.splitext(file)[1] == '.docx' or os.path.splitext(file)[1] == '.doc':
                if os.path.splitext(file)[1] == '.doc':
                    word = wc.Dispatch("Word.Application")
                    doc = word.Documents.Open(os.path.join(root, file))
                    doc.SaveAs(root+"\\"+os.path.splitext(file)[0]+".docx", 12)
                    file_path = root+"\\"+os.path.splitext(file)[0]+".docx"
                    doc.Close()
                    word.Quit()
                #读取docx文档
                else:
                    file_path = os.path.join(root, file)
                data = docx.Document(file_path)
                file_text = ""
                #用循环按照段落把内容写到file_text中
                for para in data.paragraphs:
                    file_text = file_text + para.text
                files_dic[os.path.splitext(file)[0]] = file_text
                
            elif os.path.splitext(file)[1] == '.pdf':
                #读取pdf文档
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as pdf:
                    rsrcmgr = PDFResourceManager()
                    retstr = StringIO()
                    laparams = LAParams()
                    # device
                    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
                    process_pdf(rsrcmgr, device, pdf)
                    device.close()
                    content = retstr.getvalue()
                    retstr.close()
                    # 获取所有行
                    lines = str(content).split("\n")
                    file_text = ""
                    #存储文章内容
                    for line in lines:
                        file_text = file_text + line
                    files_dic[os.path.splitext(file)[0]] = file_text
                    #添加到字典中
    return files_dic

def spilt(string, punc):
    """
    分词并返回一个元组(字典+count(其中字典格式  词项: 词项在文中出现的频率)count是文档中词项的总数目)
    """
    words = jieba.cut(string)
    #进行分词
    word_dic = {}
    #记录
    count = 0
    #去掉标点符号
    for w in words:
        if w in punc:
            continue
        if w in word_dic.keys():
            word_dic[w] += 1
            count += 1
        else:
            word_dic[w] = 1
            count += 1
    combine = (word_dic, count)
    #combine元组, word_dic：词项:频率, count词项总数
    return combine

def n_grams_spilt(string, punc=None, ngram_range=(1,1)):
    tokens = list(jieba.cut(string))
    count = 0
    if punc is not None:
        tokens = [w for w in tokens if w not in punc]
        #去掉停用词
    word_dic = {}
    min_n, max_n = ngram_range
    if max_n != 1:
        n_tokens = len(tokens)
        for n in range(min_n, min(max_n+1, n_tokens + 1)):
            for i in range(n_tokens - n + 1):
                if ("".join(tokens[i:i+n])) in word_dic.keys():
                    word_dic["".join(tokens[i:i+n])] += 1
                    count += 1
                else:
                    word_dic["".join(tokens[i:i+n])] = 1
                    count += 1
    combine = (word_dic, count) 
                
    return combine

def compare_txt(txt1, txt2):
    """
    cheatR中的计算方法: 相同词项总频率/词项总数，其中相同词项的频率 = min(a,b)*2
    """
    same_words = txt1[0].keys() & txt2[0].keys()
    #取相同词项
    #print(same_words)
    total = txt1[1]+txt2[1]
    freq = 0
    for word in same_words:
        temp = 2*(txt1[0][word] if txt1[0][word] < txt2[0][word] else txt2[0][word])
        freq += temp
        #相同词项总频率
    return freq/total
    
def jaccard(txt1, txt2):
    same_words = txt1[0].keys() & txt2[0].keys()
    total_words = txt1[0].keys() | txt2[0].keys()
    return len(same_words) / len(total_words)
    
    
def sum_df(files_spilt):
    """
    计算文档集中有某词项的个数，遍历所有文档，统计个数
    返回 词项:出现此词项的文件名 的字典
    """
    word_df = {}
    #存储词项的df值
    for file in files_spilt.keys():
        for word in files_spilt[file][0].keys():
            #word:文档中的词项
            word_find = set()
            #统计出现word的文件名
            if word in word_df.keys():
                word_df[word].add(file)
            else:
                word_find.add(file)
                word_df[word] = word_find
    return word_df

def cos_compare_txt(word_df, txt1, txt2, length):
    """
    余弦相似度比较方法
    """
    sum_word = txt1[0].keys() | txt2[0].keys()
    #sum_word统计两篇文中所有出现的词项
    temp = {}
    #格式 词项: weight列表(weight1,weight2)
    format_sum1 = 0
    format_sum2 = 0
    #用于余弦归一化操作
    for word in sum_word:
        weight_list = []
        df = len(word_df[word])
        
        idf = (math.log((length/df), 10))
        
        #idf = 1
        #print(idf)
        #idf = log(N/df)
        #tf-idf = (1+logtf)*idf
        if word in txt1[0].keys():
            tf1 = txt1[0][word]
            #词频
        else:
            tf1 = 0
        
        if word in txt2[0].keys():
            tf2 = txt2[0][word]
        else:
            tf2 = 0
        
        if tf1 > 0:
            weight1 = (1+ math.log(tf1, 10))*idf
            #权重计算
        else:
            weight1 = 0
            
        format_sum1 += weight1*weight1
        weight_list.append(weight1)
        
        if tf2 > 0:
            weight2 = (1 + math.log(tf2, 10))*idf
        else:
            weight2 = 0
        
        format_sum2 += weight2*weight2
        weight_list.append(weight2)
        
        temp[word] = weight_list
    # print(temp)
    connection = 0
    format_sum1 = format_sum1 ** 0.5
    format_sum2 = format_sum2 ** 0.5
    
    for word in temp.keys():
        t1 = temp[word][0]
        t2 = temp[word][1]
        
        if format_sum1 != 0:
            c1 = t1/format_sum1
        else:
            c1 = 0
            
        if format_sum2 != 0:
            c2 =  t2/format_sum2
        else:
            c2 = 0

        #余弦归一化
        connection += c1 * c2
        #相似度计算
    
    return connection
    
def print_table(file_matrix, name_list, length):
    tb = pt.PrettyTable()
    tb.field_names = ["Similarity"]+name_list
    for i in range(0, length):
        row = []
        row.append(name_list[i])
        for j in range(0, length):
            if j == i:
                row.append(1)
            elif j < i:
                row.append("")
            else:
                row.append(file_matrix[i][j])
        tb.add_row(row)
    print(tb)
    
def draw(file_matrix, name_list, length, min_connect, max_connect):
    """
    画图，显示在（min_connect, max_connect）范围内的边
    """
    G = nx.Graph()
    for i in range(0, length):
        G.add_node(name_list[i], desc = name_list[i])
    for i in range(0, length):
        for j in range(i+1, length):
            if file_matrix[i][j] >= min_connect and file_matrix[i][j] <=max_connect:
                #筛选
                G.add_edge(name_list[i], name_list[j], weight = file_matrix[i][j])
            else:
                continue
    pos = nx.circular_layout(G)
    nx.draw(G, pos)
    node_labels = nx.get_node_attributes(G, 'desc')
    nx.draw_networkx_labels(G, pos, labels=node_labels)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.show()          

def num_draw(con_dic):
    num_array = list(con_dic.values())
    s = pd.DataFrame(num_array,columns=['value'])
    # 创建自定义图像
    u = s['value'].mean()
    std = s['value'].std()  
    print(u)
    print(std)
    print('scipy.stats.kstest统计检验结果----------------------------------------------------')
    print(kstest(s['value'], 'norm'))
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    fig = plt.figure(figsize=(10, 6))
    # 创建子图1
    ax1 = fig.add_subplot(3,1,1)
    # 绘制散点图
    ax1.set_ylim(u-3*std,u+3*std)
    ax1.scatter(s.index, s.values) 
    plt.grid()      # 添加网格
    
    # 创建子图2
    ax2 = fig.add_subplot(3, 1, 2)
    ax2.set_xlim(u-3*std,u+3*std)
    # 绘制直方图
    s.hist(bins=len(num_array),alpha=0.5,ax=ax2)
    # 绘制密度图
    s.plot(kind='kde', secondary_y=True, ax=ax2)     # 使用双坐标轴
    plt.grid()      # 添加网格
    
    ax3 = fig.add_subplot(3, 1, 3)
    L = sorted(con_dic.items(),key = lambda x:x[1], reverse = True)
    L = L[:5]
    connect = []
    index = []
    for l in L:
        connect.append([l[1]])
        index.append(l[0])
    ax3.table(cellText=connect, colWidths=[0.3]*4, rowLabels=index,loc='center',cellLoc='center')
    ax3.axis('off')
    # 显示自定义图像
    plt.show()
              
def catch(file_dir, min_n = 1, max_n = 2):
    """
    操作流程
    """
    punc = [' ','\n','\x0c','。','','(',')']
    txt_all = read_docx(file_dir)
    #存放读数据产生的数据, 类型是字典,文本名字:内容 
    files_spilt = {}
    files_ngram_spilt = {}
    #存放分词产生的数据, 类型是字典, key是文件名字, value是分词(词典)和count的元组
    for txt_name in txt_all.keys():
        files_spilt[txt_name] = spilt(txt_all[txt_name], punc)
        files_ngram_spilt[txt_name] = n_grams_spilt(txt_all[txt_name], punc, ngram_range=(min_n,max_n))
    name_list = list(files_spilt.keys())
    #列表支持索引, name_list是文件名列表
    # print(files_spilt)
    length = len(name_list)
    file_matrix1 = np.zeros((length,length), dtype = float)
    file_matrix2 = np.zeros((length,length), dtype = float)
    file_matrix3 = np.zeros((length,length), dtype = float)
    file_matrix4 = np.zeros((length,length), dtype = float)
    file_matrix5 = np.zeros((length,length), dtype = float)
    file_matrix6 = np.zeros((length,length), dtype = float)
    con_dic1 = {}
    con_dic2 = {}
    con_dic3 = {}
    con_dic4 = {}
    con_dic5 = {}
    con_dic6 = {}
    #建立一个矩阵
    for i in range(0, length):
        for j in range(i, length):
            if i == j:
                files_weight1 = 1
                files_weight2 = 1
                files_weight3 = 1
                files_weight4 = 1
                files_weight5 = 1
                files_weight6 = 1
            else:
                print(name_list[i], name_list[j])
                files_weight1 = compare_txt(files_spilt[name_list[i]],files_spilt[name_list[j]])
                files_weight2 = compare_txt(files_ngram_spilt[name_list[i]], files_ngram_spilt[name_list[j]])
                files_weight3 = cos_compare_txt(sum_df(files_spilt), files_spilt[name_list[i]],files_spilt[name_list[j]], length)
                files_weight4 = cos_compare_txt(sum_df(files_ngram_spilt), files_ngram_spilt[name_list[i]], files_ngram_spilt[name_list[j]], length)
                files_weight5 = jaccard(files_spilt[name_list[i]],files_spilt[name_list[j]])
                files_weight6 = jaccard(files_ngram_spilt[name_list[i]], files_ngram_spilt[name_list[j]])
                con_dic1[name_list[i]+"&"+name_list[j]] = files_weight1
                con_dic2[name_list[i]+"&"+name_list[j]] = files_weight2
                con_dic3[name_list[i]+"&"+name_list[j]] = files_weight3
                con_dic4[name_list[i]+"&"+name_list[j]] = files_weight4
                con_dic5[name_list[i]+"&"+name_list[j]] = files_weight5
                con_dic6[name_list[i]+"&"+name_list[j]] = files_weight6
            file_matrix1[i][j] = round(files_weight1, 3)
            file_matrix2[i][j] = round(files_weight2, 3)
            file_matrix3[i][j] = round(files_weight3, 3)
            file_matrix4[i][j] = round(files_weight4, 3)
            file_matrix5[i][j] = round(files_weight5, 3)
            file_matrix6[i][j] = round(files_weight6, 3)
    # print(file_matrix)
    # print(sum_df(files_spilt))
    
    #draw(file_matrix, name_list, length, min_connect, max_connect)
    # print_table(file_matrix1, name_list, length)
    # print_table(file_matrix2, name_list, length)
    # print_table(file_matrix3, name_list, length)
    # print_table(file_matrix4, name_list, length)
    # print_table(file_matrix5, name_list, length)
    # print_table(file_matrix6, name_list, length)
    # print(list(con_dic1.values()))
    # print(list(con_dic2.values()))
    # print(list(con_dic3.values()))
    # print(list(con_dic4.values()))
    # print(list(con_dic5.values()))
    # print(list(con_dic6.values()))
    num_draw(con_dic1) 
    num_draw(con_dic2)
    num_draw(con_dic3)
    
    num_draw(con_dic4)
    num_draw(con_dic5)
    num_draw(con_dic6)
    
            
def main():
    # txt_all = read_docx("F:\Desktop\cheatPython-master\\test")
    # for data in txt_all.keys():
    #     print(data)
    #     print(txt_all[data])
    #combine = spilt(txt_all[2])
    #rint(combine[0])
    #print(combine[1])
    catch(r"F:\\Desktop\\cheatPython-master\\test4", 2, 3)


if __name__ == '__main__':
    main()
        