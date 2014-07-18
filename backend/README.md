
```
. ../env/bin/activate
pip install Flask
pip install Flask-SQLAlchemy
pip install py-bcrypt  # For simple authentication
pip install requests   # For requests to other services
pip install pyaml      # For config reading
pip install pyjade
```

Needed for MySQL
---------------------

```
yum install mysql-devel
pip install MySQL-python
```

HamlishJinja (being replaced with Jade)
----------------------------------------------

# Only necessary on dev machines, really:
yum install rubygem-haml

pip install git+http://github.com/Pitmairen/hamlish-jinja
# haml2hamlish.py ..


Site structure
------------------------------------------------------------
This assumes that there are two site 'levels' : 

* Main site

* subsites : 

  * Subsite1
  
    * project1
    
    * project2
    
    * project3
  
  * Subsite2
  
  * Subsite3

The Main Site as a SUPERUSER.  The subsites each have an ADMIN.  

The subsites each have a number of projects, and users.

The users have a 'dict' of permissions - and they can be allowed/denied access to individual projects.




Initialize database
============================

```
cd flask
rm sqlite_hackathon.db
python 
import www.database
www.database.create()
import www.models
www.models.User.ensure_superadmin(_password='PASSWORD-SUPER')
www.models.User.ensure_siteadmin(_password='PASSWORD-SITE')
www.models.User.ensure_client(1,_password='PASSWORD')
www.models.Site.ensure_exists(www.models.Site.tag_main)
www.models.Site.ensure_exists('subsite')
quit() 
```

```
python 
import www
site = www.models.Site.query().filter_by(tag='subsite').first()
site.bundle
site.set_data('test', 'temp_data','ewer')
www.models.Site.commit()
site.bundle
quit() 
```



Pull in Bootstrap
------------------

```
# in ./backend

wget https://github.com/twbs/bootstrap/releases/download/v3.2.0/bootstrap-3.2.0-dist.zip
unzip -t bootstrap-3.2.0-dist.zip
cp -R bootstrap-3.2.0-dist/* flask/www/static/
rm -rf bootstrap-3.2.0-dist.zip
rm -rf bootstrap-3.2.0-dist
```


cd assets/Theme
unzip Unify-theme_products-WB0412697.zip 
cd ../..
cp -R assets/Theme/HTML/assets/* flask/www/static/

# We've replaced back-to-top
#   so kill the overwritten copy and pull it back in from git
rm flask/www/static/plugins/back-to-top.js
git checkout -- flask/www/static/plugins/back-to-top.js



Set up nginx
---------------------

### NB: Need to enable nginx to access the static files directly
su ::
/usr/sbin/usermod -a -G sketchpad nginx 
chmod g+rx /home/userdirectory/


mkdir -p flask/www/templates
mkdir -p flask/www/static


## https://wrapbootstrap.com/
## Theme is Unify: expects its static assets under /assets/

cp -R assets/HTML/assets/* backend/flask/www/static/

cd flask
python run.py
# Browser : http://0.0.0.0:7882/
# http://0.0.0.0:7882/static/blog2.html

