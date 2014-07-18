import os
import unittest
import tempfile
import re  # For analysing the mail message

# Set up the database before importing the Flask app.
TEST_DB = os.path.join(os.path.dirname(os.path.realpath(__file__)),'sqlite_hackathon_test.db')
os.environ["FLASK_OVERRIDE_DB"] = "sqlite:///%s" % (TEST_DB, )
print "DB path : %s" % (TEST_DB,)

import www

default_pw = 'abc123'  # This is for the throw-away test db

class HackathonTestCase(unittest.TestCase):
    def setUp(self):
        self.app = www.app.test_client()
        
        www.database.create()
        
        #www.models.User.ensure_superadmin(_password=default_pw)
        www.models.User.ensure_siteadmin(_password=default_pw)
        #www.models.User.ensure_client(1, _password=default_pw)
        
        www.models.Site.ensure_exists()
        www.models.Site.ensure_exists('subsite', proj='test')

    def tearDown(self):
        pass
        os.unlink(TEST_DB)
        

    def login(self, email, password):
        #print "TEST Login(%s)" % email
        return self.app.post('/user/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def login_superadmin(self):
        return self.login('root@example.com', default_pw)  # this is the siteadmin

    def login_siteadmin(self):
        return self.login('admin@example.com', default_pw)  # this is the siteadmin

    def login_client(self, num):
        return self.login('client%d@example.com' % num, default_pw)  # this is the siteadmin

    def logout(self):
        #print "TEST Logout()"
        return self.app.get('/user/logout', follow_redirects=True)
        
        
    def test_login_logout(self):
        www.models.User.ensure_siteadmin(_password=default_pw)
        
        rv = self.login('admin@example.com', default_pw)
        assert '<i class="icon-home">' in rv.data
        
        rv = self.logout()
        assert '<i class="icon-home">' not in rv.data
        assert 'Sign In to' in rv.data
        
        rv = self.login('admin@example.com', 'WRONG')
        assert 'Email and password don\'t match' in rv.data
        
        rv = self.login('4dmin@example.com', default_pw)
        assert 'Email and password don\'t match' in rv.data
        
        rv = self.login('aDMIn@example.com', default_pw)
        assert '<i class="icon-home">' in rv.data
        
        rv = self.logout()
        assert '<i class="icon-home">' not in rv.data
        assert 'Sign In to' in rv.data


    def test_password_reset(self):
        www.models.User.ensure_siteadmin(_password=default_pw)
        
        rv = self.app.get('/user/login')
        assert 'Request a' in rv.data
        assert '<a href="/user/reset">' in rv.data
        assert 'Password Reset' in rv.data
        
        mail_file = www.app.config['SENDMAIL_FILE']
        if os.path.exists(mail_file):
            os.remove(mail_file)

        rv = self.app.post('/user/reset', data=dict(
            email='FAKE EMAIL',
        ))  #, follow_redirects=True 
        assert 'Send Reset Password Email' in rv.data
        assert 'Password Reset email sent' in rv.data # Even though this is a fake email - the site won't complain

        assert not os.path.exists(mail_file), "Mail file created in error"
        
        rv = self.app.post('/user/reset', data=dict(
            email='ACTUALEMAIL@SOMESITE.COM',
        ))  #, follow_redirects=True 
        assert 'Send Reset Password Email' in rv.data
        assert 'Password Reset email sent' in rv.data

        assert os.path.exists(mail_file), "Mail not created for reset"
        
        with open(mail_file, 'rb') as f:
            str = f.read()
        
        if os.path.exists(mail_file):
            os.remove(mail_file)
        
        assert 'Content-Type: multipart/alternative;' in str
        
        ### From: "Martin Andrews" <mdda@example.com>
        m = re.search('^From: "([^"]+)" <([^>]+)>', str, flags = re.MULTILINE)
        assert m, 'From: line not found'
        assert m.group(1) == 'Martin Andrews'
        assert m.group(2) == 'mdda@brithill.com'
        
        assert 'Please use the following link to create a new password for your login to the site' in str
        
        ## http://localhost/user/reset/2/933b4906
        m = re.search('http://localhost/user/reset/(\d+)/([0-9a-f]+)', str, flags = re.MULTILINE)
        assert m, 'LINK line not found'
        
        reset_link = '/user/reset/%d/%s' % (int(m.group(1)), m.group(2))
        
        print "RESET LINK = %s" % (reset_link, )
        
        ## Go to invited page with a bad link
        rv = self.app.get(reset_link+'XXYY')
        assert 'not a valid password reset link' in rv.data
        assert 'create a new password' in rv.data
        assert 'create your own password' not in rv.data
        
        ## Go to reset link page
        rv = self.app.get(reset_link)
        assert 'Your invitation is invalid' not in rv.data
        assert 'create a new password' in rv.data
        assert 'create your own password' not in rv.data
        #assert 'invitation has already been used once' not in rv.data
        
        ## Create a new password, omit Ts&Cs
        password = '1234abcd'
        rv = self.app.post(reset_link, data=dict(
            password=password,
            password2=password,
        ))
        assert 'must be accepted to continue' in rv.data
        
        ## Create a new password, and agree to Ts&Cs
        rv = self.app.post(reset_link, data=dict(
            password=password,
            password2=password,
            ts_and_cs=1,
        ), follow_redirects=True)
        assert 'must be accepted to continue' not in rv.data
        assert '<!-- Profile Update starts -->' in rv.data
        #print rv.data
        
        rv = self.logout()
        

    def test_client_access(self):
        www.models.User.ensure_client(1, _password=default_pw)
        rv = self.login_client(1)
        #quit()
        assert '<i class="icon-home">' in rv.data
        assert 'Edit DataRoom' not in rv.data
        assert 'Add Room' not in rv.data
        assert 'Invite New User' not in rv.data
        
        rv = self.app.get('/data/test', )        # follow_redirects=True
        assert 'File Listing' not in rv.data
        
        rv = self.app.get('/data/test', follow_redirects=True)
        assert 'Navigate the listings below' in rv.data
        
        rv = self.app.get('/data/MISSING/', )        # follow_redirects=True
        assert '<i class="icon-home">' in rv.data
        
        rv = self.logout()
        
        
    def test_client_access_denial(self):
        www.models.User.ensure_client(1, _password=default_pw)
        rv = self.login_client(1)
        rv = self.app.get('/admin/site', )        # follow_redirects=True
        assert '<i class="icon-home">' in rv.data
        assert 'Site Name' not in rv.data
        
        rv = self.app.get('/admin/users', )        # follow_redirects=True
        assert '<i class="icon-home">' in rv.data
        assert 'Site User List' not in rv.data
        
        #rv = self.app.get('/admin/audit', )        # follow_redirects=True
        #assert '<i class="icon-home">' in rv.data
        #assert 'Site User List' not in rv.data
        
        #rv = self.app.get('/super/sites', )        # follow_redirects=True
        #assert '<i class="icon-home">' in rv.data
        #assert 'Site User List' not in rv.data
        
        #rv = self.logout()

        
    def test_admin_access_success(self):
        www.models.User.ensure_siteadmin(_password=default_pw)
        rv = self.login_siteadmin()
        rv = self.app.get('/admin/site', follow_redirects=True)
        assert '<i class="icon-home">' not in rv.data
        assert 'Site Name' in rv.data
        
        rv = self.app.get('/admin/users', )        # follow_redirects=True
        assert '<i class="icon-home">' not in rv.data
        assert 'Site User List' in rv.data
        
        #rv = self.app.get('/admin/audit', )        # follow_redirects=True
        #assert '<i class="icon-home">' in rv.data
        #assert 'Site User List' not in rv.data
        
        #rv = self.app.get('/super/sites', )        # follow_redirects=True
        #assert '<i class="icon-home">' in rv.data
        #assert 'Site User List' not in rv.data
        
        #rv = self.logout()

    
import sys
if __name__ == '__main__':
    if len(sys.argv)>1:
        fast = unittest.TestSuite()
        fast.addTest(HackathonTestCase(sys.argv[1]))
        
        unittest.TextTestRunner(verbosity=2).run(fast)
    else: 
        unittest.main(verbosity=2)
