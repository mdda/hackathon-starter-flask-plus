import sqlalchemy as sa
import www.database as db

from sqlalchemy.orm.attributes import flag_modified

import bcrypt  # for passwords
import hashlib # for invitation tokens

import string # Template

from json import dumps, loads
from sqlalchemy.ext.mutable import Mutable
#class JSON_Mutable(sa.types.TypeDecorator, Mutable):
class JSONstore(sa.types.TypeDecorator):
    impl=sa.types.Text

    def process_bind_param(self, value, dialect):
        #print "BINDING : %s" % value
        return dumps(value)

    def process_result_value(self, value, dialect):
        #print "RESULT : %s" % value
        return loads(value)

class User(db.orm):
    __tablename__ = 'users'
    
    id = sa.Column(sa.Integer, primary_key=True)
    site_tag = sa.Column(sa.String(20), index=True)
    email= sa.Column(sa.String(200))  # Must be in lower case
    name = sa.Column(sa.String(60))
    pw_hash = sa.Column(sa.String(64))
    
    #bundle = sa.Column(sa.PickleType)
    #def _bundle_modified(self): flag_modified(self, 'bundle')
    bundle = sa.Column(JSONstore)
    def _bundle_modified(self): return flag_modified(self, 'bundle')

    ## This has a major problem if perms={} is a potential parameter...  
    ## So, don't do it - somehow it doesn't get cleared from one user to the next
    def __init__(self, _site_tag, _email, _name):
        #print "\n\nCREATING USER %s - %s" % (_email, _perms, )
        self.id=None  # Not logged in
        self.site_tag = _site_tag
        self.email = _email.lower()
        self.name = _name
        self.pw_hash=None
        self.bundle = { 'perms':dict(), }
    
    def set_password(self, passwd):
        self.pw_hash = bcrypt.hashpw(passwd, bcrypt.gensalt())
    
    @staticmethod
    def _constant_time_compare(val1, val2):
        '''Returns True if the two strings are equal, False otherwise.
        The time taken is independent of the number of characters that match.
        See : https://github.com/maxcountryman/flask-bcrypt/blob/master/flask_bcrypt.py
        '''
        if len(val1) != len(val2):
            return False
        
        result = 0
        for x, y in zip(val1, val2):
            result |= ord(x) ^ ord(y)
        
        return result == 0
    
    @staticmethod
    def get_if_password_valid(site_tag, email, passwd):
        user = User.query().filter_by( site_tag=site_tag, email=email.lower() ).first()
        if user and User._constant_time_compare(bcrypt.hashpw(passwd, user.pw_hash), user.pw_hash):
            return user
        return None
    
    @staticmethod
    def get_from_email(site_tag, email):
        return User.query().filter_by( site_tag=site_tag, email=email.lower() ).first()
        
    def invitation_token(self):  # Only depends on self.id (=user_id)
        return hashlib.md5("%dUser._cosatmecmaebpaws,u.h)sph)" % (self.id,)).hexdigest()[:8]
    
    def password_unset(self):
        return self.pw_hash is None
    
    @staticmethod
    def _ensure_user(_site_tag, _email, _name, _password, admin_level='', proj='test'):
        user = User.query().filter_by( site_tag=_site_tag, email=_email.lower() ).first()
        if not user :
            #print "Creating User"
            user = User(_site_tag, _email, _name)
            user.set_password(_password)
            User.add(user)
        #print "Creating user.bundle = %s (BEFORE)" % (user.bundle,)
        
        if admin_level=='superadmin' and not user.has_permission('', 'superadmin'): 
            user.grant_permission('', 'superadmin')
            admin_level='admin' # Now treat as an admin...
            
        if admin_level=='admin' and not user.has_permission('', 'admin'):
            user.grant_permission('', 'admin')
            
        if proj and not user.has_permission(proj, 'access'):                   #print "Add project access permission"
            user.grant_permission(proj, 'access')
            if admin_level: # Grant the room:* rights
                user.grant_permission(proj, 'admin')
                user.grant_permission(proj, 'files')
                user.grant_permission(proj, 'invite')
            
        User.commit()
        #print "Creating user.bundle = %s" % (user.bundle,)
        return user
        
    @staticmethod
    def ensure_superadmin(_password):
        return User._ensure_user(Site.tag_main, 'root@example.com', 'SUPERADMIN', admin_level='superadmin', _password=_password)

    @staticmethod
    def ensure_siteadmin(_password):
        return User._ensure_user('subsite', 'admin@example.com', 'SITEADMIN', admin_level='admin', _password=_password)

    @staticmethod
    def ensure_client(num, _password):
        return User._ensure_user('subsite', 'client%d@example.com' % (num,), 'Client #%d- REGULAR' % (num,), _password=_password)

    """ MySQL :
    CREATE TABLE users ( id INTEGER NOT NULL AUTO_INCREMENT, site VARCHAR(20), email VARCHAR(200), name VARCHAR(60), pw_hash VARCHAR(64), PRIMARY KEY (id) );
    INSERT INTO users VALUES (NULL, 'subsite', 'client1@example.com', 'SUPERADMIN', '$2a$12dfdf$s2At');
    """

    def get_data(self, item, default=''):  
        return self.bundle.get(item, default)
        
    def set_data(self, item, value):  
        if self.bundle.get(item) != value:
            self.bundle[item]=value
            self._bundle_modified()
            #print "Setting User[%s][proj='%s'].%s = '%s'" % (self.id, item, self.bundle[item])

    def has_permission(self, proj, permission):
        if proj not in self.bundle['perms']:
            return False
        return permission in self.bundle['perms'][proj]

    def can_siteadmin(self):  # , site_tag_current
        #return (self.site_tag == site_tag_current and self.has_permission('', 'siteadmin')) or self.has_permission('', 'superadmin')
        return self.has_permission('', 'admin')

    def grant_permission(self, proj, permission):
        if proj not in self.bundle['perms']:
            self.bundle['perms'][proj]=dict()
        if permission not in self.bundle['perms'][proj]:
            self.bundle['perms'][proj][permission]=True
            self._bundle_modified()
            return True
        return False  ## Return value indicates whether change made

    def revoke_permission(self, proj, permission):
        if proj not in self.bundle['perms']:
            return
        if permission in self.bundle['perms'][proj]:
            del self.bundle['perms'][proj][permission]
            self._bundle_modified()
            return True
        return False  ## Return value indicates whether change made

    def list_projects(self, permission=''):
        if permission:
            return [proj for proj in self.bundle['perms'].iterkeys() if permission in self.bundle['perms'][proj]]
        else:
            return [proj for proj in self.bundle['perms'].iterkeys()]
            
    # @staticmethod
    def mailto(self, email=None):
        if email is None: email = self.email or ''
        components = email.replace('"','').split('@')
        return """<script type="text/javascript">
<!--
    var string1 = "%s";
    var string2 = "@";
    var string3 = "%s";
    var string4 = string1 + string2 + string3;
    document.write('<a href="' + "mail" + 'to:' + string1 + string2 + string3 + '"' +  ">" + string4 + "</a>");
//-->   
</script>   """ % (components[0], components[1] if len(components)>1 else '')


 
class Site(db.orm):
    __tablename__ = 'site'
    id = sa.Column(sa.Integer, primary_key=True)
    
    tag  = sa.Column(sa.String(20), index=True)
    
    tag_main = '__MAIN__'
    domain_to_tag = {
        # Local 'run'
        '0.0.0.0:7882':tag_main,
        
        # On b3
        'example.com':tag_main,
        'www.example.com':tag_main,
        
        # Special DNS entries
        'subsite.example.com':'subsite',
        # Test rig for single site 'subsite'
        'subsite.localhost':'subsite',
    }

    bundle = sa.Column(JSONstore)
    def _bundle_modified(self): return flag_modified(self, 'bundle')
    
    def __init__(self, tag, name):
        self.tag = tag
        self.bundle = {
        '':{  #  "project"='' is for site-wide data (especially chrome())
          'name':name,
          'footer':'Copyright 2013-2014',
          'perm_script':[],  # Default perm script
         },
        }
        
    @classmethod
    def ensure_exists(class_, tag=tag_main, proj='test'):
        site = Site.query().filter_by( tag=tag ).first()
        if not site :
            if tag == Site.tag_main:
                site = Site(Site.tag_main, 'RedCatLabs')
                site.bundle[''].update({ # This admin data is for all projects in the main site
                 'admin_name':'Admin Name : Main site',
                 'admin_phone':'+dd-dddd-dddd',
                 'admin_email':'admin@example.com',
                 'footer':"This site is a product of a Hackathon - Copyright 2013-2014",
                })
                Site.add(site)
            if tag == 'subsite':
                site = Site(tag, 'subsite playground')
                site.bundle[''].update({ # This admin data is for all projects in site 'subsite'
                 'admin_name':'Admin Name : sub-site',
                 'admin_phone':'+dd-dddd-dddd',
                 'admin_email':'admin@example.com',
                 'footer':"This site is a product of a Hackathon - Copyright 2013-2014",
                })
                site.bundle[proj]=dict()
                site.bundle[proj].update({ # This admin data is for the project proj (default = 'test')
                # 'watermark':'$ip - $email',
                })
                Site.add(site)
        Site.commit()
        return None
        
    def is_main(self):
        return self.tag == Site.tag_main
        
    def chrome(self, item, default=''):  # chrome only on "project"=''
        return self.bundle[''].get(item, default)
        
    def get_data(self, proj, item, default=''):  
        if proj not in self.bundle:
            return default  # No autovivification
        return self.bundle[proj].get(item, default)
        
    def set_data(self, proj, item, value):  
        if proj not in self.bundle:
            self.bundle[proj]=dict()
        #print "Setting Site[%s][proj='%s'].%s = '%s'" % (self.tag, proj, item, value)
        if self.bundle[proj].get(item) != value:
            self.bundle[proj][item]=value
            self._bundle_modified()
            #print "Setting Site[%s][proj='%s'].%s = '%s'" % (self.tag, proj, item, self.bundle[proj][item])
            #self.bundle.changed()
        #print "  Now   Site[%s][proj='%s'].%s = '%s'" % (self.tag, proj, item, self.conf[proj][item])
        
    def perm_script(self, proj): # Get permission script for a project  (set using set_data above)
        return self.get_data(proj, 'perm_script', [])
        
    def list_users(self):
        return User.query().filter_by( site_tag=self.tag ).all()
        
    def send_email(self, _from_name, _from_email, _to_name, _to_email, _subject, _body, _html=False):
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['From'] = '"%s" <%s>' % (_from_name, _from_email, )
        msg['To'] = '"%s" <%s>' % (_to_name, _to_email, )
        #msg['Cc'] = _cc
        msg['Subject'] = _subject

        bcc = _from_email   # For regulatory compliance, do a bcc to the sender

        text = _body
        
        if _html:
            html=_html
        else:
            html = text.replace("\n", "<br />")
            html = """\
<html>
  <head></head>
  <body>
    <p>%s
    </p>
  </body>
</html>
            """ % (html,)

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        if app.config['SENDMAIL']:
            import smtplib
            # Send the message via local SMTP server.
            s = smtplib.SMTP('localhost')
            
            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            s.sendmail(_from_email, [_to_email, bcc], msg.as_string())
            s.quit()
        else:
            # This is to allow the testing framework to do something...
            with open(app.config['SENDMAIL_FILE'], 'wb') as f:
                f.write(msg.as_string(unixfrom=False))
        return True

    @staticmethod
    def substitute_dollar_strings(str, g, link=None, name=None, email=None, ip=None, date=None):
        return string.Template(str).safe_substitute(
          link = link or '',
          name = name or g.user.name, 
          email = email or g.user.email,
          ip = g.ip,
          date = datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S'),
        )

import datetime
class Audit(db.orm):
    __tablename__ = 'audit'
    id = sa.Column(sa.Integer, primary_key=True)
    ts = sa.Column(sa.DateTime())
    
    ## This makes life more pleasant
    site_tag = sa.Column(sa.String(20), index=True)
    
    hash = sa.Column(sa.String(8))
    ip = sa.Column(sa.String(16))
    
    ## Overkill - the audit log could be on another machine
    #user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), index=True)
    
    ## More direct
    user_id = sa.Column(sa.Integer, index=True)
    
    project = sa.Column(sa.String(50), index=True)
    action = sa.Column(sa.String(50))
    target = sa.Column(sa.String(200))
    result = sa.Column(sa.String(20))
    
    ## Not actually used for test suite::
    #user = sa.orm.relationship("User", backref=sa.orm.backref('audit', order_by=id))

    def __init__(self, g, project, action, target, result=None):
        self.ts = datetime.datetime.now()
        self.site_tag = g.site.tag
        self.ip = g.ip
        self.hash = g.hash
        self.user_id = g.user.id
        self.project = project or ''
        self.action = action
        self.target = target
        self.result = result or ''

    def write(self):
        Audit.add(self)

from www import app  # instance_path

import os # path, makedirs
import flask # safe_join

class SubSite():
    basedir = None
    
    def __init__(self, user, project):
        self.basedir = flask.safe_join(os.path.join(app.instance_path, user.site_tag), project)
    
    def has_permission(self, filename):
        return False
        
    def absolute_filename(self, filename):
        return flask.safe_join(self.basedir, filename)
    
    def ensure_path(self):
        path = self.basedir
        try: # This avoids a race condition : http://stackoverflow.com/questions/273192/python-best-way-to-create-directory-if-it-doesnt-exist-for-file-write
            os.makedirs(path)
        except OSError:
            if os.path.exists(path): # We are nearly safe
                pass
            else: # There was an error on creation, so make sure we know about it
                raise            
    
    @staticmethod
    def split_path(path):
        allparts = []
        while 1:
            (most, last) = os.path.split(path)
            if most == path:  # sentinel for absolute paths
                allparts.insert(0, most)
                break
            elif last == path: # sentinel for relative paths
                allparts.insert(0, last)
                break
            else:
                path = most
                allparts.insert(0, last)
        return allparts

