from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache

from google.appengine.api.labs import taskqueue

from django.utils import simplejson

import os
import re
import urllib, urllib2
from datetime import date, timedelta
import base64

import logging
import traceback

from models import PachubeMapping, ParticulateData, TwitterAlert


# http://localhost:8080/_ah/admin/
# http://localhost:8080/_ah/admin/datastore?kind=PachubeMapping&start=30

PACHUBE_API_KEY = "9d7f1b5901b16a979420171f90fc723dd1b739107ae63e08b4caed599299d317"

# Set this to false for development work
PACHUBE = True


class Index(webapp.RequestHandler):
    def get(self):
        # self.redirect("/particulate/")
        q = PachubeMapping.all()
        q.order('stationid')
        
        self.response.headers['Content-Type'] = 'text/html'

        parsepath = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        self.response.out.write(template.render(parsepath, {'mappings': q}))


class AboutPage(webapp.RequestHandler):
    def get(self):
        parsepath = os.path.join(os.path.dirname(__file__), 'templates', 'about.html')
        self.response.out.write(template.render(parsepath, {}))


class DataPage(webapp.RequestHandler):
    def get(self):
        parsepath = os.path.join(os.path.dirname(__file__), 'templates', 'data.html')
        self.response.out.write(template.render(parsepath, {}))


class MainPage(webapp.RequestHandler):
    def get(self):
        q = PachubeMapping.all()
        q.order('stationid')

        self.response.headers['Content-Type'] = 'text/html'

        parsepath = os.path.join(os.path.dirname(__file__), 'templates', 'particulates.html')
        self.response.out.write(template.render(parsepath, {'mappings': q}))
        

class StationPage(webapp.RequestHandler):
    def get(self, stationid):
        q = ParticulateData.all()
        q.filter('stationid =', stationid)
        q.filter('date > ', date.today() - timedelta(90))
        q.order('date')
        results = q.fetch(1000)
        
        mappingQuery = PachubeMapping.all()
        mappingQuery.filter('stationid =', stationid)
        mapping = None
        
        if mappingQuery.count():
            mapping = mappingQuery[0]
        
        values = {'values': results,
                    'station': stationid,
                    'mapping': mapping}
                    
        # Add the flash if we got it
        if self.request.get('flash', ''):
            values['flash'] = self.request.get('flash')
        
        self.response.headers['Content-Type'] = 'text/html'
        
        templatepath = os.path.join(os.path.dirname(__file__), 'templates', 'station.html')
        self.response.out.write(template.render(templatepath, values))
        
        
class StationJSON(webapp.RequestHandler):
    def get(self, stationid):
        response = {}

        q = ParticulateData.all()
        q.filter('stationid =', stationid)
        q.filter('date > ', date.today() - timedelta(90))
        q.order('date')
        results = q.fetch(1000)

        data = []
        for result in results:    
            data.append(result.value)

        logging.info('data got for station %s' % stationid)

        response['data'] = data
        
        # Pachube is not very happy if we hammer them on every index load
        environmentXML = memcache.get("%s_environmentxml" % stationid)
        
        if environmentXML is None:
            mappingQuery = PachubeMapping.all()
            mappingQuery.filter('stationid =', stationid)
            mapping = None
            
            if mappingQuery.count():
                mapping = mappingQuery[0]

                environmentURL = "http://www.pachube.com/api/%s.xml?key=%s" % (mapping.pachubeid, PACHUBE_API_KEY)
                logging.info('fetching url: %s', environmentURL)

                environmentGet = urlfetch.fetch(url=environmentURL)
                
                if environmentGet.status_code == 200 and environmentGet.content:
                    environmentXML = environmentGet.content
                    memcache.set("%s_environmentxml" % stationid, environmentGet.content, time=7*24*60*60)

        lat = ''
        lon = ''
        
        logging.debug('environment xml is - %s', environmentXML)
        
        if environmentXML:
            lat = re.search('<lat>(.+?)</lat>', environmentXML).group(1)
            lon = re.search('<lon>(.+?)</lon>', environmentXML).group(1)
    
            logging.info('got lon %s and lat %s', lon, lat)
        
        response['lat'] = lat
        response['lon'] = lon

        self.response.headers['Content-Type'] = 'text/json'

        self.response.out.write(simplejson.dumps(response))
                    

class AddAlert(webapp.RequestHandler):
    def post(self):
        stationid = self.request.get('stationid')
        threshold = self.request.get('threshold')
        twittername = self.request.get('twittername')
        
        logging.info('added alert on %s for %s to @%s', stationid, threshold, twittername)
        
        if stationid and threshold and twittername:
            t = TwitterAlert(stationid=stationid, amount=int(threshold), twittername=twittername)
            t.put()
            
        self.redirect("/station/%s/?flash=Alarm toegevoegd!" % stationid)
    
        
class SendTweets(webapp.RequestHandler):
    def get(self):
        logging.info('scanning twitter alerts')
        
        q = ParticulateData.all()
        q.filter('date', date.today())
        results = q.fetch(1000)
        
        for result in results:
            # Check if there are outstanding alerts
            
            q2 = TwitterAlert.all()
            q2.filter('stationid', result.stationid)
            alerts = q2.fetch(1000)
            
            for alert in alerts:
                logging.info('result value %d alert on %d', result.value, alert.amount)
                
                if result.value > alert.amount:
                    # Send Tweet
                    targetuser = alert.twittername
                    
                    logging.info('tweet to %s', targetuser)
                    
                    updateString = "@%s De waarde voor station %s is morgen te hoog, nl: %d, zie: http://www.vervuilingsalarm.nl/station/%s/" % (targetuser, result.stationid, result.value, result.stationid)
                    
                    twitterQueue = taskqueue.Queue('twitterqueue')
                    twitterTask = taskqueue.Task(url='/sendtweets/worker/',
                                                params={'update': updateString})
                    twitterQueue.add(twitterTask)
                    
                    # basic_auth = base64.encodestring('%s:%s' % ('rivmalarm', 'testalarm'))[:-1]
                    # 
                    # tweet = urlfetch.fetch(url="http://twitter.com/statuses/update.json?%s" % urllib.urlencode(param), 
                    #                             method=urlfetch.POST,
                    #                             headers = {'Authorization': 'Basic %s' % basic_auth})
                                        
                    # pachubeQueue = taskqueue.Queue('pachubequeue')
                    # pachubeTask = taskqueue.Task(url='/station/%s/updatepachube/' % line[0], 
                    #         params={'stationid': line[0], 'stationname': line[1], 'value': line[3]})
                    # pachubeQueue.add(pachubeTask)
                    
class TweetSendWorker(webapp.RequestHandler):
    def post(self):
        update = self.request.get('update')
        
        param = {'status': update}
        
        basic_auth = base64.encodestring('%s:%s' % ('rivmalarm', 'testalarm'))[:-1]
        
        tweet = urlfetch.fetch(url="http://twitter.com/statuses/update.json?%s" % urllib.urlencode(param), 
                                    method=urlfetch.POST,
                                    headers = {'Authorization': 'Basic %s' % basic_auth})
        
                    
    
class ParseData(webapp.RequestHandler):
    def get(self):
        url = 'http://www.lml.rivm.nl/data/verwachting/pm10.html'
        result = urlfetch.fetch(url)

        logging.info('parsing data')
    
        if result.status_code == 200:
            # Parse out the stuff

            logging.info('data fetch succeeded')

            datalines = []
            store = False

            lines = result.content.split('\n')
            
            for line in lines:
                if '<tr><th>nr<th>naam<th>type<th>conc' in line:
                    store = True
                else:
                    if '</table>' in line:
                        store = False
                    else:
                        if store: # Store this line
                            parts = [part.strip() for part in line.split('<td>')[1:]]
                            datalines.append(parts)
    
        for line in datalines:
            # Put them in our own database
            logging.info('storing %s and %s in database', line[0], line[3])
            data = ParticulateData(stationid=line[0], value=int(line[3]))
            data.put()
        
            pachubeQueue = taskqueue.Queue('pachubequeue')
            pachubeTask = taskqueue.Task(url='/station/%s/updatepachube/' % line[0], 
                    params={'stationid': line[0], 'stationname': line[1], 'value': line[3]})
            pachubeQueue.add(pachubeTask)        
                                
class PachubeUpdateWorker(webapp.RequestHandler):
    def post(self, stationid):
        stationid = self.request.get('stationid')
        stationname = self.request.get('stationname')
        value = self.request.get('value')
        
        logging.info('updating pachube with for station %s with value %s', stationid, value)

        if PACHUBE:
            eemlpath = os.path.join(os.path.dirname(__file__), 'templates', 'eeml.xml')        

            eeml = template.render(eemlpath, {'station': stationid, 
                                              'stationname': stationname, 
                                              'value': value})

            # Check if there's a Pachube association
            q = PachubeMapping.all().filter('stationid =', stationid)
            if q.count() == 0:
                logging.info('creating feed for station %s', stationid)
                # Create a Pachube FEED for this station
            
                feedcreate = urlfetch.fetch(url="http://www.pachube.com/api.xml?key=" + PACHUBE_API_KEY, payload=eeml, method=urlfetch.POST)

                location = feedcreate.headers['location']
                feedid = location.split('/')[-1].split('.')[0]

                logging.info('station %s feed created at %s', stationid, location)

                p = PachubeMapping(stationid=stationid, stationname=stationname, pachubeid=feedid)
                p.put()
            else:
                # We do have a Pachube feed id for this station
                feedid = q[0].pachubeid
                
                logging.info('sending update to pachube feed %s', feedid)

                # Update that station
                logging.info('updating station %s on http://www.pachube.com/api/%s.xml', stationid, feedid)
                try:
                    pachubeupdate = urlfetch.fetch(url="http://www.pachube.com/api/%s.xml?key=%s" % (feedid, PACHUBE_API_KEY), payload=eeml, method=urlfetch.PUT)
                except urlfetch.DownloadError:
                    traceback.print_exc()
                    logging.info('urlfetch failed in updating feed %s' % feedid)
            


class DeleteFeeds(webapp.RequestHandler):
    def post(self):
        # TODO close off delete for admin only
        # users.is_current_user_admin()

        q = PachubeMapping.all()

        for mapping in q:
            logging.info('deleting pachube feed %s', mapping.pachubeid)
            urlfetch.fetch(url="http://www.pachube.com/api/%s?key=%s" % (mapping.pachubeid, PACHUBE_API_KEY), method=urlfetch.DELETE)

            logging.info('deleting mapping')
            mapping.delete()

application = webapp.WSGIApplication(
                                     [('/', Index),
                                     ('/station/alarm/', AddAlert),
                                     ('/station/([^/]+?)/', StationPage),
                                     ('/station/([^/]+?)/json/', StationJSON),
                                     ('/station/([^/]+?)/updatepachube/', PachubeUpdateWorker),
                                     ('/sendtweets/', SendTweets),
                                     ('/sendtweets/worker/', TweetSendWorker),
                                     ('/particulate/', MainPage),
                                    ('/particulate/parse', ParseData),
                                    ('/particulate/deletefeeds', DeleteFeeds),
                                    ('/over/', AboutPage),
                                    ('/data/', DataPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()