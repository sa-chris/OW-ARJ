
import json
import socket
import urllib2
import cookielib
import datetime
from datetime import datetime
from time import sleep, localtime, strftime, time
import _strptime
import threading
import Queue
import random
from operator import itemgetter
import captcha_api
import io
from os import sys
import Mover
import traceback


lock = threading.Lock()

cj = cookielib.CookieJar()
user_agent = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36')
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
opener.addheaders = [('User-agent', user_agent)]

def url_opener(url, p_data=None):
    attempt = 0
    while True:
        try:
            if not p_data:
                request = urllib2.Request(url)
                site = opener.open(request,timeout=3.0)
            else:
                request = urllib2.Request(url, p_data)
                site = opener.open(request, timeout=3.0)
            break
        except IOError:
            #print format('URLError: Site not loading. Retrying...')
            attempt = attempt + 1
            if attempt >= 5:
                checkIfLoggedIn(url)
        except socket.timeout:
            print format('Error: socket timeout (url_opener)')
            pass
        except Exception:
            print format('Unknown error, retrying...')
            print format('Link error = %s' % url)
            checkIfLoggedIn(url)
    return site

def sub_string(source, start, end):
    try:
        return source.split(start)[1].split(end)[0]
    except IndexError:
        print format('Could not retrieve the inbetween value (sub_string())')
        return


def char_name(source):
    try:
        char_name = source.split('" selected>')[1].split('</option>')[0]
    except IndexError:
        char_name = "Unknown"
        print format("Could not retrieve the inbetween value (char_name())")
    finally:
        return char_name

def get_raid_id(source):
    try:
        return sub_string(source, "joinraid.php?raidid=", "&")
    except IndexError:
        print format("Couldn't retrieve raid ID")
        return False

def format(string):
    cur = datetime.now().strftime("[%H:%M:%S.%f")[:-2] + ']'
    writeLog(cur, string)
    return "%s %s" % (cur, string)

def writeLog(time, string):
    with open("Logs/%s.txt" % (USERLOG), 'a') as f:
        f.write("%s %s \n" % (time, string))


SPOTTERS = ''
GODSPOTTED = False
RAIDER_GROUP = ''
STARTINGGROUP = ''
SERVER = "torax"  # server name - sigil or torax
SERVERID = 2  # server id - sigil = 1, torax = 2
USERNAME = '' # username
PASSWORD = '' # password
USERLOG = ''
RAIDERGROUPS = [0,1,2,3,4,5,6,5555,9999]
VPNGROUP = False
VPNIP = ''
GOTOSLEEP = False
STOPRAID = False
NOTLOGGEDIN = False
SPOTTER_TORAX = ''
SPOTTER_SIGIL = ''
TORAXGODS = []
SIGILGODS = []
TORAXRAIDERS = []
SIGILRAIDERS = []

GOD_CHECK_TIME = 0.1

CAPTCHADELAY = 1.6, 2.1 # Raiding values
#CAPTCHADELAY = 2.0, 3.5 # testing values

SKEWFACTOR = 0.95 # < 1.0 means captcha times will skew to be faster
MEAN = ((CAPTCHADELAY[0] + CAPTCHADELAY[1]) / 2) * SKEWFACTOR


# adds delay when submitting captcha to better mimic human speed
def captchaDelay(num, int=False):
    intLow = CAPTCHADELAY[0]
    intHigh = CAPTCHADELAY[1]
    lowValue = MEAN - intLow
    highValue = intHigh - MEAN
    delay = ''
    if 1 <= num <= 2:
        lowSkew = lowValue * 0.1
        delay = random.uniform(intLow, intLow + lowSkew)
    elif 3 <= num <= 20:
        lowSkew = lowValue * 0.1
        highSkew = lowValue * 0.4
        delay = random.uniform(intLow + lowSkew, intLow + highSkew)
    elif 21 <= num <= 80:
        lowSkew = lowValue * 0.4
        highSkew = highValue * 0.6
        delay = random.uniform(intLow + lowSkew, intHigh - highSkew)
    elif 81 <= num < 98:
        lowSkew = highValue * 0.6
        highSkew = highValue * 0.9
        delay = random.uniform(intHigh - highSkew, intHigh - lowSkew)
    elif 98 <= num <= 100:
        highSkew = highValue * 0.9
        delay = random.uniform(intHigh - highSkew, intHigh)
    if int==True:
        #delay = delay * 1.30  #testing value
        delay = delay * 1.10  #'raiding' value
    return delay





def arjSetup():
    # setup threading for arj
    arj_queue = Queue.Queue()
    lock.acquire()
    for bot in SPOTTERS:
        arj_queue.put(bot)
    lock.release()
    threads = []
    for _ in range(len(SPOTTERS)):
        thread = arjClass(arj_queue)
        thread.start()
        threads.append(thread)
    arj_queue.join()
    print format('All threads stopped!')

class arjClass(threading.Thread):
    # core of the arj
    def __init__(self, queue):
        self.queue = queue
        threading.Thread.__init__(self)
    def run(self):
        try:
            self.setup()
            while not GOTOSLEEP and not NOTLOGGEDIN:
                self.Raider()
            self.queue.task_done()
        except:
            # error logging for threading... sys.excepthook doesnt catch threading exceptions
            print format(traceback.format_exc())

    def setup(self):
        # initialize all variables needed
        self.server, self.serverID, self.spotterID = self.queue.get()
        self.spotterURL = 'http://%s.outwar.com/raidtools.php?suid=%s&serverid=%s' % (self.server, self.spotterID, self.serverID)
        self.changeURL = 'http://%s.outwar.com/ajax_changeroomb.php?serverid=%s&suid=' % (self.server, self.serverID)
        self.joinRaidURL = 'http://%s.outwar.com/joinraid.php?serverid=%s&raidid=' % (self.server, self.serverID)
        self.raidMemberURL = 'http://%s.outwar.com/raidmembers.php?raidid=' % (self.server)
        self.FuriousKeyboardSmashing = False
        self.STOPRAID = False
        self.formAttempt = 0
        self.launchAttempt = 0
        self.resultAttempt = 0
        self.grabRaiders()
        self.grabGodList()
    def grabRaiders(self):
        if self.server == 'torax':
            self.raiderList = TORAXRAIDERS
        elif self.server == 'sigil':
            self.raiderList = SIGILRAIDERS
    def grabGodList(self):
        if self.server == 'torax':
            self.godList = TORAXGODS
        elif self.server == 'sigil':
            self.godList = SIGILGODS
    def Spotter(self):
        try:
            global GODSPOTTED, NOTLOGGEDIN
            godspawnpage = url_opener(self.spotterURL).read()
            self.timeCheck()
            if GODSPOTTED and not self.FuriousKeyboardSmashing:
                # workaround for rasppi. will trap non-arj thread here until global updates.
                self.OffThreadLoop()
            for god in self.godList:
                if str(god) in godspawnpage:
                    self.captchaGet()  # pre-load captcha
                    self.GroupUpdater()
                    GODSPOTTED = True # update global to tell other thread to sleep
                    self.FuriousKeyboardSmashing = True # tell this thread to begin raiding
                    print format('***' + god + ' has been spotted on %s!!' % self.server)
                    self.raidTimer = time()
                    self.god = god
            if 'You must be logged in to use this page' in godspawnpage: # is this actually necessary?
                NOTLOGGEDIN = True
            elif not GODSPOTTED:
                sleep(GOD_CHECK_TIME)
        except socket.timeout:
            print format('%s - Socket error occurred during spotting' % self.server)
            pass
    def OffThreadLoop(self):
        print format('%s thread is sleeping...' % self.server)
        while GODSPOTTED and not self.FuriousKeyboardSmashing:
            pass
        print format('%s thread woke up!' % self.server)
        print format('Spotting %s Gods: %s' % (self.server, self.godList))
    # handles raider group rotation based on current time
    def GroupUpdater(self):
        global RAIDER_GROUP
        set1 = datetime.strptime('10:00', '%H:%M')
        set2 = datetime.strptime('12:00', '%H:%M')
        set3 = datetime.strptime('14:00', '%H:%M')
        set4 = datetime.strptime('16:00', '%H:%M')
        set5 = datetime.strptime('18:00', '%H:%M')
        set6 = datetime.strptime('20:00', '%H:%M')
        dnow = datetime.now()
        if dnow.time() > set1.time() and dnow.time() <= set2.time():
            if RAIDER_GROUP == 0:
                RAIDER_GROUP = 2 # 0
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 2:
                RAIDER_GROUP = 5 # 2
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 5:
                RAIDER_GROUP = 0 # 5
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
        elif dnow.time() > set2.time() and dnow.time() <= set3.time():
            if RAIDER_GROUP == 4:
                RAIDER_GROUP = 5 # 4
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 5:
                RAIDER_GROUP = 4 # 2
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
        elif dnow.time() > set3.time() and dnow.time() <= set4.time():
            if RAIDER_GROUP == 0:
                RAIDER_GROUP = 5 # 5
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 2:
                RAIDER_GROUP = 4 # 0
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 4:
                RAIDER_GROUP = 2 # 2
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 5:
                RAIDER_GROUP = 0 # 4
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
        elif dnow.time() > set4.time() and dnow.time() <= set5.time():
            if RAIDER_GROUP == 0:
                RAIDER_GROUP = 2 # 4
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 2:
                RAIDER_GROUP = 0 # 2
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
        elif dnow.time() > set5.time() and dnow.time() <= set6.time():
            if RAIDER_GROUP == 0:
                RAIDER_GROUP = 2 # 2
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 2:
                RAIDER_GROUP = 4 # 4
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 4:
                RAIDER_GROUP = 5 # 0
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 5:
                RAIDER_GROUP = 0 # 5
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
        elif dnow.time() > set6.time():
            if RAIDER_GROUP == 0:
                RAIDER_GROUP = 5 # 5
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
            elif RAIDER_GROUP == 5:
                RAIDER_GROUP = 0 # 0
                print format('Your raider group has been updated to %s (Original = %s)' % (RAIDER_GROUP, STARTINGGROUP))
    def Raider(self):
        global GODSPOTTED
        print format('Spotting %s Gods: %s' % (self.server, self.godList))
        while not self.FuriousKeyboardSmashing and not GOTOSLEEP and not NOTLOGGEDIN:
            # messy, but:
            # FuriousKeyboardSmashing determined by which thread spots god
            # GOTOSLEEP stops threads for nightly sleep function
            # NOTLOGGEDIN stops threads and relogs if sess_id unobtainable
            # if any of the values becomes true, quit spotting and move on to quitting threads, sleeping, or arj.
            self.Spotter()
        if GOTOSLEEP or NOTLOGGEDIN:  # kill thread for bedtime or not logged in
            pass
        elif self.FuriousKeyboardSmashing:  # controls whether to arj or not for thread
            self.assignRaiders()
            if RAIDER_GROUP == 0 or RAIDER_GROUP == 5555:
                if VPNGROUP:
                    self.checkCurrentIP()
                if not self.STOPRAID: # if ip check fails, will not form.
                    self.FormRaid()
                if not self.STOPRAID: # if forming fails, will not proceed to join.
                    self.JoinRaid()
                    self.WaitForFullRaid()
                    self.LaunchControls()
                    print format('Raid completed!')
                else:
                    pass
            else:
                self.raidCheckTime = time()
                if not self.STOPRAID:  # control to include certain raid groups or not, like not having 5 arjs for a 5 man
                    if VPNGROUP:
                        self.checkCurrentIP()
                    while not self.waitForRaid():
                        pass
                    if self.RAIDFORMED and not self.STOPRAID: #second self.STOPRAID added as a vpn safety; will stopraid if ipcheck fails
                        self.JoinRaid()
                        self.LaunchControls()
                        self.getResults()
                        print format('Raid completed!')
                    else:
                        pass
                else:
                    pass
            self.cleanupFunctions()
            sleep(5)  # adding slight delay to ensure defeated god does not show up on spotting page
        else:  # thread that isnt arj'ing follows this
            print format('Unknown error - what happened here?')
    def timeCheck(self):
        global GOTOSLEEP
        d = datetime.strptime('23:50', '%H:%M') # time at which arj goes to sleep for the night
        dnow = datetime.now()
        if dnow.time() > d.time():
            GOTOSLEEP = True
            print format('Stop time reached, %s thread quitting.' % self.server)
    def cleanupFunctions(self):
        global GODSPOTTED
        self.god = ''
        self.raiders = ''
        self.raidSize = ''
        self.godID = ''
        self.formerID = ''
        GODSPOTTED = False
        self.FuriousKeyboardSmashing = False
        self.STOPRAID = False
        self.RAIDFORMED = False
        self.formAttempt = 0
        self.launchAttempt = 0
        self.resultAttempt = 0
    def assignRaiders(self):
        self.info = self.raiderList[self.god]
        self.raiders = self.info['Raiders']
        self.raidSize = str(self.info['RaidSize'])
        self.godID = self.info['ID']
        self.formerID = self.raiders[0]
        if self.raidSize == '5':
            if RAIDER_GROUP == 0:
                #self.joiners = itemgetter(1, 1)(self.raiders)  #
                self.joiners = []  #
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(1, 2, 3, 4)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(4, 3, 2, 1)(self.raiders)
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(2, 3, 1, 4)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(3, 4, 1, 2)(self.raiders)
            if RAIDER_GROUP == 5:
                #self.STOPRAID = True #
		        self.joiners = itemgetter(2, 1, 3, 4)(self.raiders)
            # if RAIDER_GROUP == 6:
            #    self.joiners = itemgetter(2,3,1,4)(self.raiders)
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4)(self.raiders)
        if self.raidSize == '10':
            if RAIDER_GROUP == 0:
                self.joiners = itemgetter(1, 1)(self.raiders) #
                #self.joiners = itemgetter(6, 6)(self.raiders) #
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(9, 5, 8, 4, 7, 3, 6, 2, 1)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(8, 4, 5, 7, 3, 6, 2, 1, 9)(self.raiders)  #
                #self.joiners = itemgetter(9, 5, 2, 8, 7, 6, 4, 3, 1)(self.raiders) #
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(7, 3, 6, 2, 1, 9, 5, 8, 4)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(6, 2, 5, 1, 9, 8, 4, 7, 3)(self.raiders) #
                #self.joiners = itemgetter(8, 4, 1, 2, 3, 5, 6, 7, 9)(self.raiders) #
            if RAIDER_GROUP == 5:
                self.joiners = itemgetter(5, 3, 1, 2, 4, 6, 7, 8, 9)(self.raiders)
                #self.STOPRAID = True
                self.joiners = itemgetter(7, 3, 2, 1, 9, 8, 6, 5, 4)(self.raiders) #

            # if RAIDER_GROUP == 6:
            #    self.joiners = itemgetter(6, 3, 7, 2, 8, 1, 9, 5, 4)(self.raiders)
            # if RAIDER_GROUP == 5555:
            #    self.joiners= itemgetter(1,2,3,4,5,6,7,8,9)(self.raiders)
        if self.raidSize == '15':
            if RAIDER_GROUP == 0:
                #self.joiners = itemgetter(1, 2, 3)(self.raiders) #
                self.joiners = itemgetter(1, 5, 9)(self.raiders)
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(3, 7, 11, 4, 8, 12, 5, 9, 13, 6, 10, 14, 1, 2)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(4, 8, 12, 5, 9, 13, 6, 10, 14, 1, 2, 3, 7, 11)(self.raiders) #
                #self.joiners = itemgetter(2, 6, 10, 13, 14, 1, 3, 4, 5, 7, 8, 9, 11, 12)(self.raiders)
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(5, 9, 13, 6, 10, 14, 1, 2, 3, 7, 11, 4, 8, 12)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(6, 10, 14, 1, 2, 3, 7, 11, 4, 8, 12, 5, 9, 13)(self.raiders) #
                #self.joiners = itemgetter(3, 7, 11, 14, 13, 12, 10, 9, 8, 6, 5, 4, 2, 1)(self.raiders)
            if RAIDER_GROUP == 5:
                #self.STOPRAID = True #
                self.joiners = itemgetter(4, 8, 12, 13, 14, 5, 6, 7, 9, 10, 11, 1, 2, 3)(self.raiders)
                # Add check to see if its a god we realllly want, then can join in on the fun
                # JOINERS = itemgetter(11,12,13,14,1,2,3,4,5,6,7,8,9,10)(RAIDERS)
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)(self.raiders)
        if self.raidSize == '20':
            if RAIDER_GROUP == 0:
                self.joiners = itemgetter(1, 2, 3, 4)(self.raiders)
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 1, 2, 3, 4)(self.raiders)
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(10, 11, 12, 13, 14, 15, 1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 18, 17, 16)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(4, 16, 15, 14, 10, 9, 8, 7, 6, 5, 3, 2, 1, 19, 18, 17, 13, 12, 11)(self.raiders)
            if RAIDER_GROUP == 5:
                self.joiners = itemgetter(4, 16, 15, 14, 10, 9, 8, 7, 6, 5, 3, 2, 1, 19, 18, 17, 13, 12, 11)(self.raiders)
                #self.STOPRAID = True
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19)(self.raiders)
        if self.raidSize == '25':
            if RAIDER_GROUP == 0:
                self.joiners = itemgetter(1, 2, 3)(self.raiders)
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(4, 9, 14, 19, 24, 5, 10, 15, 20, 6, 11, 16, 21, 7, 12, 17, 22, 8, 13, 18, 23, 1, 2, 3)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(5, 10, 15, 20, 24, 6, 11, 16, 21, 7, 12, 17, 22, 8, 13, 18, 23, 1, 2, 3, 4, 9, 14,  19)(self.raiders)
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(6, 11, 16, 21, 24, 7, 12, 17, 22, 8, 13, 18, 23, 1, 2, 3, 4, 9, 14, 19, 5, 10, 15, 20)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(7, 12, 17, 22, 24, 8, 13, 18, 23, 1, 2, 3, 4, 9, 14, 19, 5, 10, 15, 20, 6, 11, 16, 21)(self.raiders)
            if RAIDER_GROUP == 5:
                self.joiners = itemgetter(8, 13, 18, 23, 24, 1, 2, 3, 4, 9, 14, 19, 5, 10, 15, 20, 6, 11, 16, 21, 7, 12, 17,22)(self.raiders)
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24)(self.raiders)
        if self.raidSize== '30':
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,24, 25, 26, 27, 28, 29)(self.raiders)
        if self.raidSize == '50':
            if RAIDER_GROUP == 0:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 47)(self.raiders)
            if RAIDER_GROUP == 1:
                self.joiners = itemgetter(7, 12, 17, 22, 27, 32, 37, 42, 47, 8, 13, 18, 23, 28, 33, 38, 43, 48, 9, 14, 19, 24, 29, 34, 39, 44, 49, 10, 15, 20, 25, 30, 35, 40, 45, 11, 16, 21, 26, 31, 36, 41, 46, 1, 2, 3, 4, 5, 6)(self.raiders)
            if RAIDER_GROUP == 2:
                self.joiners = itemgetter(8, 13, 18, 23, 28, 33, 38, 43, 48, 9, 14, 19, 24, 29, 34, 39, 44, 49, 10, 15, 20, 25, 30, 35, 40, 45, 11, 16, 21, 26, 31, 36, 41, 46, 1, 2, 3, 4, 5, 6, 7, 12, 17, 22, 27, 32, 37, 42, 47)(self.raiders)
            if RAIDER_GROUP == 3:
                self.joiners = itemgetter(9, 14, 19, 24, 29, 34, 39, 44, 49, 10, 15, 20, 25, 30, 35, 40, 45, 11, 16, 21, 26, 31, 36, 41, 46, 1, 2, 3, 4, 5, 6, 7, 12, 17, 22, 27, 32, 37, 42, 47, 8, 13, 18, 23, 28, 33, 38, 43, 48)(self.raiders)
            if RAIDER_GROUP == 4:
                self.joiners = itemgetter(10, 15, 20, 25, 30, 35, 40, 45, 48, 11, 16, 21, 26, 31, 36, 41, 46, 1, 2, 3, 4, 5, 6, 7, 12, 17, 22, 27, 32, 37, 42, 47, 8, 13, 18, 23, 28, 33, 38, 43, 9, 14, 19, 24, 29, 34, 39, 44, 49)(self.raiders)
            if RAIDER_GROUP == 5:
                self.joiners = itemgetter(11, 16, 21, 26, 31, 36, 41, 46, 49, 1, 2, 3, 4, 5, 6, 7, 12, 17, 22, 27, 32, 37, 42, 47, 8, 13, 18, 23, 28, 33, 38, 43, 48, 9, 14, 19, 24, 29, 34, 39, 44, 10, 15, 20, 25, 30, 35, 40, 45)(self.raiders)
            if RAIDER_GROUP == 5555:
                self.joiners = itemgetter(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49)(self.raiders)
    def FormRaid(self):
        if time() > self.raidTimer + 15:
            print format('Unable to form raid.')
            self.STOPRAID = True
        else:
            self.formRaidURL = 'http://%s.outwar.com/formraid.php?suid=%s&serverid=%s&target=M%s' % (self.server, self.formerID, self.serverID, self.godID)
            self.formRaidURL = self.formRaidURL + '&h=' + url_opener("%s" % self.formRaidURL).read().split()[0]
            self.sleepCalc(time())
            print format('finished waiting')
            raidForm = url_opener("%s" % (self.formRaidURL), "&formtime=1&captcha_code=%s" % (self.captcha) + "&submit=Join+this+Raid%21&submit.x=157&submit.y=25&bomb=none")
            formTime = self.capSolveTime
            self.captchaGet() # preload captcha to join next character or to launch
            raidInfo = raidForm.read()
            if "click the \"Launch Raid\" button" in raidInfo:
                self.charName, self.raidID = char_name(raidInfo), get_raid_id(raidInfo)
                print format("***%s formed by %s. (Solve time: %s seconds)" % (self.god, self.charName, formTime))
                joindata = url_opener("%s%s" % (self.changeURL, self.formerID)).read()
                #open('%s - joindata.txt' % (self.god), 'w').write(joindata)
                with open("JoinData/%s.txt" % (self.god), 'a') as f:
                    f.write("%s"% joindata)
            else:
                print format("Incorrect captcha entered on form, retrying...")
                cur = datetime.now().strftime("[%H:%M:%S.%f")[:-2] + ']'
                writeLog(cur,raidInfo)
                self.formAttempt = self.formAttempt + 1
                if self.formAttempt <= 3:
                    self.FormRaid()
                else:
                    print format("TOO MANY UNKNOWN ERRORS EXPERIENCED, QUITTING")
                    self.STOPRAID = True
    def JoinRaid(self):
        for char in self.joiners:
            if self.joinCheck(char):
                if RAIDER_GROUP == 0:
                    print format('FORMER: breaking out of joining...')
                    break
                else:
                    print format('%s already in raid, joining next character...' % (char))
            else:
                joinAttempt = 0
                self.sleepCalc(time())
                charCap = self.captcha
                url_opener('%s%s&suid=%s' % (self.joinRaidURL, self.raidID, char),"captcha_code=%s" % (self.captcha) + "&submit=Join+this+Raid%21&submit.x=0&submit.y=0&join=1")
                joinTime = self.capSolveTime
                self.captchaGet()  # preload captcha to join next character or to launch
                charName = self.charNameFromJoin(char)
                while not charName:
                    if joinAttempt >= 3:
                        print format('Incorrect captcha limit reached, stopping raid.')
                        self.STOPRAID = True
                        break
                    else:
                        joinAttempt = joinAttempt + 1
                        print format("%s captcha, retrying" % (charName))
                        self.sleepCalc(time())
                        url_opener('%s%s&suid=%s' % (self.joinRaidURL, self.raidID, char), "captcha_code=%s" % (self.captcha) + "&submit=Join+this+Raid%21&submit.x=0&submit.y=0&join=1")
                        joinTime = self.capSolveTime
                        self.captchaGet()  # preload next captcha
                        charName = self.charNameFromJoin(char)
                if self.STOPRAID:
                    break
                print format('Joined character: %s (Solve time: %s seconds, Cap: %s)' % (charName, joinTime, charCap))
    def LaunchControls(self):
        ShouldILaunch = True
        print format('Waiting for raid to fill up...')
        while not self.WaitForFullRaid():
            if time() > self.raidTimer + 120:
                print format('Raid has taken too long, aborting launch')
                ShouldILaunch = False
                break
            else:
                pass
        if ShouldILaunch:
            self.sleepCalc(time())
            self.LaunchRaid()
        else:
            pass
    def WaitForFullRaid(self):
        page = url_opener('%s%s' % (self.raidMemberURL, self.raidID)).read()
        if page.find("%s people have joined this raid" % (self.raidSize)) == -1:
            pass
        else:
            print format('Raid full!')
            return True
    def LaunchRaid(self):
        launch = url_opener('http://%s.outwar.com/joinraid.php?suid=%s&captcha_code=%s&raidid=%s&launchraid=yes&x=0&y=0' % (self.server, self.formerID, self.captcha, self.raidID)).read()
        self.captchaGet()
        if "Your raid will launch shortly" in launch:
            raidTime = time() - self.raidTimer
            print format('RAID LAUNCHED! Raid time: %s (Solve time: %s seconds)' % (raidTime, self.capSolveTime))
        elif "error" in launch:
            self.launchAttempt = 0
            while self.launchAttempt <= 3:
                self.launchAttempt = self.launchAttempt + 1
                self.sleepCalc(time())
                print format('launching - attempt #%s' % (self.launchAttempt + 1))
                launch = url_opener('http://%s.outwar.com/joinraid.php?suid=%s&captcha_code=%s&raidid=%s&launchraid=yes&x=0&y=0' % (self.server, self.formerID, self.captcha, self.raidID)).read()
                self.captchaGet()
                if "Your raid will launch shortly" in launch:
                    raidTime = time() - self.raidTimer
                    print format('RAID LAUNCHED! Raid time: %s (Solve time: %s seconds)' % (raidTime, self.capSolveTime))
                    break
                else:
                    pass # what should i do here??
        self.getResults()
    # reads raid result page
    def getResults(self):
        global GODSPOTTED
        result = url_opener('http://%s.outwar.com/raidattack.php?raidid=%s' % (self.server, self.raidID)).read()
        if "has won!" in result:
            print format("SUCCESS! %s defeated" % (self.god))
        elif "has lost!" in result:
            print format("YOU LOST! Retrying %s" % (self.god))
            self.raidTimer = time() # to update the start time of the raid
            GODSPOTTED = False
            self.Raider()
        elif "This mob has already been defeated or you have selected an invalid raid" in result and self.resultAttempt <= 2:
            self.resultAttempt = self.resultAttempt + 1
            sleep(2)
            self.getResults()
        elif "This mob has already been defeated or you have selected an invalid raid" in result and self.resultAttempt > 2:
            # need to figure out a better way to handle this result
            print format('%s has been defeated by another crew.' % (self.god))
        else:
            print('ERROR: Not sure what happened (E:3)')
    def waitForRaid(self):  # NEEDS CLEANING
        joiner_ID = self.joiners[0]
        world = url_opener("%s%s" % (self.changeURL, joiner_ID)).read()
        strGod = '<b>' + self.god + '<\/b>'
        if time() > self.raidCheckTime + 30:
            print format('No raid was ever formed, heading back to spotting...')
            self.RAIDFORMED = False
            return True
        else:
            try:
                self.raidID = world.split(strGod)[1].split("joinraid.php?raidid=")[1].split('\\">')[0]
                print format('Raid spotted!')
                self.RAIDFORMED = True
                return True
            except IndexError:
                print format("No raid formed yet...Refreshing")
                return False
            except:
                print format('Unknown Error - (E:4)')
                print format(world)
                self.RAIDFORMED = False
                return True
    def joinCheck(self,Char):
        char = str(Char)
        charCheck = url_opener('%s%s' % (self.raidMemberURL, self.raidID)).read()
        joinStatus = ''
        if str(char) in charCheck:
            joinStatus = True
        return joinStatus
    def checkJoinedChars(self):
        join = url_opener('%s%s' % (self.raidMemberURL, self.raidID)).read()
        if join.find("%s people have joined this raid" % (self.raidSize)) == -1:
            pass
        else:
            return True
    def charNameFromJoin(self,Char):
        char = str(Char)
        charCheck = url_opener('%s%s' % (self.raidMemberURL, self.raidID)).read()
        try:
            charname = charCheck.split('profile.php?id=%s' % (char))[1].split('</font>')[0].split('\"yellow\">')[1]
            return charname
        except IndexError:
            return False
    def captchaGet(self):
        fd = url_opener('http://%s.outwar.com/phpcatcha/phpcatcha_show.php' % (self.server))
        self.captchaTimer = time()
        image_file = io.BytesIO(fd.read())
        captcha = captcha_api.predict(image_file)
        randomInt = random.randint(1, 100)
        if ContainsInt(captcha):  # if string contains an integer sleep longer
            solve_time = captchaDelay(randomInt, int=True)
        else:
            solve_time = captchaDelay(randomInt)
        self.captcha = captcha.lower()
        self.capSolveTime = solve_time
        #print format('%s, %s, %s' % (self.captcha, self.capSolveTime, intcap))
    def sleepCalc(self, endTime):
        sleepTime = self.capSolveTime - (endTime - self.captchaTimer)
        if sleepTime > 0:
            sleep(sleepTime)
        else:
            pass
    def checkCurrentIP(self):
        curIP = url_opener('http://ident.me').read()
        adjustedVPNIP = VPNIP.split('.')[0:3]
        adjustedcurIP = curIP.split('.')[0:3]
        if adjustedVPNIP == adjustedcurIP:
            print format('Starting IP %s matches current IP of %s' % (VPNIP, adjustedcurIP))
            return True
        else:
            print format('IP Mismatch, stopping join attempt. Starting IP:%s, current IP: %s' % (VPNIP, curIP))
            self.STOPRAID = True
            exit()
            return False


def grabSessID():
    source = url_opener('http://torax.outwar.com/privacy.php').read() # suid, serverid not necessary as this shouldnt force sigil to become torax, will auto-redirect to appropriate server
    try:
        sess_id = source.split('rg_sess_id=')[1].split('\" target=\"_blank\">')[0]
    except IndexError:
        print format('Could not grab session ID - quitting threads and relogging.')
        return False
    else: # if sess id located, returns True
        return True

def checkIfLoggedIn(sourceURL):
    global NOTLOGGEDIN
    if grabSessID():
        pass
        #print format("Checked if we're still logged in... I think we are")
        #print format("URL that triggered this check: %s" % sourceURL)
        #info = sourceURL.read()
        #with open("Logs/ErrorLogs/%s.txt" % (USERLOG), 'a') as f:
            #f.write("%s\n" % info)
    else:
        print format("Don't think we're logged in...")
        print format("URL that triggered this check: %s" % sourceURL)
        #info = sourceURL.read()
        #with open("Logs/ErrorLogs/%s.txt" % (USERLOG), 'a') as f:
            #f.write("%s\n" % info)
        NOTLOGGEDIN = True


def ContainsInt(captchastring):
    return any(char.isdigit() for char in captchastring)

def timeCheck():
    d = datetime.strptime('22:30', '%H:%M') # program will stop for bedtime at this time, based on the time of the computer/VM
    dnow = datetime.now()
    if dnow.time() > d.time():
        snoozeAlarm = random.randint(1, 1800)
        sleepyTime = 27600 + snoozeAlarm
        print format('bed time!  sleeping for %s sec' % sleepyTime)
        sleep(sleepyTime)
        print format('Wakey-wakey! Time to start raiding again!')

def LoadGodList():
    global TORAXGODS, SIGILGODS
    with open("Torax-GodsToSpot.json") as t:
        TORAXGODS = json.load(t)['Gods']
    with open("Sigil-GodsToSpot.json") as s:
        SIGILGODS = json.load(s)['Gods']
    print format('Gods loaded.')

def LoadRaiders():
    global TORAXRAIDERS, SIGILRAIDERS
    with open("Torax-RaiderGroups.json") as t:
        TORAXRAIDERS = json.load(t)
    with open("Sigil-RaiderGroups.json") as s:
        SIGILRAIDERS = json.load(s)
    print format('Raiders loaded.')

def firstLogin():
    global SPOTTER_TORAX, SPOTTER_SIGIL, GOD_CHECK_TIME, USERNAME, PASSWORD, VPNGROUP
    if RAIDER_GROUP == 0:
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 1:
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 2:
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 3:
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 4:  ### VPNGROUP ###
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 5:  ### VPNGROUP ###
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        #VPNGROUP = True
        #VPNCheck()
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 6:
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 5555:
        global CAPTCHADELAY
        USERNAME = ''
        PASSWORD = ''
        SPOTTER_TORAX = ''
        SPOTTER_SIGIL = ''
        GOD_CHECK_TIME = 0.1
        CAPTCHADELAY = 2.5, 3.7  # testing values
        print format('no login info')
        exit()
    elif RAIDER_GROUP == 9999:
        print format('Testing 5 captchas...')
        for x in range(0, 5, 1):
            capTests()
        print format('exiting program, restart to enter raider.')
        exit()
    login = url_opener('http://%s.outwar.com/myaccount.php' % (SERVER), 'login_username=%s&login_password=%s&serverid=%s&suid=%s' % (USERNAME, PASSWORD, SERVERID, SPOTTER_TORAX))
    sleep(2)
    print format('Logged in to RGA %s \n' % (USERNAME))

def setupRaiderGroup():
    global RAIDER_GROUP, STARTINGGROUP
    print format("\n \
        # # # # # # # # # # # \n \
        #   RAIDER GROUPS   # \n \
        # 0 = ...           # \n \
        # 1 = ...           # \n \
        # 2 = ...           # \n \
        # 3 = ...           # \n \
        # # # # # # # # # # # \n \
        # 5555 = solo mode  # \n \
        # 9999 = cap test   # \n \
        # # # # # # # # # # # \n \
                 ")
    print format("Please enter your Raider Group #:")
    RAIDER_GROUP = input()
    while RAIDER_GROUP not in RAIDERGROUPS:
        print format("Invalid raider group entered, please enter a valid integer:")
        RAIDER_GROUP = input()
    print format('Welcome Raider Group %s' % (RAIDER_GROUP))
    STARTINGGROUP = RAIDER_GROUP

def setupLogging():
    global USERLOG
    user = socket.gethostname()
    time = strftime("%H:%M:%S")
    date = strftime("%Y-%m-%d")
    strLog = "\n \n \n \n Log for %s beginning at %s \n" % (date, time)
    USERLOG = user + date
    writeLog(time, strLog)

def createSpotters():
    global SPOTTERS
    SPOTTERS = [('torax','2',SPOTTER_TORAX),('sigil','1',SPOTTER_SIGIL)]

def StartupFunctions():
    global RAIDER_GROUP
    setupLogging()
    # future
    # Ask for input if you're behind a VPN or not? update global to True if you are.
    # But this might be useless, so long as we don't try having a VPN bot starting with group0 or something
    setupRaiderGroup()
    LoadGodList()
    LoadRaiders()
    if RAIDER_GROUP == 0:
        Mover.Main(TORAXGODS, TORAXRAIDERS, SIGILGODS, SIGILRAIDERS)
    firstLogin()
    createSpotters()
    #grabSessID()

def MainFunctions():
    arjSetup()
    timeCheck()
    WakeupFunctions()

def WakeupFunctions():
    global GOTOSLEEP, NOTLOGGEDIN, RAIDER_GROUP
    GOTOSLEEP = False
    NOTLOGGEDIN = False
    RAIDER_GROUP = STARTINGGROUP
    setupLogging() # to update logging to a new file for the day
    LoadGodList()
    LoadRaiders()
    if RAIDER_GROUP == 0:
        Mover.Main(TORAXGODS, TORAXRAIDERS, SIGILGODS, SIGILRAIDERS)
    if VPNGROUP:
        VPNCheck(wakeup=True)
    else:
        wakeupLogin()

def VPNCheck(wakeup=False):
    if wakeup:
        curIP = recheckIP()
        if curIP == VPNIP:
            wakeupLogin()
        else:
            print format('Error occurred with VPN. Starting IP was %s, and current ip is %s. Quitting' % (VPNIP, curIP))
            exit()
    else:
        print format('THIS IS A VPN GROUP. !!!!!!! ENSURE VPN IS CONNECTED BEFORE CONTINUING!!!!!!!')
        if RAIDER_GROUP == 4:
            print format('Ensure Location is .....')
        elif RAIDER_GROUP == 5:
            print format('Ensure location is .....')
        print format('You are located in %s, %s, %s using IP: %s' % (IPLocation()))
        print format('If this IP is correct, press "y" to continue or "n" to exit')
        hardDecision = raw_input().lower()
        while True:
            if hardDecision == 'y':
                print format('Continuing...')
                break
            elif hardDecision == 'n':
                print format('Exiting...')
                exit()
            else:
                print format('Incorrect option. type "y" to continue or "n" to exit. Y u so dumb')
                hardDecision = raw_input().lower()


def recheckIP():
    data = url_opener('http://www.privateinternetaccess.com/pages/whats-my-ip/').read()
    locinfo = data.split('<div class="ipbox-light clearfix">')[1].split('<div id="ipbox-map" class="ipbox-map"></div>')[0]
    common = '<span class="darktext">'
    currentIP = locinfo.split('IP Address:')[1].split('</span>')[0].split(common)[1]
    return currentIP

def IPLocation():
    global VPNIP
    data = url_opener('http://www.privateinternetaccess.com/pages/whats-my-ip/').read()
    locinfo = data.split('<div class="ipbox-light clearfix">')[1].split('<div id="ipbox-map" class="ipbox-map"></div>')[0]
    common = '<span class="darktext">'
    city = locinfo.split('City:')[1].split('</span>')[0].split(common)[1]
    state = locinfo.split('State/Region')[1].split('</span>')[0].split(common)[1]
    country = locinfo.split('Country:')[1].split('</span>')[0].split(common)[1]
    VPNIP = locinfo.split('IP Address:')[1].split('</span>')[0].split(common)[1]
    return city, state, country, VPNIP

def wakeupLogin():
    print format('Welcome back Raider Group %s' % RAIDER_GROUP)
    login = url_opener('http://%s.outwar.com/myaccount.php' % (SERVER),'login_username=%s&login_password=%s&serverid=%s&suid=%s' % (USERNAME, PASSWORD, SERVERID, SPOTTER_TORAX))
    sleep(2)
    print format('Logged in to RGA %s \n' % (USERNAME))

def writeErrorLog(exctype, value, traceback):
    print format('---Error Log---')
    print format('Type: %s' % (exctype))
    print format('Value: %s' % (value))
    print format('Line: %s' % (traceback.tb_lineno))

def capTests():
        fd = url_opener('http://torax.outwar.com/phpcatcha/phpcatcha_show.php')
        image_file = io.BytesIO(fd.read())
        captcha = captcha_api.predict(image_file)
        randomInt = random.randint(1, 100)
        if ContainsInt(captcha):  # if string contains an integer sleep longer
            solve_time = captchaDelay(randomInt, int=True)
        else:
            solve_time = captchaDelay(randomInt)
        captcha = captcha.lower()
        capSolveTime = solve_time
        print format('captcha = %s, "solved" in %s seconds' % (captcha, capSolveTime))
        sleep(capSolveTime)

if __name__ == "__main__":
    sys.excepthook = writeErrorLog
    StartupFunctions()
    while True:
        MainFunctions()
