from time import localtime, sleep, strftime, time
import cookielib
import datetime
import Queue
import socket
import threading
import urllib2
import os
import json



lock = threading.Lock()
socket.setdefaulttimeout(10.0)

# login information
rg_sess_id = "" #session id
username = "" # rga username
password = "" # rga password

# GLOBALS
DESTINATIONROOM = ""
PATH = []
CHARS = []
ROOM = ''
TELEPORT = ""
SERVER = "torax"
SERVERID = 2 # 1 for sigil, 2 for torax
BASE_ID = ''  # ... for torax,  nothing for sigil yet.
TORAXCHARS = ''
SIGILCHARS = ''
TORAXGODS = ''
SIGILGODS = ''
MOVEDCHARS = []
FAILEDCHARS = []



MOVE_URL = 'http://%s.outwar.com/ajax_changeroomb.php?room=' % (SERVER)



cj = cookielib.CookieJar()
user_agent = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36')
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
opener.addheaders = [('User-agent', user_agent)]

def format(string):
    cur = strftime("[%H:%M:%S]", localtime(time()))
    return "%s %s" % (cur, string)

def char_name(source):
    try:
        char_name = source.split('" selected>')[1].split('</option>')[0]
    except IndexError:
        char_name = "Unknown"
        print format("Could not retrieve the inbetween value (char_name())")
    finally:
        return char_name

def sub_string(source, start, end):
    try:
        return source.split(start)[1].split(end)[0]
    except IndexError:
        print format('2Could not retrieve the inbetween value')
        return


def url_opener(url, p_data=None):
    while True:
        try:
            if not p_data:
                site = opener.open(url)
            else:
                site = opener.open(url, p_data)
            break
        except IOError:
            print format('URLError: Site not loading. Retrying...')
            login()
        except Exception:
                print format('Unknown error, retrying...')
    return site

def LoadCharacters():
    global TORAXCHARS, SIGILCHARS
    with open("Torax-RaiderGroups.json") as t:
        TORAXCHARS = json.load(t)
    with open("Sigil-RaiderGroups.json") as s:
        SIGILCHARS = json.load(s)
    print format('Characters loaded.')

def LoadGods():
    global TORAXGODS, SIGILGODS
    with open("Torax-GodsToSpot.json") as t:
        TORAXGODS = json.load(t)
    with open("Sigil-GodsToSpot.json") as s:
        SIGILGODS = json.load(s)
    print format('Gods loaded.')

def moveTorax():
    global SIZE, ROOM, PATH, TELEPORT, SERVER, SERVERID, MOVEDCHARS
    SERVER = 'torax'
    SERVERID = '2'
    for god in TORAXGODS:
        attempt = 0
        torax = TORAXCHARS[god]
        chars, SIZE, ROOM, PATH, TELEPORT = torax['Raiders'], str(torax['RaidSize']), torax['Room'], torax['Path'], torax['Teleport']
        print format('Moving %s characters to %s' % (SERVER, god))
        if str(len(chars)) != SIZE:
            print format("WARNING: This group does not have exactly %s characters in it. Currently there are %s in it" % (SIZE, str(len(chars))))
        while attempt <= 2:
            mover_queue = Queue.Queue()
            lock.acquire()
            for char in chars:
                mover_queue.put(char)
            lock.release()
            threads = []
            for _ in range(len(chars)):
                thread = CheckRoomThread(mover_queue)
                thread.start()
                threads.append(thread)
            mover_queue.join()
            if str(len(MOVEDCHARS)) == SIZE:
                print format('All %s characters are in room %s.' % (SIZE, ROOM))
                MOVEDCHARS = [] # reset value
                FAILEDCHARS = [] # reset value
                break
            else:
                print format('%s characters failed to reach room %s. chars = %s ' % (len(FAILEDCHARS), ROOM, FAILEDCHARS))
                chars = FAILEDCHARS
        if attempt > 2:
            print format("Unknown Error Occurred - Likely on OW's end")

def moveSigil():
    global SIZE, ROOM, PATH, TELEPORT, SERVER, SERVERID, MOVEDCHARS, FAILEDCHARS
    SERVER = 'sigil'
    SERVERID = '1'
    for god in SIGILGODS:
        attempt = 0
        sigil = SIGILCHARS[god]
        chars, SIZE, ROOM, PATH, TELEPORT = sigil['Raiders'], str(sigil['RaidSize']), sigil['Room'], sigil['Path'], sigil['Teleport']
        print format('Moving %s characters to %s' % (SERVER, god))
        if str(len(chars)) != SIZE:
            print format("WARNING: This group does not have exactly %s characters in it. Currently there are %s in it" % (SIZE, str(len(chars))))
        while attempt <= 2:
            mover_queue = Queue.Queue()
            lock.acquire()
            for char in chars:
                mover_queue.put(char)
            lock.release()
            threads = []
            for _ in range(len(chars)):
                thread = CheckRoomThread(mover_queue)
                thread.start()
                threads.append(thread)
            mover_queue.join()
            if str(len(MOVEDCHARS)) == SIZE:
                print format('All %s characters are in room %s.' % (SIZE, ROOM))
                MOVEDCHARS = []  # reset value
                FAILEDCHARS = []  # reset value
                break
            else:
                print format('%s characters failed to reach room %s. chars = %s ' % (len(FAILEDCHARS), ROOM, FAILEDCHARS))
                chars = FAILEDCHARS
        if attempt > 2:
            print format("Unknown Error occured during moving - likely on OW's end")

class CheckRoomThread(threading.Thread):
    def __init__(self, queue):
        self.queue = queue
        threading.Thread.__init__(self)

    def run(self):
        self.mover()
        self.queue.task_done()

    def mover(self):
        global MOVEDCHARS, FAILEDCHARS, MOVE_URL
        char = self.queue.get()
        targetRoom = '"curRoom":"%s"' % ROOM
        MOVE_URL = 'http://%s.outwar.com/ajax_changeroomb.php?room=' % (SERVER)
        charName = char_name(url_opener('http://%s.outwar.com/world.php?serverid=%s&suid=%s' % (SERVER, SERVERID, char)).read())
        curRoom = url_opener('http://%s.outwar.com/ajax_changeroomb.php?serverid=%s&suid=%s' % (SERVER, SERVERID, char)).read()
        if targetRoom in curRoom:
            #print format("%s is in the correct room, no moving required." % (charName))
            MOVEDCHARS.append(char)
        else:
            print format("%s is not in the correct room, attempting to teleport and try again" % (charName))
            url_opener('http://%s.outwar.com/world.php?room=%s&serverid=%s&suid=%s' % (SERVER, TELEPORT, SERVERID, char))
            for room in PATH:
                url_opener('%s%s&serverid=%s&suid=%s' % (MOVE_URL, room, SERVERID, char))
            curRoom = url_opener('http://%s.outwar.com/ajax_changeroomb.php?serverid=%s&suid=%s' % (SERVER, SERVERID, char)).read()
            if targetRoom in curRoom:
                #print format("%s is now in the correct room." % (charName))
                MOVEDCHARS.append(char)
            else:
                print format('%s failed to move. lets try again!')
                FAILEDCHARS.append(char)


def mover():
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = PriestCheckerThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()




def moveTo_Suka():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"455"'
    PATH = [483, 249, 450, 451, 455]
    CHARS = GodMover.GROUP_SUKA()[0]
    SIZE = GodMover.GROUP_SUKA()[1]
    TELEPORT = 130
    print format("Moving characters to Suka...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Ganeshan():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"456"'
    PATH = [483, 249, 450, 451, 455, 456]
    CHARS = GodMover.GROUP_GANESHAN()[0]
    SIZE = GodMover.GROUP_GANESHAN()[1]
    TELEPORT = 130
    print format("Moving characters to Ganeshan...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Kroshuk():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3023"'
    PATH = [92, 93, 94, 95, 96, 97, 2349, 2350, 2351, 2352, 2353, 2499, 2500, 2501, 2502, 2503, 2504, 2512, 2514, 2515, 2513, 2507, 2508, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2528, 2523, 2524, 2525, 2526, 2527, 2530, 2529, 2532, 2959, 2673, 2674, 2675, 2676, 2677, 2678, 2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2696, 2697, 2698, 2699, 2960, 2961, 2964, 2967, 2968, 2969, 2974, 2976, 2977, 2978, 2979, 2986, 2990, 2991, 2994, 2999, 3007, 3006, 3008, 3031, 3029, 3023]
    CHARS = GodMover.GROUP_KROSHUK()[0]
    SIZE = GodMover.GROUP_KROSHUK()[1]
    TELEPORT = 91
    print format("Moving characters to Kro Shuk...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Ebliss():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2755"'
    PATH = [40, 39, 38, 37, 1006, 1007, 1008, 1009, 1012, 1105, 1106, 1728, 1727, 1726, 1725, 1724, 2156, 2157, 2158, 2159, 1790, 1803, 1804, 1805, 1813, 1815, 1816, 1920, 1919, 1918, 1917, 1916, 1922, 1924, 1925, 2753, 2754, 2755]
    CHARS = GodMover.GROUP_EBLISS()[0]
    SIZE = GodMover.GROUP_EBLISS()[1]
    TELEPORT = 11
    print format("Moving characters to Ebliss...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Brutalitar():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"1975"'
    PATH = [40, 39, 38, 37, 1006, 1007, 1008, 1009, 1012, 1105, 1106, 1728, 1727, 1726, 1725, 1724, 2156, 2157, 2158, 2159, 1790, 1803, 1804, 1805, 1813, 1815, 1817, 1818, 1821,  1820, 1822, 1823, 1824, 1825, 1830, 1833, 1834, 1835, 1836, 1837, 1838, 1839, 1840, 1841, 1842, 1843, 1844, 1845, 1847, 1848, 1849, 1850, 1951, 1953, 1955, 1956, 1957, 1958, 1959, 1962, 1963, 1964, 1966, 1967, 1968, 1970, 1971, 1972, 1975]
    CHARS = GodMover.GROUP_BRUTALITAR()[0]
    SIZE = GodMover.GROUP_BRUTALITAR()[1]
    TELEPORT = 11
    print format("Moving characters to Brutalitar...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Dregnor():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2945"'
    PATH = [2766, 2767, 2768, 2769, 2770, 2761, 2762, 2763, 2764, 2765, 2771, 2772, 2773, 2777, 2783, 2789, 2791, 2796, 2798, 2799, 2866, 2867, 2868, 2869, 2870, 2873, 2874, 2875, 2876, 2877, 2878, 2879, 2886, 2887, 2888, 2889, 2939, 2948, 2947, 2946, 2945]
    CHARS = GodMover.GROUP_DREGNOR()[0]
    SIZE = GodMover.GROUP_DREGNOR()[1]
    TELEPORT = 130
    print format("Moving characters to Dreg Nor...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Ashnar():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2955"'
    PATH = [2766, 2767, 2768, 2769, 2770, 2761, 2762, 2763, 2764, 2765, 2771, 2772, 2774, 2776, 2778, 2780, 2781, 2782, 2790, 2792, 2793, 2794, 2795, 2797, 2803, 2804, 2805, 2823, 2830, 2832, 2837, 2861, 2860, 2862, 2864, 2872, 2880, 2890, 2891, 2896, 2897, 2898, 2901, 2904, 2906, 2910, 2913, 2916, 2918, 2919, 2920, 2921, 2933, 2935, 2937, 2934, 2938, 2954, 2953, 2956, 2955]
    CHARS = GodMover.GROUP_ASHNAR()[0]
    SIZE = GodMover.GROUP_ASHNAR()[1]
    TELEPORT = 130
    print format("Moving characters to Ashnar...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Narzhul():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3059"'
    PATH = [92, 93, 94, 95, 96, 97, 2349, 2350, 2351, 2352, 2353, 2499, 2500, 2501, 2502, 2503, 2504, 2512, 2514, 2515, 2513, 2507, 2508, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2528, 2523, 2524, 2525, 2526, 2527, 2530, 2529, 2532, 2959, 2673, 2674, 2675, 2676, 2677, 2678, 2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2696, 2697, 2698, 2699, 2960, 2961, 2964, 2967, 2968, 2969, 2974, 2976, 2977, 2978, 2979, 2986, 2990, 2991, 2994, 2999, 3007, 3006, 3008, 3031, 3029, 3023, 3035, 3041, 3045, 3047, 3048, 3049, 3052, 3054, 3057, 3059]
    CHARS = GodMover.GROUP_NARZHUL()[0]
    SIZE = GodMover.GROUP_NARZHUL()[1]
    TELEPORT = 91
    print format("Moving characters to Nar Zhul...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Volgan():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"26306"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 26137, 26142, 26143, 26144, 26145, 26182, 26185, 26186, 26191, 26192, 26197, 26198, 26201, 26293, 26296, 26297, 26303, 26304, 26305, 26306]
    CHARS = GodMover.GROUP_VOLGAN()[0]
    SIZE = GodMover.GROUP_VOLGAN()[1]
    TELEPORT = 11
    print format("Moving characters to Volgan...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Sarcrina():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"26294"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 26137, 26142, 26143, 26144, 26145, 26182, 26185, 26186, 26191, 26192, 26197, 26198, 26201, 26293, 26294]
    CHARS = GodMover.GROUP_SARCRINA()[0]
    SIZE = GodMover.GROUP_SARCRINA()[1]
    TELEPORT = 11
    print format("Moving characters to Sarcrina...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Tarkin():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"26295"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 26137, 26142, 26143, 26144, 26145, 26182, 26185, 26186, 26191, 26192, 26197, 26198, 26201, 26293, 26295]
    CHARS = GodMover.GROUP_TARKIN()[0]
    SIZE = GodMover.GROUP_TARKIN()[1]
    TELEPORT = 11
    print format("Moving characters to Ancient Magus Tarkin...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Jorun():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"26302"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 26137, 26142, 26143, 26144, 26145, 26182, 26185, 26186, 26191, 26192, 26197, 26198, 26201, 26293, 26296, 26297, 26299, 26300, 26301, 26302]
    CHARS = GodMover.GROUP_JORUN()[0]
    SIZE = GodMover.GROUP_JORUN()[1]
    TELEPORT = 11
    print format("Moving characters to Jorun...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Zikkr():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"26298"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 26137, 26142, 26143, 26144, 26145, 26182, 26185, 26186, 26191, 26192, 26197, 26198, 26201, 26293, 26296, 26297, 26298]
    CHARS = GodMover.GROUP_ZIKKR()[0]
    SIZE = GodMover.GROUP_ZIKKR()[1]
    TELEPORT = 11
    print format("Moving characters to Zikkr...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


#COES#
def moveTo_Neudeus():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"7394"'
    PATH = []
    CHARS = GodMover.GROUP_NEUDEUS()[0]
    SIZE = GodMover.GROUP_NEUDEUS()[1]
    TELEPORT = 6640
    print format("Moving characters to Emperor Neudeus, Controller of the Universe...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Numerocure():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"7652"'
    PATH = []
    CHARS = GodMover.GROUP_NUMEROCURE()[0]
    SIZE = GodMover.GROUP_NUMEROCURE()[1]
    TELEPORT = 6640
    print format("Moving characters to Melt Numerocure, The Black Messenger of Evil...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_Rotborn():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"7000"'
    PATH = [6639, 6683, 6682, 6681, 6680, 6677, 6673, 6561, 6560, 6646, 6647, 6648, 6556, 6555, 6554, 6705, 6706, 6715, 6714, 6713, 6718, 6712, 6541, 6540, 6711, 6538, 6537, 6536, 6535, 6512, 6511, 6510, 6460, 6459, 6458, 6457, 6434, 6476, 6475, 6431, 6430, 6480, 6482, 6487, 6491, 6493, 6495, 6496, 6504, 6503, 6989, 6990, 6991, 6992, 6993, 6994, 6995, 6996, 6997, 6998, 7007, 7006, 7005, 7000]
    CHARS = GodMover.GROUP_ROTBORN()[0]
    SIZE = GodMover.GROUP_ROTBORN()[1]
    TELEPORT = 6640
    print format("Moving characters to Rotborn, Eater of the Dead...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Meltbane():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"7421"'
    PATH = [6639, 6683, 6682, 6681, 6680, 6677, 6673, 6561, 6560, 6646, 6647, 6648, 6556, 6555, 6554, 6705, 6706, 6715, 6714, 6713, 6718, 6712, 6541, 6540, 6711, 6538, 6537, 6536, 6535, 6512, 6511, 6510, 6460, 6459, 6458, 6457, 6434, 6433, 6445, 6446, 6447, 6448, 6449, 6450, 7446, 7456, 7455, 7454, 7453, 7452, 7424, 7423, 7422, 7421]
    CHARS = GodMover.GROUP_MELTBANE()[0]
    SIZE = GodMover.GROUP_MELTBANE()[1]
    TELEPORT = 6640
    print format("Moving characters to Melt Bane, The Forbidden Demon Dragon...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()



def moveTo_Pinosis():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"435"'
    PATH = [483, 249, 435]
    CHARS = GodMover.GROUP_PINOSIS()[0]
    SIZE = GodMover.GROUP_PINOSIS()[1]
    TELEPORT = 130
    print format("Moving characters to Pinosis...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()



def moveTo_Gnorb():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"249"'
    PATH = [483, 249]
    CHARS = GodMover.GROUP_GNORB()[0]
    SIZE = GodMover.GROUP_GNORB()[1]
    TELEPORT = 130
    print format("Moving characters to Gnorb...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_Tsort():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"437"'
    PATH = [483, 249, 435, 437]
    CHARS = GodMover.GROUP_TSORT()[0]
    SIZE = GodMover.GROUP_TSORT()[1]
    TELEPORT = 130
    print format("Moving characters to Tsort...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()



def moveTo_Shadow():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"438"'
    PATH = [483, 249, 435, 437, 438]
    CHARS = GodMover.GROUP_SHADOW()[0]
    SIZE = GodMover.GROUP_SHADOW()[1]
    TELEPORT = 130
    print format("Moving characters to Shadow...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_Nessam():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"420"'
    PATH = [483, 249, 420]
    CHARS = GodMover.GROUP_NESSAM()[0]
    SIZE = GodMover.GROUP_NESSAM()[1]
    TELEPORT = 130
    print format("Moving characters to Nessam...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_Crane():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"421"'
    PATH = [483, 249, 420, 421]
    CHARS = GodMover.GROUP_CRANE()[0]
    SIZE = GodMover.GROUP_CRANE()[1]
    TELEPORT = 130
    print format("Moving characters to Crane...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()



def moveTo_Synge():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"1053"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 1021, 1020, 1019, 1018, 994, 993, 1015, 1016, 1017, 1023, 1024, 1025, 1026, 1043, 1044, 1045, 1046, 1050, 1051, 1052, 1053]
    CHARS = GodMover.GROUP_SYNGE()[0]
    SIZE = GodMover.GROUP_SYNGE()[1]
    TELEPORT = 11
    print format("Moving characters to Synge...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Garland():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2489"'
    PATH = [90, 89, 88, 2333, 2334, 2343, 2342, 2341, 2340, 2339, 2338, 2337, 2336, 2452, 2453, 2454, 2457, 2458, 2461, 2462, 2465, 2466, 2473, 2474, 2476, 2479, 2480, 2490, 2492, 2497, 2496, 2483, 2487, 2489]
    CHARS = GodMover.GROUP_GARLAND()[0]
    SIZE = GodMover.GROUP_GARLAND()[1]
    TELEPORT = 91
    print format("Moving characters to Garland...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Tylos():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2487"'
    PATH = [90, 89, 88, 2333, 2334, 2343, 2342, 2341, 2340, 2339, 2338, 2337, 2336, 2452, 2453, 2454, 2457, 2458, 2461, 2462, 2465, 2466, 2473, 2474, 2476, 2479, 2480, 2490, 2492, 2497, 2496, 2483, 2487]
    CHARS = GodMover.GROUP_TYLOS()[0]
    SIZE = GodMover.GROUP_TYLOS()[1]
    TELEPORT = 91
    print format("Moving characters to Tylos, The Lord Master...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Threk():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2486"'
    PATH = [90, 89, 88, 2333, 2334, 2343, 2342, 2341, 2340, 2339, 2338, 2337, 2336, 2452, 2453, 2454, 2457, 2458, 2461, 2462, 2465, 2466, 2473, 2474, 2476, 2479, 2480, 2490, 2492, 2497, 2496, 2483, 2487, 2486]
    CHARS = GodMover.GROUP_THREK()[0]
    SIZE = GodMover.GROUP_THREK()[1]
    TELEPORT = 91
    print format("Moving characters to Threk...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Rancid():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"1054"'
    PATH = [40, 39, 38, 37, 36, 35, 34, 33, 32, 1021, 1020, 1019, 1018, 994, 993, 1015, 1016, 1017, 1023, 1024, 1025, 1026, 1043, 1044, 1045, 1046, 1050, 1051, 1052, 1054]
    CHARS = GodMover.GROUP_RANCID()[0]
    SIZE = GodMover.GROUP_RANCID()[1]
    TELEPORT = 11
    print format("Moving characters to Rancid...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Hyrak():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"452"'
    PATH = [483,249,450,451,452]
    CHARS = GodMover.GROUP_HYRAK()[0]
    SIZE = GodMover.GROUP_HYRAK()[1]
    TELEPORT = 130
    print format("Moving characters to Hyrak...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Vitkros():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"454"'
    PATH = [483,249,450,451,452,453,454]
    CHARS = GodMover.GROUP_VITKROS()[0]
    SIZE = GodMover.GROUP_VITKROS()[1]
    TELEPORT = 130
    print format("Moving characters to Vitkros...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Wanhi():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"434"'
    PATH = [483, 249, 420, 434]
    CHARS = GodMover.GROUP_WANHI()[0]
    SIZE = GodMover.GROUP_WANHI()[1]
    TELEPORT = 130
    print format("Moving characters to Wanhiroeaz the Devourer...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Mistress():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"436"'
    PATH = [483, 249, 435, 436]
    CHARS = GodMover.GROUP_MISTRESS()[0]
    SIZE = GodMover.GROUP_MISTRESS()[1]
    TELEPORT = 130
    print format("Moving characters to Mistress of the Sword...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Traxodon():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"457"'
    PATH = [483, 249, 450, 451, 455, 456, 457]
    CHARS = GodMover.GROUP_TRAXODON()[0]
    SIZE = GodMover.GROUP_TRAXODON()[1]
    TELEPORT = 130
    print format("Moving characters to Traxodon the Plaguebringer...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_AgNabak():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3019"'
    PATH = [92, 93, 94, 95, 96, 97, 2349, 2350, 2351, 2352, 2353, 2499, 2500, 2501, 2502, 2503, 2504, 2512, 2514, 2515, 2513, 2507, 2508, 2516, 2517, 2518, 2519, 2520, 2521, 2522, 2528, 2523, 2524, 2525, 2526, 2527, 2530, 2529, 2532, 2959, 2673, 2674, 2675, 2676, 2677, 2678, 2679, 2680, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2696, 2697, 2698, 2699, 2960, 2961, 2964, 2967, 2968, 2969, 2974, 2976, 2977, 2978, 2979, 2986, 2990, 2991, 2994, 2999, 3007, 3006, 3008, 3031, 3029, 3023, 3022, 3021, 3020, 3019]
    CHARS = GodMover.GROUP_AGNABAK()[0]
    SIZE = GodMover.GROUP_AGNABAK()[1]
    TELEPORT = 91
    print format("Moving characters to Ag Nabak...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Anguish():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3878"'
    PATH = [92, 93, 98, 99, 100, 101, 102, 103, 104, 2344, 2345, 3824, 3825, 3826, 3827, 3828, 3829, 3832, 3837, 3838, 3843, 3857, 3861, 3878]
    CHARS = GodMover.GROUP_ANGUISH()[0]
    SIZE = GodMover.GROUP_ANGUISH()[1]
    TELEPORT = 91
    print format("Moving characters to Anguish...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Detox():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3858"'
    PATH = [92, 93, 98, 99, 100, 101, 102, 103, 104, 2344, 2345, 3824, 3825, 3826, 3827, 3828, 3829, 3832, 3837, 3838, 3848, 3849, 3850, 3856, 3858]
    CHARS = GodMover.GROUP_DETOX()[0]
    SIZE = GodMover.GROUP_DETOX()[1]
    TELEPORT = 91
    print format("Moving characters to Detox...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_EmeraldAssassin():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3859"'
    PATH = [92, 93, 98, 99, 100, 101, 102, 103, 104, 2344, 2345, 3824, 3825, 3826, 3827, 3828, 3829, 3830, 3833, 3834, 3840, 3841, 3853, 3859]
    CHARS = GodMover.GROUP_EMERALDASSASSIN()[0]
    SIZE = GodMover.GROUP_EMERALDASSASSIN()[1]
    TELEPORT = 91
    print format("Moving characters to The Emerald Assassin...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Murderface():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"3860"'
    PATH = [92, 93, 98, 99, 100, 101, 102, 103, 104, 2344, 2345, 3824, 3825, 3826, 3827, 3828, 3829, 3831, 3836, 3835, 3839, 3842, 3852, 3860]
    CHARS = GodMover.GROUP_MURDERFACE()[0]
    SIZE = GodMover.GROUP_MURDERFACE()[1]
    TELEPORT = 91
    print format("Moving characters to Murderface...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_BaronMu():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"6928"'
    PATH = [6639, 6683, 6682, 6681, 6680, 6677, 6673, 6561, 6560, 6646, 6647, 6648, 6556, 6555, 6554, 6705, 6706, 6715, 6714, 6713, 6718, 6712, 6541, 6540, 6711, 6538, 6537, 6536, 6535, 6512, 6511, 6510, 6460, 6459, 6458, 6457, 6434, 6476, 6475, 6478, 6479, 6480, 6412, 6411, 6410, 6422, 6408, 6407, 6406, 6413, 8178, 6375, 6374, 6359, 6354, 6338, 6335, 6336, 6924, 6923, 6922, 6929, 6928]
    CHARS = GodMover.GROUP_BARONMU()[0]
    SIZE = GodMover.GROUP_BARONMU()[1]
    TELEPORT = 6640
    print format("Moving characters to Baron Mu, Dark Rider of the Undead...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Sibannac():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2813"'
    PATH = [2766, 2767, 2768, 2769, 2770, 2761, 2762, 2763, 2764, 2765, 2771, 2772, 2774, 2776, 2778, 2780, 2781, 2782, 2790, 2792, 2793, 2794, 2795, 2797, 2803, 2804, 2805, 2823, 2830, 2832, 2837, 2861, 2860, 2859, 2858, 2841, 2831, 2829, 2822, 2808, 2809, 2810, 2811, 2812, 2813]
    CHARS = GodMover.GROUP_SIBANNAC()[0]
    SIZE = GodMover.GROUP_SIBANNAC()[1]
    TELEPORT = 130
    print format("Moving characters to Lord Sibannac...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Ganja():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2132"'
    PATH = [40, 39, 38, 37, 1006, 1007, 1008, 1009, 1012, 1105, 1106, 1728, 1727, 1726, 1725, 1724, 2156, 2157, 2158, 2159, 1790, 1803, 1804, 1805, 1813, 1815, 1817, 1818, 1821,  1820, 1822, 1823, 1824, 1825, 1826, 1827, 1852, 1895, 1894, 1893, 1892, 1891, 1890, 1887, 1886, 1885, 1884, 1902, 1901, 1926, 1927, 1928, 1929, 1930, 1931, 2036, 2037, 2039, 2041, 2049, 2141, 2140, 2139, 2138, 2137, 2136, 2131, 2132]
    CHARS = GodMover.GROUP_GANJA()[0]
    SIZE = GodMover.GROUP_GANJA()[1]
    TELEPORT = 11
    print format("Moving characters to Ganja the Stone Golem...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Smoot():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2834"'
    PATH = [2766, 2767, 2768, 2769, 2770, 2761, 2762, 2763, 2764, 2765, 2771, 2772, 2773, 2777, 2783, 2789, 2802, 2801, 2818, 2819, 2820, 2824, 2828, 2835, 2834]
    CHARS = GodMover.GROUP_SMOOT()[0]
    SIZE = GodMover.GROUP_SMOOT()[1]
    TELEPORT = 130
    print format("Moving characters to Smoot the Yeti...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_Bloodchill():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"2034"'
    PATH = [40, 39, 38, 37, 1006, 1007, 1008, 1009, 1012, 1105, 1106, 1728, 1727, 1726, 1725, 1724, 2156, 2157, 2158, 2159, 1790, 1803, 1804, 1805, 1813, 1815, 1817, 1818, 1821,  1820, 1822, 1823, 1824, 1825, 1830, 1833, 1834, 1835, 1836, 1837, 1838, 1839, 1840, 1841, 1842, 1843, 1844, 1845, 1847, 1848, 1849, 1850, 1951, 1952, 1954, 2005, 2006, 2007, 2008, 2009, 2011, 2012, 2013, 2014, 2019, 2018, 2021, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2031, 2032, 2033, 2034]
    CHARS = GodMover.GROUP_BLOODCHILL()[0]
    SIZE = GodMover.GROUP_BLOODCHILL()[1]
    TELEPORT = 11
    print format("Moving characters to Bloodchill the Grizzly...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Varan():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"433"'
    PATH = [483, 249, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433]
    CHARS = GodMover.GROUP_VARAN()[0]
    SIZE = GodMover.GROUP_VARAN()[1]
    TELEPORT = 130
    print format("Moving characters to Lord Varan...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Narada():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"449"'
    PATH = [483, 249, 435, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449]
    CHARS = GodMover.GROUP_NARADA()[0]
    SIZE = GodMover.GROUP_NARADA()[1]
    TELEPORT = 130
    print format("Moving characters to Lord Narada...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Ariella():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"453"'
    PATH = [483,249,450,451,452, 453]
    CHARS = GodMover.GROUP_ARIELLA()[0]
    SIZE = GodMover.GROUP_ARIELLA()[1]
    TELEPORT = 130
    print format("Moving characters to Lady Ariella...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Jade():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"9608"'
    PATH = [6639, 6683, 6682, 6681, 6680, 6677, 6673, 6561, 6560, 6646, 6647, 6648, 6556, 6555, 6554, 6705, 6706, 6715, 6714, 6713, 6718, 6712, 6541, 6540, 6711, 6538, 6537, 6536, 6535, 6512, 6511, 6510, 6460, 6459, 6458, 6457, 6434, 6476, 6475, 6431, 6430, 6429, 6412, 6411, 6410, 6422, 6421, 6418, 6406, 6405, 8178, 6381, 6382, 6383, 6384, 6385, 6386, 6387, 6388, 6398, 9919, 9920, 9918, 9917, 8577, 8575, 8574, 8573, 8527, 8526, 8524, 8525, 8522, 8570, 8564, 8571, 8558, 8557, 8556, 8504, 8506, 8582, 8890, 8886, 8887, 8891, 8892, 8893, 8913, 8917, 8915, 8921, 8922, 8929, 8930, 8931, 8932, 8933, 8942, 8943, 8944, 8948, 8951, 8950, 8982, 8983, 8985, 8988, 8990, 8991, 8992, 8993, 8994, 8995, 8996, 8997, 8998, 8999, 9000, 9065, 9066, 9067, 9068, 9069, 9070, 9071, 9072, 9510, 9511, 9514, 9515, 9517, 9518, 9519, 9520, 9523, 9524, 9526, 9527, 9528, 9530, 9531, 9533, 9534, 9535, 9537, 9538, 9540, 9542, 9543, 9544, 9545, 9547, 9548, 9549, 9551, 9553, 9555, 9556, 9559, 9560, 9561, 9563, 9564, 9565, 9566, 9568, 9570, 9572, 9573, 9578, 9579, 9580, 9582, 9584, 9595, 9596, 9597, 9598, 9604, 9605, 9606, 9607, 9608]
    CHARS = GodMover.GROUP_JADE()[0]
    SIZE = GodMover.GROUP_JADE()[1]
    TELEPORT = 6640
    print format("Moving characters to Jade Dragonite...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_Drake():
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"9615"'
    PATH = [6639, 6683, 6682, 6681, 6680, 6677, 6673, 6561, 6560, 6646, 6647, 6648, 6556, 6555, 6554, 6705, 6706, 6715, 6714, 6713, 6718, 6712, 6541, 6540, 6711, 6538, 6537, 6536, 6535, 6512, 6511, 6510, 6460, 6459, 6458, 6457, 6434, 6476, 6475, 6431, 6430, 6429, 6412, 6411, 6410, 6422, 6421, 6418, 6406, 6405, 8178, 6381, 6382, 6383, 6384, 6385, 6386, 6387, 6388, 6398, 9919, 9920, 9918, 9917, 8577, 8575, 8574, 8573, 8527, 8526, 8524, 8525, 8522, 8570, 8564, 8571, 8558, 8557, 8556, 8504, 8506, 8582, 8890, 8886, 8887, 8891, 8892, 8893, 8913, 8917, 8915, 8921, 8922, 8929, 8930, 8931, 8932, 8933, 8942, 8943, 8944, 8948, 8951, 8950, 8982, 8983, 8985, 8988, 8990, 8991, 8992, 8993, 8994, 8995, 8996, 8997, 8998, 8999, 9000, 9065, 9066, 9067, 9068, 9069, 9070, 9071, 9072, 9510, 9511, 9514, 9515, 9517, 9518, 9519, 9520, 9523, 9524, 9526, 9527, 9528, 9530, 9531, 9533, 9534, 9535, 9537, 9538, 9540, 9542, 9543, 9544, 9545, 9547, 9548, 9549, 9551, 9553, 9555, 9556, 9559, 9560, 9561, 9563, 9564, 9565, 9566, 9568, 9570, 9572, 9573, 9578, 9579, 9580, 9582, 9584, 9595, 9596, 9597, 9598, 9604, 9605, 9606, 9607, 9608, 9612, 9613, 9614, 9615]
    CHARS = GodMover.GROUP_DRAKE()[0]
    SIZE = GodMover.GROUP_DRAKE()[1]
    TELEPORT = 6640
    print format("Moving characters to Jade Dragonite...")
    if len(CHARS) != SIZE:
        print format ("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_WOZ1(): # mercenary
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"20"'
    PATH = [12,13,14,15,16,17,18,19,20]
    CHARS = GodMover.GROUP_WOZ1()[0]
    SIZE = GodMover.GROUP_WOZ1()[1]
    TELEPORT = 11
    print
    format("Moving characters to Zhulian Mercenary...")
    if len(CHARS) != SIZE:
        print
        format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()


def moveTo_WOZ2(): # mistress
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"22"'
    PATH = [41,42,43,44,45,46,26,25,24,23,22]
    CHARS = GodMover.GROUP_WOZ2()[0]
    SIZE = GodMover.GROUP_WOZ2()[1]
    TELEPORT = 11
    print format("Moving characters to Zhulian Mistress...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def moveTo_WOZ3(): # friar
    global DESTINATIONROOM, PATH, CHARS, TELEPORT
    DESTINATIONROOM = '"curRoom":"81"'
    PATH = [90, 89, 88, 82, 469, 237, 233, 57, 58, 59, 60, 78, 79, 80, 81]
    CHARS = GodMover.GROUP_WOZ3()[0]
    SIZE = GodMover.GROUP_WOZ3()[1]
    TELEPORT = 91
    print format("Moving characters to Zhulian Friar...")
    if len(CHARS) != SIZE:
        print format("WARNING: This group does not have exactly %s characters in it." % (SIZE))
    mover_queue = Queue.Queue()
    lock.acquire()
    for char in CHARS:
        mover_queue.put(char)
    lock.release()
    threads = []
    for _ in range(THREADS):
        thread = CheckRoomThread(mover_queue)
        thread.start()
        threads.append(thread)
    mover_queue.join()

def login():
    # login to RGA
    login = url_opener('http://%s.outwar.com/myaccount.php' % (SERVER), 'login_username=%s&login_password=%s&serverid=%s&suid=%s' % (username, password, SERVERID, BASE_ID))
    print format('Logged in to RGA %s\n' % username)
    sleep(2)

def logout():
    url_opener('http://torax.outwar.com/world?cmd=logout')

if __name__ == "__main__":
    LoadCharacters()
    LoadGods()
    login()
    sleep(2)
    moveSigil()
    moveTorax()
    

def Main(toraxG, toraxR, sigilG, sigilR):
    global TORAXGODS, TORAXCHARS, SIGILGODS, SIGILCHARS
    TORAXGODS, TORAXCHARS = toraxG, toraxR
    SIGILGODS, SIGILCHARS = sigilG, sigilR
    login()
    moveTorax()
    moveSigil()
    logout()


def oldstuff():
    # # # # # # # #
    # 5 man raids #
    # # # # # # # #

    #moveTo_Suka()
    #moveTo_Ganeshan()
    #moveTo_Kroshuk()
    #moveTo_Ebliss()
    #moveTo_Brutalitar()
    #moveTo_Dregnor()
    #moveTo_Ashnar()
    #moveTo_Narzhul()

    # # # #  # # # #
    # 10 man raids #
    # # # #  # # # #

    moveTo_Volgan()
    moveTo_Sarcrina()
    moveTo_Tarkin()
    moveTo_Jorun()
    moveTo_Zikkr()

    # # # #  # # # #
    # 15 man raids #
    # # # #  # # # #

    #moveTo_Rotborn()
    #moveTo_Meltbane()
    #moveTo_Ladychaos()
    #moveTo_Numerocure()
    #moveTo_Hackerphage()
    #moveTo_Howldroid()
    #moveTo_Slashbrood()
    #moveTo_Neudeus()

    #moveTo_WOZ1()
    #moveTo_WOZ2()
    #moveTo_WOZ3()

    # # # #  # # # #
    #   Noob Gods  #
    # # # #  # # # #
    #moveTo_Pinosis()
    #moveTo_Tsort()
    #moveTo_Shadow()
    #moveTo_Nessam()
    #moveTo_Gnorb()
    #moveTo_Crane()
    #moveTo_Synge()
    #moveTo_Garland()
    #moveTo_Threk()
    #moveTo_Rancid()
    #moveTo_Vitkros()
    #moveTo_Wanhi()
    #moveTo_Hyrak()
    #moveTo_AgNabak()
    #moveTo_Mistress()
    #moveTo_Anguish()
    #moveTo_Murderface()
    #moveTo_EmeraldAssassin()
    #moveTo_Detox()
    #moveTo_Traxodon()
    #moveTo_BaronMu()
    #moveTo_Sibannac()
    #moveTo_Tylos()
    #moveTo_Bloodchill()
    #moveTo_Ganja()
    #moveTo_Smoot()
    #moveTo_Varan()
    #moveTo_Ariella()
    #moveTo_Narada()
    #moveTo_Jade()
    #moveTo_Drake()
    print format('Done moving characters!')

