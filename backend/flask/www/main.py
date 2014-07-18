from www import app
from www.auth import requires_auth, login

from www.models import User, Site, Audit

from flask import request, Response, render_template, session
from flask import redirect, url_for, flash
from flask import json, jsonify
import flask # send_file and 'flask.g'

import os # isdir, isfile, listdir, normpath, getsize

@app.route('/', methods=['GET', 'POST'])
### The 'home_page()' function is required here to satisfy a dependency in admin.py
def home_page():
    #return redirect("http://www.example.com/", )
    return render_template('starter.jade')

@app.route('/landing', methods=['GET', 'POST'])
def landing_page():
    #return redirect("http://www.example.com/", )

    name = request.values.get('name', '')
    email = request.values.get('email', '')

    mailto=flask.g.user.mailto('info@example.com')
    return render_template('landing.v1.haml', name=name, email=email, mailto=mailto)
    
# @app.route('/beta-signup', methods=['GET', 'POST'])
@app.route('/beta-signup', methods=['POST'])
## @requires_auth
def beta_signup():
    print "send_beta-signup"

    err=False
    name = request.values.get('name', '')
    if len(name)==0: 
        flash(u'Please give us your name', 'beta')
        err=True
    email = request.values.get('email', '')
    if len(email)==0: 
        flash(u'Please give us your email address', 'beta')
        err=True

    if err:
        print "send_beta-signup FAILED : re-ask"
        return redirect(url_for('landing_page', name=name, email=email))

    text = render_template('beta-signup.email.haml', name=name, email=email, is_plain_text=True)
    html = render_template('beta-signup.email.haml', name=name, email=email, is_plain_text=False)
    
    sent = flask.g.site.send_email(
      flask.g.site.chrome('admin_name'), 
      flask.g.site.chrome('admin_email'), 
      flask.g.site.chrome('admin_name'), 
      flask.g.site.chrome('admin_email'), 
      "Red Cat Labs New User : %s" % (name),
      text, html
    )
    if sent:
        print "send_reset_link DONE"
    else:
        print "send_reset_link FAIL"

    return render_template('beta-signup.thankyou.haml', name=name, email=email)
    
@app.route('/comingsoon')
## @requires_auth
def coming_soon():
    # This is because the root route doesn't need a login on the main site
    if flask.g.site.is_main():
        #return render_template('main.home.haml', )
        return render_template('main.comingsoon.haml', )
    
    # for all the other sites, need to be logged in...
    return home_page_room_list()
    
@requires_auth
def home_page_room_list():
    print "User.id=%4d Email='%s' :: bundle='%s'" % (flask.g.user.id, flask.g.user.email, flask.g.user.bundle, )
    
    projects = []
    for i,proj in enumerate(sorted(flask.g.user.list_projects('access'))):
        summary = flask.g.site.get_data(proj, 'summary', 'No Summary Available')
        #f = DataRoom(flask.g.user, proj).absolute_filename('_summary.html')
        #if os.path.isfile(f):
        #    summary = open(f).read()
        active = 'active' if i==0 else ''
        projects.append({ 'i':i, 'name':proj, 'summary':summary, 'active':active })
    
    return render_template('roomlist.haml', projects=projects )

@app.route('/public')
def hello_world_public():
    return 'live - public'

@app.route('/private')
@requires_auth
def hello_world_private():
    return 'live - private'

@app.route('/test')
def hello_world_test():
    return render_template('blog2.haml')
    
@app.route('/ts-and-cs')
def terms_and_conditions():
    return render_template('ts-and-cs_SG.haml')  # Based on FAQ
    
@app.route('/privacy')
def privacy():
    return render_template('privacy_SG.haml')  # Based on FAQ
    

    
@app.errorhandler(404)
def page_not_found(e):
    print "404 for HOST=%s" %(request.host.lower(),)
    print "404 for PATH=%s" %(request.path, )
    flask.g.user = User(Site.tag_main, 'NonExistent@LandingPage.com', 'Not logged in')  # Creates a user with id=None
    #return render_template('404.haml'), 404
    return "", 404
    
