# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from webapp2_extras import json

import jinja2
import webapp2


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
        ami_launch.ami_id = obj['imageId']
        ami_launch.instance_type = obj['instanceType']
        ami_launch.region = obj['region']
        ami_launch.availability_zone = obj['availabilityZone']
        #hh


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
