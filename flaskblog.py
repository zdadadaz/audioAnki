### Example inspired by Tutorial at https://www.youtube.com/watch?v=MwZwr5Tvyxo&list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH
### However the actual example uses sqlalchemy which uses Object Relational Mapper, which are not covered in this course. I have instead used natural sQL queries for this demo. 

from flask import Flask, render_template, url_for, flash, redirect,request
from forms import RegistrationForm, BlogForm
import sqlite3
import shlex, subprocess
import pandas as pd
import mysql.connector
import random
from datetime import timedelta
from util import json_io
from functools import wraps
import requests
from newsapi import NewsApiClient
import numpy as np

# Init
newsapi = NewsApiClient(api_key='22947e3bd0e3484aacaa95a9f14c9779')

# url = ('https://newsapi.org/v2/everything?'
#        'q=Apple&'
#        'sortBy=popularity&'
#        'language=en&'
#        'apiKey=22947e3bd0e3484aacaa95a9f14c9779')

# r = requests.get(url)
# print(r.json()) 

conn = sqlite3.connect('blog.db')
app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

config = {
  'user': 'root',
  'password': 'root',
  'unix_socket': '/Applications/MAMP/tmp/mysql/mysql.sock',
  'database': 'Anki',
  'raise_on_warnings': True,
}
# conn = mysql.connector.connect(**config)
currentUser={"currentSid": [], "adjtime": 0, "lang": "en", "lineNum": 1,"uid":1,"vid":0}
userio = json_io()
userio.save_userid(currentUser)

def addcomma(input):
    return "'"+input+"'"

#Turn the results from the database into a dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_tempInfo(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        currentUser=userio.read()
        return f(*args, **kwargs)
    return decorated_function


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        conn = mysql.connector.connect(**config)
        c= conn.cursor()
        vName= request.form.get('vName')
        vSeason=request.form.get('vSeason')
        vEpisode=request.form.get('vEpisode')
        vlang=request.form.get('vlang')
        vFilename=request.form.get('vFilename')
        if (vName is not None) and (vSeason is not None) and (vEpisode is not None):
            c.execute("SELECT vid FROM Video where vname=%s and season =%s and episode=%s " % (addcomma(vName),addcomma(vSeason),addcomma(vEpisode)) )
            vidExist = c.fetchall()
        print(vidExist)
        upfile = request.files.get('file')
        print(upfile)
        print("print vid=============vidExist===================",vidExist)
        print(not len(vidExist))
        if not len(vidExist):
            query_insert = "INSERT INTO `Video` (`vname`,`lang`,`season`,`episode`,`vfilename`) VALUES ( %s,%s,%s,%s,%s)" % \
                            (addcomma(vName),addcomma(vlang),addcomma(vSeason),addcomma(vEpisode),addcomma(vFilename))
            c.execute(query_insert)
            conn.commit()
            c.execute("SELECT vid FROM Video where vname=%s and season =%s and episode=%s " % (addcomma(vName),addcomma(vSeason),addcomma(vEpisode)) )
            vidExist = c.fetchall()

        if (upfile is not None) and len(vidExist):
            df = pd.read_excel(upfile) 
            dflen = len(df.columns)
            if dflen==4:
                subset = df[['sstime', 'sftime', 'tran','org']]
                query_insert = "insert into Subtitle(sstime,sftime,translation,org,vid) VALUES ("
            elif dflen==3:
                subset = df[['sstime', 'sftime', 'org']]
                query_insert = "insert into Subtitle(sstime,sftime,org,vid) VALUES ("
            tuples = [tuple(x) for x in subset.values]
            for i in range(len(tuples)):
                elementstr = addcomma(str(tuples[i][0]))
                for j in range(1,dflen):
                    elementstr = ' '.join([elementstr, ",", addcomma(str(tuples[i][j]).replace("'","''"))])
                query = query_insert +  elementstr +","+addcomma(str(vidExist[0][0])) +')'
                # print('query->',query)
                c.execute(query)
                conn.commit()     
        else:
            print("no valid vid================================")
        flash(f'Scripts uploaded!', 'success')
        return render_template('upload.html')
    return render_template('upload.html')

@app.route("/")
@app.route("/home")
def home():
    return redirect(url_for('showVideo'))

    # conn = sqlite3.connect('blog.db')

    # #Display all blogs from the 'blogs' table
    # conn.row_factory = dict_factory
    # c = conn.cursor()
    # c.execute("SELECT * FROM blogs")
    # posts = c.fetchall()
    # return render_template('home.html', posts=posts)

@app.route("/replay",methods=['POST'])
@get_tempInfo
def replay():
    title = ('stime','ftime','org','translation')
    clip=['','','','']
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    rangelist =currentUser['currentSid']
    lineNum =currentUser['lineNum']
    # ssid =currentUser['ssid']
    # print(currentUser['currentSid'])
    # print(currentUser['currentSid'] is None)
    # print(not (currentUser['currentSid']))
    # if ssid != '' and ssid is not None and not currentUser['currentSid']:
    #     low = ssid
    #     high = ssid + lineNum
    #     currentUser['currentSid'] = [i for i in range(low,high+1)]
    # else:
        # print(rangelist)
    low = rangelist[0]
    high = rangelist[len(rangelist)-1]
    print(low,high)
    c.execute("SELECT S.*,V.vfilename FROM Subtitle S,Video V where V.vid=S.vid and sid>=%s and sid < %s " % ((str(low)),(str(high))) )
    clip = c.fetchall()
    stime = clip[0][1]
    ftime= clip[len(clip)-1][2]
    durtime = ftime-stime
    print('stime=',stime)

    adjtime = currentUser['adjtime']
    print(adjtime)
    userio.save_userid(currentUser)
    stime = stime + timedelta(seconds = int(adjtime)) 
    print('stime=',stime)
    print('durtime=',durtime)
    command_line="ffplay -ss " + str(stime) +" -t " + str(durtime) +" -autoexit ./static/data/"+ clip[0][6]
    # command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
    args = shlex.split(command_line)
    p = subprocess.Popen(args)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)

@app.route("/playnext",methods=['POST'])
@get_tempInfo
def playnext():
    title = ('stime','ftime','org','translation')
    clip=['','','','']
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    rangelist =currentUser['currentSid']
    lineNum = currentUser['lineNum']
    low = int(rangelist[0])+int(lineNum)
    high = int(rangelist[len(rangelist)-1]) + int(lineNum)
    print("low,high")
    print(low,high)
    currentUser['currentSid'] = [i for i in range(low,high+1)]
    c.execute("SELECT S.*,V.vfilename FROM Subtitle S,Video V where V.vid=S.vid and sid>=%s and sid < %s " % ((str(low)),(str(high))) )
    clip = c.fetchall()
    stime = clip[0][1]
    ftime= clip[len(clip)-1][2]
    durtime = ftime-stime
    print("====next clip====")
    print(clip)
    # adjtime = request.form.get("adjusttime")
    userio.save_userid(currentUser)    
    adjtime = currentUser['adjtime']
    stime = stime + timedelta(seconds = int(adjtime)) 
    print('stime=',stime)
    command_line="ffplay -ss " + str(stime) +" -t " + str(durtime) +" -autoexit ./static/data/"+ clip[0][6]
    # command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
    args = shlex.split(command_line)
    p = subprocess.Popen(args)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)
    
@app.route("/playprev",methods=['POST'])
@get_tempInfo
def playprev():
    title = ('stime','ftime','org','translation')
    clip=['','','','']
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    rangelist =currentUser['currentSid']
    lineNum = currentUser['lineNum']
    low = int(rangelist[0])- int(lineNum) if int(rangelist[0])- int(lineNum)>0 else 0
    high = int(rangelist[len(rangelist)-1])-int(lineNum)
    currentUser['currentSid'] = [i for i in range(low,high+1)]
    c.execute("SELECT S.*,V.vfilename FROM Subtitle S,Video V where V.vid=S.vid and sid>=%s and sid < %s " % ((str(low)),(str(high))) )
    clip = c.fetchall()
    stime = clip[0][1]
    ftime= clip[len(clip)-1][2]
    durtime = ftime-stime
    # adjtime = request.form.get("adjusttime")
    adjtime = currentUser['adjtime']
    stime = stime + timedelta(seconds = int(adjtime)) 
    command_line="ffplay -ss " + str(stime) +" -t " + str(durtime) +" -autoexit ./static/data/"+ clip[0][6]
    # command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
    args = shlex.split(command_line)
    p = subprocess.Popen(args)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)

@app.route("/playmp3",methods=['GET','POST'])
@get_tempInfo
def playmp3():
    title = ('stime','ftime','org','translation')
    clip=['','','','']
    if request.method == 'POST':
        option = request.form.get("lang")
        lineNum = request.form.get("lineNum")
        adjtime = request.form.get("adjusttime")
        vid = request.form.get("vid")
        ssid = request.form.get("ssid")
        # if adjtime is None or adjtime=='':
        #     adjtime=currentUser['adjtime']  
        adjtime = currentUser['adjtime'] if (adjtime is None or adjtime=='') else adjtime
        lineNum = 1 if lineNum =='' or lineNum is None else lineNum
        vid = 0 if vid =='' or vid is None else vid
        option = "en" if option is None or option == '' else option
        currentUser['lang']= option
        currentUser['adjtime']=int(adjtime)
        currentUser['lineNum'] = int(lineNum)
        currentUser['vid'] = int(vid)
        # currentUser['ssid'] = int(ssid)
        userio.save_userid(currentUser)    
        # return redirect(url_for('playmp3'))
        return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)
    # return redirect(url_for('playmp3'))

@app.route("/randplay",methods=[ 'POST'])
@get_tempInfo
def randomplay():
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    
    option = currentUser['lang']
    lineNum = currentUser['lineNum']
    vid = currentUser['vid']
    adjtime = currentUser['adjtime']
    if vid ==0:
        vidquery = ''
    else:
        vidquery = ' and S.vid = ' + addcomma(str(vid))
    print("========================")
    c.execute("SELECT (S.sid) FROM Subtitle S, Video V where S.vid = V.vid and V.lang="+addcomma((option))+ vidquery)
    totclips = c.fetchall()
    totnum = len(totclips)
    randnum = int(random.random()*(totnum-1))
    print("========================")
    # print(totclips)
    print(totnum)
    lineNum = int(lineNum)
    low = randnum if (randnum >=0) else 0
    high = randnum+lineNum if (randnum+lineNum <totnum) else totnum
    print(low,high)
    low = totclips[low][0]
    high = totclips[high][0]
    query = "SELECT S.*,V.adjusttime,V.vfilename FROM Subtitle S,Video V where S.vid=V.vid and S.sid>=%s and S.sid < %s and V.lang=%s" % (addcomma(str(low)),addcomma(str(high)), addcomma((option)))
    c.execute( query + vidquery)
    print(query + vidquery)
    clip = c.fetchall()
    # print(clip)
    title = ('stime','ftime','org','translation')
    stime = clip[0][1]
    ftime= clip[len(clip)-1][2]
    durtime = ftime-stime
    print("------------------------------------")
    print(stime,ftime, ftime-stime)
    print("---------------qq---------------------")
    adjtime = clip[0][6] if (clip[0][6] != 0) else adjtime
    print(adjtime)
    currentUser['currentSid'] = [i for i in range(low,high+1)]
    currentUser['adjtime'] = adjtime
    userio.save_userid(currentUser)
    
    stime = stime + timedelta(seconds = int(adjtime)) 
    command_line="ffplay -ss " + str(stime) +" -t " + str(durtime) +" -autoexit ./static/data/"+ clip[0][7]
    # command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
    args = shlex.split(command_line)
    p = subprocess.Popen(args)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)

@app.route("/startheadplay",methods=[ 'POST'])
@get_tempInfo
def startheadplay():
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    
    option = currentUser['lang']
    lineNum = currentUser['lineNum']
    vid = currentUser['vid']
    adjtime = currentUser['adjtime']
    if vid ==0 or vid is None:
        return redirect(url_for('playmp3'))
    c.execute("SELECT (S.sid),S.sstime,V.adjusttime FROM Subtitle S, Video V where S.vid = V.vid and S.vid="+addcomma(str(vid)) )
    totclips = c.fetchall()
    print(totclips)
    totnum = len(totclips)
    adjtime = totclips[0][2] if (totclips[0][2] != 0) else adjtime
    print(adjtime)
    
    lineNum = int(lineNum)
    for i in range(totnum):
        if totclips[i][1]+timedelta(seconds = int(adjtime)) >timedelta(seconds = int(0)):
            low =i
            high = i+lineNum
            break
    print("low,high")
    print(low,high)
    low = totclips[low][0]
    high = totclips[high][0]
    query = "SELECT S.*,V.adjusttime,V.vfilename FROM Subtitle S,Video V where S.vid=V.vid and S.sid>=%s and S.sid < %s and S.vid=%s" % (addcomma(str(low)),addcomma(str(high)), addcomma(str(vid)))
    c.execute( query )
    clip = c.fetchall()
    # print(clip)
    title = ('stime','ftime','org','translation')
    stime = clip[0][1]
    ftime= clip[len(clip)-1][2]
    durtime = ftime-stime
    print("------------------------------------")
    print(stime,ftime, ftime-stime)
    print("---------------qq---------------------")
    currentUser['currentSid'] = [i for i in range(low,high+1)]
    currentUser['adjtime'] = adjtime
    userio.save_userid(currentUser)
    # error Argument '23:59:55' provided as input filename, but 'day,' was already specified.
    stime = stime + timedelta(seconds = int(adjtime)) 
    print(clip[0][7])
    command_line="ffplay -ss " + str(stime) +" -t " + str(durtime) +" -autoexit ./static/data/"+ clip[0][7]
    # command_line="ffplay -ss 00:01:03 -t 00:00:03 -autoexit ./static/data/Bigbang_s08e01.mp3"
    print(command_line)
    args = shlex.split(command_line)
    p = subprocess.Popen(args)
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)


@app.route("/showVideo/<string:vid>/edit", methods=['GET', 'POST'])
def editVideo(vid):
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    c.execute("SELECT * FROM Video V where vid="+addcomma(vid))
    video = c.fetchone()
    if request.method == 'POST':
        vName= request.form.get('vName')
        vSeason=request.form.get('vSeason')
        vEpisode=request.form.get('vEpisode')
        vlang=request.form.get('vlang')
        adjtime=request.form.get('adjtime')
        filename=request.form.get('filename')
        query_insert = 'UPDATE Video SET vname='+addcomma(vName)+',lang='+addcomma(vlang) \
        +',season='+ addcomma(vSeason) +',episode='+addcomma(vEpisode) +',adjusttime='+ \
         addcomma(adjtime) + ',vfilename='+addcomma(filename) +' WHERE vid='+(str(vid))
                    # + ',vfilename='+addcomma(filename)+' WHERE vid='+(str(vid))
        c.execute(query_insert)
        conn.commit()
        
        return redirect(url_for('showVideo'))
    return render_template('editVideo.html',video=video)
    
@app.route("/showVideo", methods=['GET', 'POST'])
def showVideo():
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    c.execute("SELECT * FROM Video V")
    titles=['vid','vname','lang','season','episode','adjusttime','filename']
    videos = c.fetchall()
    return render_template('showVideo.html',titles=titles,videos=videos)

@app.route("/showVideo/<string:vid>", methods=['POST'])
def Video_delete(vid):
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    query= 'DELETE FROM Video WHERE vid='+str(vid)
    c.execute(query) #Execute the query
    conn.commit() #Commit the changes
    return redirect(url_for('showVideo'))

@app.route("/showList", methods=['GET'])
@get_tempInfo
def showList():
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    c.execute("SELECT S.*,h.vocid FROM has h, Subtitle S where S.sid = h.sid and uid ="+str(uid))
    title = ('stime','ftime','org','translation','vid','vocid')    
    scripts = c.fetchall()
    return render_template('showList.html',titles=title,scripts=scripts)

@app.route("/showList/<string:vocidSid>", methods=['POST'])
def voc_delete(vocidSid):
    vocidSid = vocidSid.split('-')
    vocid = vocidSid[0]
    sid = vocidSid[1]
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    query= 'DELETE FROM Voclist WHERE vocid='+str(vocid)+' and uid = '+str(uid)
    print("uid ============",query)
    
    c.execute(query) #Execute the query
    query= 'DELETE FROM has WHERE vocid='+str(vocid)+' and uid = '+str(uid) + ' and sid = '+str(sid)
    c.execute(query) #Execute the query
    conn.commit() #Commit the changes
    return redirect(url_for('showList'))

@app.route("/showList/clear", methods=['POST'])
def voc_delete_all():
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    query= 'DELETE FROM Voclist WHERE uid = '+str(uid)
    print("uid ============",query)
    
    c.execute(query) #Execute the query
    query= 'DELETE FROM has WHERE uid = '+str(uid)
    c.execute(query) #Execute the query
    conn.commit() #Commit the changes
    return redirect(url_for('showList'))

@app.route("/addlist/<string:sid>", methods=['POST'])
@get_tempInfo
def addToList(sid):
    conn = mysql.connector.connect(**config)
    c= conn.cursor()
    uid= currentUser['uid']
    c.execute("SELECT MAX(vocid) FROM Voclist WHERE uid="+addcomma(str(uid)))
    numVoc = c.fetchone()
    print("-=================numVoc=========")
    print(numVoc[0])
    print(type(numVoc[0]))
    numVoc = int(numVoc[0])+1 if numVoc[0] is not None else 1
    print(numVoc)
    print(uid)
    print(sid)
    query_insert = "INSERT INTO `Voclist` (`uid`,`vocid`) VALUES ( %s,%s)" % \
                        ((str(uid)),(str(numVoc)))
    c.execute(query_insert)
    query_insert = "INSERT INTO `has` (`uid`,`vocid`,`sid`) VALUES ( %s,%s,%s)" % \
                        ((str(uid)),(str(numVoc)),(str(sid)))
    c.execute(query_insert)
    conn.commit() #Commit the changes
    
    title = ('stime','ftime','org','translation')
    rangelist =currentUser['currentSid']
    low = rangelist[0]
    high = rangelist[len(rangelist)-1]
    c.execute("SELECT S.*,V.vfilename FROM Subtitle S,Video V where V.vid=S.vid and sid>=%s and sid < %s " % ((str(low)),(str(high))) )
    clip = c.fetchall()
    return render_template('playmp3.html',titles=title, scripts=clip,curInfo=currentUser)

@app.route("/output", methods=['POST'])
@get_tempInfo
def output():
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    c.execute("SELECT S.org, S.translation FROM has h, Subtitle S where S.sid = h.sid and uid ="+str(uid))
    scripts = c.fetchall()
    df = pd.DataFrame(scripts)
    df.columns = ["org","translation"]
    print(df)
    df.to_excel("./output/output.xlsx",index = False,index_label=None)
    return redirect(url_for('showList'))

@app.route("/wordlist", methods=['GET', 'POST'])
@get_tempInfo
def wordlist():
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    titles = ('uid','wid','word','org_exp','trans_exp','phrase','language')
    c.execute("SELECT * FROM WordBank where uid ="+str(uid))
    words = c.fetchall()
    if request.method == 'POST':
        c.execute("SELECT MAX(wid) FROM WordBank WHERE uid="+addcomma(str(uid)))
        numVoc = c.fetchone()
        numVoc = int(numVoc[0])+1 if numVoc[0] is not None else 1
        wid = numVoc
        wName = request.form.get("wName")
        org_exp = request.form.get("org_exp")
        tran_exp = request.form.get("tran_exp")
        phrase = request.form.get("phrase")
        lang = request.form.get("lang")
        org_exp = org_exp.replace("'","''")
        phrase = phrase.replace("'","''")
            
        query_insert = "INSERT INTO `WordBank` (`uid`,`wid`,`wName`,`org_exp`,`tran_exp`,`phrase`,`lang`) VALUES ( %s,%s,%s,%s,%s,%s,%s)" % \
                            ((str(uid)),(str(wid)),addcomma(str(wName)),addcomma(str(org_exp)),addcomma(str(tran_exp)),addcomma(str(phrase)),addcomma(str(lang)))
        c.execute(query_insert)
        conn.commit() #Commit the changes
        return redirect(url_for('wordlist'))    
    return render_template('wordlist.html',words=words,titles=titles)

@app.route("/wordlist/<string:wid>", methods=['POST'])
def word_delete(wid):
    conn = mysql.connector.connect(**config)
    c = conn.cursor()
    uid = currentUser['uid']
    query= 'DELETE FROM WordBank WHERE wid='+str(wid)+' and uid = '+str(uid)
    c.execute(query) #Execute the query
    conn.commit() #Commit the changes
    return redirect(url_for('wordlist'))

@app.route("/wordtest", methods=['GET', 'POST'])
@get_tempInfo
def wordtest():
    articles=()
    if request.method == 'POST':
        lang = request.form.get("lang")
        conn = mysql.connector.connect(**config)
        c = conn.cursor()
        uid = currentUser['uid']
        c.execute("SELECT wid FROM WordBank where uid="+addcomma(str(uid)) +" and lang="+addcomma(lang))
        totclips = c.fetchall()
        totnum = len(totclips)
        choices = np.random.choice(totnum, 3)
        ind = int(choices[0])
        ind = totclips[ind][0]
        c.execute("SELECT * FROM WordBank where uid="+addcomma(str(uid)) +" and wid="+addcomma(str(ind)))
        word = c.fetchone()
        sourcelist='reddit-r-all,new-scientist,national-geographic,espn,buzzfeed,bbc-sport,abc-news-au,abc-news,\
        bbc-news,the-verge,reuters,techcrunch,time,the-new-york-times,the-economist'
        all_articles = newsapi.get_everything(q=word[2],
                                    #   sources=sourcelist,
                                      language=lang,
                                      sort_by='relevancy',
                                      page=1)
        url = 'https://newsapi.org/v2/everything?qInTitle='+word[2]+'&sort_by=relevancy&page=1&apiKey=22947e3bd0e3484aacaa95a9f14c9779'
        test11 = requests.get(url)
        data = test11.json()
        print(data['articles'][0]['title'])
        # check if the vocabulary in the description, make it underline.
        # add description/ image url / article url/ words into html
        # print(all_articles)
        articles=()
        print(all_articles['articles'][0]['title'])
        print(all_articles['articles'][1]['title'])
        
        return render_template('wordtest.html',articles=articles)
    return render_template('wordtest.html',articles=articles)
    # return redirect(url_for('wordtest'))    
    # return render_template('wordtest.html')




@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        conn = sqlite3.connect('blog.db')
        c = conn.cursor()
        
        #Add the new blog into the 'blogs' table
        query = 'insert into users VALUES (' + "'" + form.username.data + "',"  + "'" + form.email.data + "'," + "'" + form.password.data + "'" + ')' #Build the query
        c.execute(query) #Execute the query
        conn.commit() #Commit the changes

        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)


if __name__ == '__main__':
    app.run(debug=True)

