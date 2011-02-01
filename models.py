from google.appengine.ext import db

class PachubeMapping(db.Model):
    stationid = db.StringProperty()
    stationname = db.StringProperty()
    pachubeid = db.StringProperty()
  
  
class ParticulateData(db.Model):
    stationid = db.StringProperty()
    value = db.IntegerProperty()
    date = db.DateProperty(auto_now_add=True)
    
# Model to keep track of people wanting twitter alerts for certain stations > value
class TwitterAlert(db.Model):
    stationid = db.StringProperty()
    amount = db.IntegerProperty()
    twittername = db.StringProperty()


def addSampleData():
    from datetime import date, timedelta
    """Sample code to add data to the local development server."""
    # Create 3 sample stations
    PachubeMapping(stationid="131", stationname="Vredepeel-Vredeweg", pachubeid="1674").put()
    PachubeMapping(stationid="133", stationname="Wijnandsrade-Opfergeltstraat", pachubeid="1675").put()
    PachubeMapping(stationid="136", stationname="Heerlen-Looierstraat", pachubeid="1676").put()
    
    # Create sample data for the stations
    from datetime import timedelta
    
    ParticulateData(stationid="131", value=10, date=date.today()).put()
    ParticulateData(stationid="131", value=9, date=date.today()-timedelta(1)).put()
    ParticulateData(stationid="131", value=55, date=date.today()-timedelta(2)).put()

    ParticulateData(stationid="133", value=35, date=date.today()).put()
    ParticulateData(stationid="133", value=23, date=date.today()-timedelta(1)).put()
    ParticulateData(stationid="133", value=45, date=date.today()-timedelta(2)).put()

    ParticulateData(stationid="136", value=90, date=date.today()).put()
    ParticulateData(stationid="136", value=25, date=date.today()-timedelta(1)).put()
    ParticulateData(stationid="136", value=5, date=date.today()-timedelta(2)).put()