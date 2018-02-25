# DO NOT RUN THIS IN PRODUCTION! It's for testing only

import os
import pprint
import random
import time
import datetime
import string
import hashlib

from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.ext import db

#pprint.pprint(os.environ.copy())

from phone_home import AMILaunch, get_parent

def randstring(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def random_date(start_time_string, end_time_string, format_string, random_number):
    """
    Get a time at a proportion of a range of two formatted times.
    start and end should be strings specifying times formated in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """
    dt_start = datetime.datetime.strptime(start_time_string, format_string)
    dt_end = datetime.datetime.strptime(end_time_string, format_string)

    start_time = time.mktime(dt_start.timetuple()) + dt_start.microsecond / 1000000.0
    end_time = time.mktime(dt_end.timetuple()) + dt_end.microsecond / 1000000.0

    random_time = start_time + random_number * (end_time - start_time)

    ret = datetime.datetime.fromtimestamp(random_time)#.strftime(format_string)
    # print(ret.__class__.__name__)
    return ret



for i in range(200):
    ami_launch = AMILaunch(parent=get_parent())
    account_id = randstring(12)
    ami_launch.is_bioc_account = bool(random.getrandbits(1))
    if ami_launch.is_bioc_account:
        account_id = "some consistent string"
    ami_launch.account_hash = hashlib.md5(account_id.encode()).hexdigest()
    ami_launch.ami_id = "ami-" + randstring(8)
    ami_launch.instance_type = randstring(5)
    ami_launch.region = randstring(6)
    ami_launch.availability_zone = randstring(9)
    ami_launch.ami_name = randstring(20)
    ami_launch.ami_description = randstring(30)
    ami_launch.bioc_version = randstring(3)
    #print(ami_launch)
    ami_launch.date = random_date("2000/01/01 00:00:00.000000", "2049/12/31 23:59:59.999999", '%Y/%m/%d %H:%M:%S.%f', random.random())
    #print(ami_launch.date)
    ami_launch.put()
