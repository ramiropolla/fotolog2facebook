#!/usr/bin/python
# -*- coding: utf-8 -*-

from lxml import etree
from StringIO import StringIO
import errno, os
import facebook
import urllib2
import json
import sys
import re

# pegue um access token em
# https://developers.facebook.com/tools/explorer
# com os direitos necessários para fazer upload de fotos
access_token = ""
# crie um album no facebook, vá em
# https://developers.facebook.com/tools/explorer/?method=GET&path=me%2Falbums
# e pegue o "id" dele
album_id = ""

if len(sys.argv) < 2:
    print "usage: %s <username> [-download ou -upload]" % sys.argv[0]
    sys.exit(0)

# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

start_upload = True
#start_upload = False
do_download = False
do_upload   = False
if len(sys.argv) > 2:
    if   sys.argv[2] == "-download":
        do_download = True
    elif sys.argv[2] == "-upload":
        do_upload   = True

graph = None
if do_upload:
    graph = facebook.GraphAPI(access_token)

username = sys.argv[1]

mkdir_p(username)
mkdir_p(username+"/mosaic")
mkdir_p(username+"/img")
mkdir_p(username+"/jpg")
mkdir_p(username+"/metadata")

parser = etree.HTMLParser()

meses = { u"janeiro"  :  1,
          u"January"  :  1,
          u"fevereiro":  2,
          u"February" :  2,
          u"março"    :  3,
          u"March"    :  3,
          u"abril"    :  4,
          u"April"    :  4,
          u"maio"     :  5,
          u"May"      :  5,
          u"junho"    :  6,
          u"June"     :  6,
          u"julho"    :  7,
          u"July"     :  7,
          u"agosto"   :  8,
          u"August"   :  8,
          u"setembro" :  9,
          u"September":  9,
          u"outubro"  : 10,
          u"October"  : 10,
          u"novembro" : 11,
          u"November" : 11,
          u"dezembro" : 12,
          u"December" : 12, }

next_url = "http://www.fotolog.com.br/" + username + "/mosaic/"
while True:
    print next_url
    fname = next_url[next_url.find("mosaic/"):]
    if fname[-1] == "/":
        fname = fname + "index"
    fname = username + "/" + fname + ".html"
    if do_download:
        open(fname, "wb").write(urllib2.urlopen(next_url).read())
    mosaic_xml = etree.fromstring(open(fname, "rb").read(), parser)
    for img in mosaic_xml.xpath("//a[@class='wall_img_container']"):
        link = img.get("href")
        print link
        number = re.search("/\d+/", link).group(0)[1:-1]
        fname = username + "/img/" + number + ".html"
        if do_download:
            open(fname, "wb").write(urllib2.urlopen(link).read())
        img_xml = etree.fromstring(open(fname, "rb").read(), parser)

        description = img_xml.xpath("//div[@id='description_photo']")[0]
        try:
            titulo  = description[0].text
            content = description[1]
        except IndexError:
            titulo  = None
            content = description[0]
        descricao = u""
        if content.text:
            descricao = descricao + content.text
        for y in content:
            if y.tag == "br":
                if y.text:
                    descricao = descricao + y.text
                elif y.tail:
                    if y.tail[0:8] == "\nligado ":
                        date = re.match("\nligado (\d+) (\S+) (\d+)", y.tail).groups()
                    else:
                        descricao = descricao + y.tail

        comments = []
        for comment in img_xml.xpath("//div[@class='flog_img_comments']"):
            if comment.get("id"):
                continue
            comment = comment[1]
            comment_str = u""
            for y in comment:
                if   y.tag == "b":
                    poster_name = y[0].text
                    poster_href = y[0].get("href")
                    comment_date = re.match(" ligado (\d+)/(\d+)/(\d+)", y.tail).groups()
                elif y.tag == "br":
                    if y.text:
                        comment_str = comment_str + y.text
                    elif y.tail:
                        comment_str = comment_str + y.tail
            comments.append({"name": poster_name, "href": poster_href, "str": comment_str, "date": comment_date})

        date = { "day": int(date[0]), "month": meses[date[1]], "year": int(date[2]) }
        post = { "title": titulo, "description": descricao, "date": date, "comments": comments }
        fname = username + "/metadata/" + number + ".json"
        open(fname, "wb").write(json.dumps(post))

        jpg = img_xml.xpath("//a[@class='wall_img_container_big']")[0]
        jpg_url = jpg.find("img").get("src")
        fname = username + "/jpg/" + number + ".jpg"
        if do_download:
            open(fname, "wb").write(urllib2.urlopen(jpg_url).read())

        if do_upload:
            message = link + u"\n\n"
            message = message + u"%02d/%02d/%d\n" % ( date["day"], date["month"], date["year"] )
            if titulo:
                message = message + titulo + u"\n\n"
            message = message + descricao
#            if number == "12345678": # se o upload der erro, use o
#                                     # start_upload para decidir de onde
#                                     # começar
#                start_upload = True
            if start_upload:
                graph.put_photo(open(fname), message, album_id)

    next = mosaic_xml.xpath("//div[@id='pagination']")[0][-1]
    if next.text != ">":
        break
    next_url = next.get("href")
