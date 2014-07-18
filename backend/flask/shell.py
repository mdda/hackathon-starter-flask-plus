import readline
from pprint import pprint

import os

# Set up the database before importing the Flask app.
TEST_DB = os.path.join(os.path.dirname(os.path.realpath(__file__)),'sqlite_hackathon_shell.db')
os.environ["FLASK_OVERRIDE_DB"] = "sqlite:///%s" % (TEST_DB, )
print "DB path : %s" % (TEST_DB,)

import www
# This forces the database to be linked to the tempfile
www.database.create()

from www.models import User, Site

#User.ensure_superadmin()
#User.ensure_siteadmin()
#User.ensure_client()

Site.ensure_exists()
#Site.ensure_exists('basic', proj='hackathon')


#user1 = User.ensure_siteadmin()
#print "TEST User1.id=%4d Email='%s' :: bundle='%s'" % (user1.id, user1.email, user1.bundle, )
        
#user2 = User.ensure_client()
#print "TEST User2.id=%4d Email='%s' :: bundle='%s'" % (user2.id, user2.email, user2.bundle, )

"""
user1 = User('bhc', 'email1', 'name1')
user1.grant_permission('', 'admin_level')
User.add(user1)
#user1.email='dgfdfgdfgd'
User.commit()
print "TEST User1.id[%s]  Email='%s' :: bundle='%s'\n\n" % (user1.id, user1.email, user1.bundle, )

user2 = User('bhc', 'email2', 'name2') #, {})
User.add(user2)
#user2.grant_permission('', 'aasdasddmin_level')
User.commit()
print "TEST User2.id[%s]  Email='%s' :: bundle='%s'\n\n" % (user2.id, user2.email, user2.bundle, )
"""


"""
class TestMe():
    data=None
    
    def __init__(self, _p={'b':'334334'}):
        print "TEST with p=%s" % (_p)
        self.data=_p

t1=TestMe()
t1.data = { 'a':'34342' }
t2=TestMe({})
"""

os.environ['PYTHONINSPECT'] = 'True'
