from HTMLParser import HTMLParser, HTMLParseError
from urllib2 import urlopen, urlparse, HTTPError, URLError
from httplib import HTTPException
from datetime import date, datetime, timedelta
import re

class MenuItem():
    def __init__(self):
        self.name = None
        self.mealtime = None
        self.offeredOn = None
        self.parsedFromMenuOn = None
        
    def __str__(self):
        return '%s,%s,%s,%s' % (self.name, self.mealtime, self.offeredOn, self.parsedFromMenuOn)
        
class Menu():
    def __init__(self):
        self.html = None
        self.building = None
        self.weekOf = None
        self.downloadedOn = None
        self.menuItems = None
        
    def __str__(self):
        xmlStr = '%s,%s,%s\r' % (self.building, self.weekOf, self.downloadedOn)
        for menuItem in self.menuItems :
            xmlStr += menuItem.__str__( ) + '\r'
        return xmlStr

class SodexoMenuParser(HTMLParser):
    def parse(self, url):
        self.recordTitle = False
        self.recordBuilding = False
        self.recordMenuItem = False
        self.recordMealtime = False
        self.mealtime = None
        self.date = None
        
        self.menu = Menu()
        self.menuItem = MenuItem()
        
        try: 
            response = urlopen(url)
        except HTTPError, e:
            return 'HTTPError = ' + str(e.code)
        except URLError, e:
            return 'URLError = ' + str(e.reason)
    
        html = response.read() # byte string, need to decode to text
        
        # http://www.w3.org/TR/REC-html40/charset.html#h-5.2.2 defines the encoding priority
        encoding = None # the page's encoding
        
        # Check HTTP Response for charset first
        if 'content-type' in response.headers and 'charset=' in response.headers['content-type']:
            encoding = response.headers['content-type'].split('charset=')[-1]
        
        # Check HTML for charset second
        if encoding == None or encoding == '':
            # initially assume ISO-8859-1; see http://www.ietf.org/rfc/rfc2616.txt section 3.7.1
            # *NOTE* That standard is for HTTP/1.1, but what about others?
            encoding = 'ISO-8859-1'
            temp_content = html.decode(encoding, 'replace')
            
            match = re.search('charset=([a-zA-Z0-9\-]*)', temp_content, re.DOTALL | re.MULTILINE)
            if match and match.group(1): # found the encoding in the HTML
                encoding = match.group(1)
        
        html = html.decode(encoding, 'replace').encode('utf8')
        
        # HTML parser is not very robust and tends to die so lets remove the troublesome bits
        style_pattern = re.compile('<style.*?</style>', re.DOTALL | re.MULTILINE | re.I)
        script_pattern = re.compile('<script.*?</script>', re.DOTALL | re.MULTILINE | re.I)
        cleaned_html = re.sub(script_pattern, '', re.sub(style_pattern, '', html))
        
        # grab the menu's "Week of" date; unfortunately there is no very nice way to get this
        weekof_pattern = re.compile('Week of (.*?)</', re.DOTALL)
        date_str = weekof_pattern.search(cleaned_html)
        if date_str and date_str.group(1):
            date_str = ' '.join(date_str.group(1).split()) # remove whitespace between day and month
        self.date = datetime.strptime(date_str, '%A %B %d, %Y').date()
        
        # set up the menu
        self.menu.html = html
        self.menu.weekOf = self.date
        self.menu.downloadedOn = datetime.now()
        self.menu.menuItems = []
        
        # -1 day from the weekof date since the script +1s before adding menu items
        self.date = self.date - timedelta(days=1)

        try:
            self.feed(cleaned_html)
        except HTMLParseError, e:
            f = open('c:\\a.error', 'w+')
            print >> f,cleaned_html
            raise e
        
        return self.menu
        
    def handle_starttag(self, tag, attrs):
        if tag == 'td':
            for attr in attrs:
                if attr[0] == 'class':
                    if attr[1] == 'dayouter': # advance the date
                        self.date = self.date + timedelta(days=1)
                    elif attr[1] == 'mealname': # breakfast, lunch, ...
                        self.recordMealtime = True
                    elif attr[1] == 'titlecell':
                        self.recordTitle = True
                        
        if tag == 'span':
            if self.recordTitle:
                self.recordBuilding = True
            for attr in attrs:
                if attr[0] == 'class':
                    if attr[1] == 'ul': # food
                        self.recordMenuItem = True
                        
    def handle_data(self, data):
        if self.recordBuilding:
            self.menu.building = ' '.join(data.split()).lower() # remove excess whitespace
            self.recordTitle = False
            self.recordBuilding = False
        
        if self.recordMealtime:
            self.mealtime = data.strip().lower()
            self.recordMealtime = False
        elif self.recordMenuItem:
            self.menuItem.name = re.sub(' +', ' ', re.sub('\r\n', '', data)).strip()
                        
    def handle_endtag(self, tag):
        if self.recordMenuItem:
            self.menuItem.offeredOn = self.date
            self.menuItem.mealtime = self.mealtime
            self.menuItem.parsedFromMenuOn = datetime.now()
            self.menu.menuItems.append(self.menuItem)
            self.menuItem = MenuItem()
            self.recordMenuItem = False

parser = SodexoMenuParser()
f = open('c:\\a.dump', 'w+')
print >>f,parser.parse('https://rpi.sodexomyway.com/Menu/Commons2.htm')

