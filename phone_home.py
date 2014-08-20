
# FIXME - in future we might want to make an AWS call that gives
# us into about the AMI that was launched (full name and description).
# Currently all we can do with the AMI-ID we get back from amazon
# is look in config.yml for our website, where it MAY match one of the
# official BioC AMIs. If we have other public AMIs whose usage we
# want to track we should revisit this, probably using boto
# to make a describe-images call (using an IAM user who can do
# nothing else).

# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras import json

import jinja2
import webapp2
import yaml
import urllib2
import pprint
import boto.ec2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'


# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)

def get_parent():
    return ndb.Key('phone-home Parent', 'phone-home Parent name')

def get_bioc_version(ami_id):
    response = urllib2.urlopen('https://raw.githubusercontent.com/Bioconductor/bioconductor.org/master/config.yaml') 
    obj = yaml.load(response)
    print("yaml obj is:")
    print(obj['ami_ids'])
    for k,v in obj['ami_ids'].iteritems():
        if v == ami_id:
            return k.replace("bioc", "").replace("_", ".")
    return None

def get_ami_info(ami_id):
    configfile = os.path.join(os.path.dirname(__file__), "config.yaml")
    stream = open(configfile, 'r')
    config = yaml.load(stream)
    conn = boto.ec2.connect_to_region("us-east-1",
        aws_access_key_id=config['amazon_access_key'],
        aws_secret_access_key=config['amazon_secret_key'])
    img = conn.get_all_images([ami_id])
    return({name: img[0].name, description: img[0].description})



class Greeting(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class AMILaunch(ndb.Model):
    """Models a launch of a BioC AMI"""
    is_bioc_account = ndb.BooleanProperty()
    is_aws_ip = ndb.BooleanProperty()
    ami_id = ndb.StringProperty()
    bioc_version = ndb.StringProperty()
    ami_name = ndb.StringProperty()
    ami_description = ndb.StringProperty()
    instance_type = ndb.StringProperty()
    region = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    availability_zone = ndb.StringProperty()


class AWSHandler(webapp2.RequestHandler):
    def post(self):
        # remote_addr shows up as "::1" when calling from localhost
        # or is it when using the simulated version of the 
        # GAE environment? not sure.
        # print("remote ip is %s" % self.request.remote_addr)
        raw = self.request.body
        try:
            obj = json.decode(raw)
        except ValueError:
            self.response.out.write("invalid json")
            return


        ami_launch = AMILaunch(parent=get_parent())
        ami_launch.is_bioc_account = obj['accountId'] == "555219204010"
        ami_launch.ami_id = obj['imageId']
        ami_launch.instance_type = obj['instanceType']
        ami_launch.region = obj['region']
        ami_launch.availability_zone = obj['availabilityZone']

        is_aws_ip("foo")

        ami_launch.bioc_version = get_bioc_version(obj['imageId'])

        ami_info = get_ami_info(obj['imageId'])
        ami_launch.ami_name = ami_info['name']
        ami.launch.ami_description = ami_info['description']

        ami_launch.put()

        self.response.out.write("hello\n")



# [START main_page]
class MainPage(webapp2.RequestHandler):

    def get(self):
        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        greetings_query = Greeting.query(
            ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
        greetings = greetings_query.fetch(10)

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'greetings': greetings,
            'guestbook_name': urllib.quote_plus(guestbook_name),
            'url': url,
            'url_linktext': url_linktext,
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))
# [END main_page]


class Guestbook(webapp2.RequestHandler):

    def post(self):
        # We set the same parent key on the 'Greeting' to ensure each Greeting
        # is in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate to a single entity group
        # should be limited to ~1/second.
        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        greeting = Greeting(parent=guestbook_key(guestbook_name))

        if users.get_current_user():
            greeting.author = users.get_current_user()

        greeting.content = self.request.get('content')
        greeting.put()

        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', Guestbook),
    ('/phone-home', AWSHandler)
], debug=True)

def is_aws_ip(ip):
    aws_ips="""72.44.32.0/19 (72.44.32.0 - 72.44.63.255) 
67.202.0.0/18 (67.202.0.0 - 67.202.63.255) 
75.101.128.0/17 (75.101.128.0 - 75.101.255.255) 
174.129.0.0/16 (174.129.0.0 - 174.129.255.255) 
204.236.192.0/18 (204.236.192.0 - 204.236.255.255) 
184.73.0.0/16 (184.73.0.0 - 184.73.255.255) 
184.72.128.0/17 (184.72.128.0 - 184.72.255.255)
184.72.64.0/18 (184.72.64.0 - 184.72.127.255) 
50.16.0.0/15 (50.16.0.0 - 50.17.255.255)
50.19.0.0/16 (50.19.0.0 - 50.19.255.255)
107.20.0.0/14 (107.20.0.0 - 107.23.255.255)
23.20.0.0/14 (23.20.0.0 - 23.23.255.255)
54.242.0.0/15 (54.242.0.0 - 54.243.255.255)
54.234.0.0/15 (54.234.0.0 - 54.235.255.255)
54.236.0.0/15 (54.236.0.0 - 54.237.255.255)
54.224.0.0/15 (54.224.0.0 - 54.225.255.255)
54.226.0.0/15 (54.226.0.0 - 54.227.255.255)
54.208.0.0/15 (54.208.0.0 - 54.209.255.255)
54.210.0.0/15 (54.210.0.0 - 54.211.255.255)
54.221.0.0/16 (54.221.0.0 - 54.221.255.255)
54.204.0.0/15 (54.204.0.0 - 54.205.255.255)
54.196.0.0/15 (54.196.0.0 - 54.197.255.255)
54.198.0.0/16 (54.198.0.0 - 54.198.255.255)
54.80.0.0/13 (54.80.0.0 - 54.87.255.255) 
54.88.0.0/14 (54.88.0.0 - 54.91.255.255)
54.92.0.0/16 (54.92.0.0 - 54.92.255.255)
54.92.128.0/17 (54.92.128.0 - 54.92.255.255)
54.160.0.0/13 (54.160.0.0 - 54.167.255.255)
54.172.0.0/15 (54.172.0.0 - 54.173.255.255)
50.112.0.0/16 (50.112.0.0 - 50.112.255.255)
54.245.0.0/16 (54.245.0.0 - 54.245.255.255)
54.244.0.0/16 (54.244.0.0 - 54.244.255.255)
54.214.0.0/16 (54.214.0.0 - 54.214.255.255)
54.212.0.0/15 (54.212.0.0 - 54.213.255.255)
54.218.0.0/16 (54.218.0.0 - 54.218.255.255)
54.200.0.0/15 (54.200.0.0 - 54.201.255.255)
54.202.0.0/15 (54.202.0.0 - 54.203.255.255)
54.184.0.0/13 (54.184.0.0 - 54.191.255.255)
54.68.0.0/14 (54.68.0.0 - 54.71.255.255)
204.236.128.0/18 (204.236.128.0 - 204.236.191.255)
184.72.0.0/18 (184.72.0.0 - 184.72.63.255)
50.18.0.0/16 (50.18.0.0 - 50.18.255.255)
184.169.128.0/17 (184.169.128.0 - 184.169.255.255)
54.241.0.0/16 (54.241.0.0 - 54.241.255.255)
54.215.0.0/16 (54.215.0.0 - 54.215.255.255)
54.219.0.0/16 (54.219.0.0 - 54.219.255.255)
54.193.0.0/16 (54.193.0.0 - 54.193.255.255)
54.176.0.0/15 (54.176.0.0 - 54.177.255.255)
54.183.0.0/16 (54.183.0.0 - 54.183.255.255)
54.67.0.0/16 (54.67.0.0 - 54.67.255.255) NEW
79.125.0.0/17 (79.125.0.0 - 79.125.127.255) 
46.51.128.0/18 (46.51.128.0 - 46.51.191.255)
46.51.192.0/20 (46.51.192.0 - 46.51.207.255)
46.137.0.0/17 (46.137.0.0 - 46.137.127.255)
46.137.128.0/18 (46.137.128.0 - 46.137.191.255)
176.34.128.0/17 (176.34.128.0 - 176.34.255.255)
176.34.64.0/18 (176.34.64.0 - 176.34.127.255)
54.247.0.0/16 (54.247.0.0 - 54.247.255.255)
54.246.0.0/16 (54.246.0.0 - 54.246.255.255)
54.228.0.0/16 (54.228.0.0 - 54.228.255.255)
54.216.0.0/15 (54.216.0.0 - 54.217.255.255)
54.229.0.0/16 (54.229.0.0 - 54.229.255.255)
54.220.0.0/16 (54.220.0.0 - 54.220.255.255)
54.194.0.0/15 (54.194.0.0 - 54.195.255.255)
54.72.0.0/14 (54.72.0.0 - 54.75.255.255)
54.76.0.0/15 (54.76.0.0 - 54.77.255.255)
54.78.0.0/16 (54.78.0.0 - 54.78.255.255)
54.74.0.0/15 (54.74.0.0 - 54.75.255.255)
185.48.120.0/22 (185.48.120.0 - 185.48.123.255)
54.170.0.0/15 (54.170.0.0 - 54.171.255.255)
175.41.128.0/18 (175.41.128.0 - 175.41.191.255)
122.248.192.0/18 (122.248.192.0 - 122.248.255.255)
46.137.192.0/18 (46.137.192.0 - 46.137.255.255)
46.51.216.0/21 (46.51.216.0 - 46.51.223.255)
54.251.0.0/16 (54.251.0.0 - 54.251.255.255) 
54.254.0.0/16 (54.254.0.0 - 54.254.255.255) 
54.255.0.0/16 (54.255.0.0 - 54.255.255.255)
54.179.0.0/16 (54.179.0.0 - 54.179.255.255)
54.169.0.0/16 (54.169.0.0 - 54.169.255.255)
54.252.0.0/16 (54.252.0.0 - 54.252.255.255)
54.253.0.0/16 (54.253.0.0 - 54.253.255.255) 
54.206.0.0/16 (54.206.0.0 - 54.206.255.255)
54.79.0.0/16 (54.79.0.0 - 54.79.255.255)
54.66.0.0/16 (54.66.0.0 - 54.66.255.255)
175.41.192.0/18 (175.41.192.0 - 175.41.255.255)
46.51.224.0/19 (46.51.224.0 - 46.51.255.255)
176.32.64.0/19 (176.32.64.0 - 176.32.95.255)
103.4.8.0/21 (103.4.8.0 - 103.4.15.255)
176.34.0.0/18 (176.34.0.0 - 176.34.63.255)
54.248.0.0/15 (54.248.0.0 - 54.249.255.255)
54.250.0.0/16 (54.250.0.0 - 54.250.255.255)
54.238.0.0/16 (54.238.0.0 - 54.238.255.255)
54.199.0.0/16 (54.199.0.0 - 54.199.255.255)
54.178.0.0/16 (54.178.0.0 - 54.178.255.255)
54.95.0.0/16 (54.95.0.0-54.95.255.255)
54.92.0.0/17 (54.92.0.0 - 54.92.127.255)
54.168.0.0/16 (54.168.0.0 - 54.168.255.255)
54.64.0.0/15 (54.64.0.0 - 54.65.255.255)
177.71.128.0/17 (177.71.128.0 - 177.71.255.255)
54.232.0.0/16 (54.232.0.0 - 54.232.255.255)
54.233.0.0/18 (54.233.0.0 - 54.233.63.255)
54.207.0.0/16 (54.207.0.0 - 54.207.255.255)
54.94.0.0/16 (54.94.0.0 - 54.94.255.255)
54.223.0.0/16 (54.223.0.0 - 54.223.255.255)
96.127.0.0/18 (96.127.0.0 - 96.127.63.255)
"""
    print("hi")
    ip_segs = ip.split(".")
