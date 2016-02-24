# -* coding: utf8 -*-

from __future__ import unicode_literals
import json
import codecs
import urllib2
import re
import sys
import os
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')


"""
Скрипт для скачивания статей с Хабра и распределения их по
рубрикам и хабам, принятым на Хабре.

"""


def retrieve_hub_links(url, page_number):

    """

    Функция принимает на вход url на хаб и сохраняет
    в список все ссылки на статьи с того количества страниц хаба,
    сколько указано в аргументе page_namber.

    :param url: str
    :param page_number: int
    :return: list
    """

    page_range = range(1, page_number+1)
    posts_urls = []

    for pn in page_range:
        url = url+"page"+str(pn)+"/"
        link_source = urllib2.urlopen(url).read()
        page_urls = re.findall('href="(.*)"\sclass="post_title"', link_source)
        posts_urls += page_urls

    return posts_urls


def index_hubs(page_number=5):

    """
    Функция загружает словарь рубрик, хабов и ссылок на эти хабы из файла hubs.txt.
    Затем пробегает по словарю и формирует вложенные списки ссылок на статьи с хабов.
    В итоге получается список списков вида
    [[категория, [хаб, [ссылки с хаба]]], [категория, [хаб, [ссылки с хаба]]]]
    Сохранение названий категории и хаба необходимо для формирования папок и подпапок на диске,
    куда будут сохранятся скаченные статьи.
    В переменную no_duplicates сохраняются все скаченные ссылки,
    чтобы проверять и удалять дубликаты ссылок на статьи.

    :param page_number: int
    :return: list of nested lists
    """

    # make dict from txt list of habr's hubs
    with codecs.open('hubs.txt', 'r', 'utf8') as hub_list:
        hubs_json = json.loads(hub_list.read())

    no_duplicates = []

    links_all = []

    for Category, Hubs in hubs_json["Hubs"].iteritems():
        print "Processing...", Category
        category_urls = [Category, []]
        for Hub, URL in Hubs.iteritems():
            hub_urls = [Hub, retrieve_hub_links(URL, page_number)]
            copy_hubs = hub_urls[1]
            for d_url in hub_urls[1]:
                if d_url in tuple(no_duplicates):
                    hub_urls[1].remove(d_url)
            no_duplicates += copy_hubs
            category_urls[1].append(hub_urls)
        links_all.append(category_urls)

    return links_all


def dump_index_as_json(urls):

    """

    Скидываем индекс ссылок, полученный функцией index_hubs() в формате json

    :param urls: list of lists
    :return: json
    """

    category_index = {"Categories": urls}

    with open("categories_index.json", 'w') as outfile:
        json.dump(category_index, outfile)


def download_article(url):

    """

    Функция принимает на вход ссылку на статью и ищет в html заголовок и тела статьи по regexp,
    чистит от тегов.

    :param url: str
    :return: str
    """

    try:
        article_html = urllib2.urlopen(url)

    except (urllib2.URLError, urllib2.HTTPError) as urlerror:
        with codecs.open('error_log.txt', 'a', 'utf8') as log:
            log.write(url+'\t'+str(urlerror)+'\n')

    else:

        article_html = article_html.read()

        article_title = re.search('<span class="post_title">(.*)</span>', article_html)

        art_re = re.compile('<div class="content html_format">(.*)\n\s+<div class="clear"></div>\n\s+</div>', re.DOTALL)
        article_body = art_re.search(article_html)

        clean_article = BeautifulSoup(article_body.group(1), 'html.parser').get_text().strip()

        text = article_title.group(1)+'\n\n'+clean_article

        return text


def get_name(url):

    """
    Функция принимает на вход ссылку на статью и выделяет из ссылки номер статьи,
    чтобы под ним статья была сохранена на диск.

    https://habrahabr.ru/post/265075/ === 265075 <-- имя файла на диске

    :param url: str
    :return: str
    """

    last_slash = url.rfind('/')
    prelast_slash = url[:last_slash].rfind('/')
    filename = url[prelast_slash+1:last_slash]+'.txt'

    return filename


def save_to_disk(article, filename, folder, subfolder):

    """
    Функция сохраняет статью на диск с именем filename и по пути root + folder + subfolder.
    root = 'Habrahabr_texts/'
    folder - название категории
    subfolder - название подкатегории

    :param article: str
    :param filename: str
    :param folder: str
    :param subfolder: str
    :return: none
    """

    root = 'Habrahabr_texts/'

    if not os.path.exists(root+folder):
        os.makedirs(root+folder)
    if not os.path.exists(root+folder+'/'+subfolder):
        os.makedirs(root+folder+'/'+subfolder)

    with codecs.open(root+folder+'/'+subfolder+'/'+filename, 'w', 'utf16') as outfile:
        outfile.write(article)


def build_initial_corpus():

    """
    Основная функция для построения корпуса.
    Загружается сформированный ранее индекс ссылок, в цикле на каждую ссылку вызывается:
    1. функция download_article для скачивания статьи по ссылке,
    2. функция get_name для создания имени файла,
    3. функция save_to_disk для сохранения файла на диск.

    :return: none
    """

    with open('categories_index.json', 'r') as in_json:
        index = json.load(in_json)

    for category in index["Categories"]:
        print "Saving category...", category[0]
        for subcategory in category[1]:
            print "\tSaving subcategory...", subcategory[0]
            for link in subcategory[1]:
                article = download_article(link)

                filename = get_name(link)
                print "\t\tSaving article...", filename
                save_to_disk(article, filename, category[0], subcategory[0])


def main():

    # check if index file exists, build corpus
    # if not - make index first.
    if os.path.exists('categories_index.json'):
        print "Corpus index exists. Start to load articles..."
        build_initial_corpus()
    else:
        print "Need to build a corpus index... Wait for indexing completion and restart the script."
        index = index_hubs()
        dump_index_as_json(index)


if __name__ == '__main__':

    main()




# test = build_initial_corpus()
# print test

# with codecs.open('out', 'w', 'utf-8') as out:
#     for category in test:
#         out.write(category[0]+'\n\n')
#         for subcategory in category[1]:
#             out.write(subcategory[0].upper()+':\n')
#             for link in subcategory[1]:
#                 out.write(link+'\n')