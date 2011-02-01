from google.appengine.ext import db
from google.appengine.tools import bulkloader

from datetime import date

import sys
sys.path.append('/Users/alper/Documents/projects/rivm/rivmsensor')

import models

# Download data from server
# appcfg.py download_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/mapping_download.csv --kind=PachubeMapping rivmsensor/
# appcfg.py download_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/data_download.csv --kind=ParticulateData rivmsensor/
# appcfg.py download_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/alert_download.csv --kind=TwitterAlert rivmsensor/

# Upload data to development
# appcfg.py upload_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/mapping_download.csv --kind=PachubeMapping --url=http://localhost:8080/remote_api rivmsensor/
# appcfg.py upload_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/data_download.csv --kind=ParticulateData --url=http://localhost:8080/remote_api rivmsensor/
# appcfg.py upload_data --config_file=rivmsensor/loaders.py --filename=rivmsensor/alert_download.csv --kind=TwitterAlert --url=http://localhost:8080/remote_api rivmsensor/


class PachubeMappingLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'PachubeMapping',
                                    [('stationid', str),
                                    ('stationname', str),
                                    ('pachubeid', str)])
        
class ParticulateDataLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'ParticulateData',
                                    [('stationid', str),
                                    ('value', int),
                                    ('date', lambda x: date(int(x.split('-')[0]), int(x.split('-')[1]), int(x.split('-')[2])))])

class TwitterAlertLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'TwitterAlert',
                                        [('stationid', str),
                                        ('amount', int),
                                        ('twittername', str)])

loaders = [PachubeMappingLoader, ParticulateDataLoader, TwitterAlertLoader]



class PachubeMappingExporter(bulkloader.Exporter):
    def __init__(self):
        bulkloader.Exporter.__init__(self, 'PachubeMapping',
                                    [('stationid', str, None),
                                    ('stationname', str, None),
                                    ('pachubeid', str, None)])
        
class ParticulateDataExporter(bulkloader.Exporter):
    def __init__(self):
        bulkloader.Exporter.__init__(self, 'ParticulateData',
                                    [('stationid', str, None),
                                    ('value', str, None),
                                    ('date', lambda x: x.date().isoformat(), None)])

class TwitterAlertExporter(bulkloader.Exporter):
    def __init__(self):
        bulkloader.Exporter.__init__(self, 'TwitterAlert',
                                    [('stationid', str, None),
                                    ('amount', str, None),
                                    ('twittername', str, None)])


exporters = [PachubeMappingExporter, ParticulateDataExporter, TwitterAlertExporter]