from www import app
from www.models import User, Site, Audit

from flask import request, render_template, session
from flask import flash, redirect, url_for, abort
import flask

#import os # for environ['SERVER_NAME']
from os import urandom # for hashing of machine / session

##  Test at # Browser : http://0.0.0.0:7882/user/login :: This is the MAIN site

##  Test at # Browser : http://subsite.localhost:7882/user/login :: This is the subsite site
##  Test at # Browser : http://subsite.example.com:7882/user/login :: This is the subsite site

@app.before_request
def before_request():
    #print "REQUEST_HOST='%s'" % (request.host,)
    host_name = request.host.lower()
    # if ':' in host_name: host_name = host_name[:host_name.find(':')]
    
    if host_name in Site.domain_to_tag:
        # This is for DNS resolved versions
        site_tag = Site.domain_to_tag[host_name]
    else:
        # This is for subdomains of the main site : Just strip off the subdomain
        site_tag = host_name[:host_name.find('.')].lower()
       
    #print "REQUEST_HOST_TAG='%s'" % (site_tag,)
        
    flask.g.site = Site.query().filter_by(tag=site_tag).first()
    if flask.g.site is None:
        print "FAILED TO FIND SITE_TAG : DEFAULTING"
        # Default if all else fails
        flask.g.site = Site.query().filter_by(tag=Site.tag_main).first()
    
    if 'userid' in session:
        flask.g.user = User.get(session['userid'])
    else:
        flask.g.user = User(flask.g.site.tag, 'NonExistent@redcatlabs.com', 'Not logged in')  # Creates a user with id=None
        
    #session.pop('hash')
    if 'hash' not in session:
        session['hash'] = ''.join([ '%02x' % ord(ch) for ch in urandom(4) ])
        print "Created session hash '%s'" % (session['hash'],)
    flask.g.hash = session['hash']
        
    flask.g.ip = request.remote_addr

from functools import wraps
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        valid=False  # Definitely require a log-in to access
        if flask.g.user.id is not None: 
            # Ok, so we are a 'user' - but are we one the right site?
            if flask.g.user.site_tag == flask.g.site.tag:
                valid=True
            else:
                # site_tag doesn't match : is this user a superadmin (only case where it's Ok)
                if g.user.has_permission('', 'superadmin'): 
                    valid=True
                    
            #if flask.g.site == Site.tag_main:  # Special handling for main site ?
            #    valid=NONO - unless an admin of a sitelet
            
        if valid:
            return f(*args, **kwargs)   
        return redirect(url_for('login', next_url=request.path))
    return decorated


@app.route('/user/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next_url', '/')
    
    # if we are already logged in, go back to were we came from
    if flask.g.user.id is not None:
        Audit(flask.g, '', '/user/login', '', result='Already logged in').write()
        return redirect(next_url)
        
    if request.method == 'POST':
        email = request.form['email']
        user = User.get_if_password_valid(flask.g.site.tag, email, request.form['password'])
        print "Trying to Login : %s - %s" % (flask.g.site.tag, email, )
        if user:
            print "Trying to Login - SUCCESS"
            flask.g.user = user # Fix up g, so that Audit works
            Audit(flask.g, '', '/user/login', email, result='Success').write()
            session['userid']=user.id
            return redirect(next_url)
        else:
            print "Trying to Login - FAILURE"
            Audit(flask.g, '', '/user/login', email, result='Failure').write()
            flash("Email and password don't match", 'error')
    
    Audit(flask.g, '', '/user/login', '', result='').write()
    # Previous request.form rolls over to next iteration automatically
    return render_template('user.login.haml', next_url=next_url)

@app.route('/user/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'POST':
        email = request.form['email']
        user = User.get_from_email(flask.g.site.tag, email)
        print "Password Reset request : %s - %s" % (flask.g.site.tag, email, )
        if user:
            Audit(flask.g, '', '/user/reset', email, result='Success').write()
            send_reset_link(user)
            #return redirect(next_url)
        else:
            Audit(flask.g, '', '/user/reset', email, result='Failure').write()
        flash("Password Reset email sent : Click on the link in your email to create a new password", 'success')
    else:
        Audit(flask.g, '', '/user/reset', '', result='').write()
        
    return render_template('user.reset.haml', ) # next_url=next_url)
   

def send_reset_link(user):
    print "send_reset_link"
    #Audit(flask.g, '', url_here, '', result='Invite start').write()
    if user is None: return
    reset_link = url_for('user_reset_password_with_token', _external=True, user_id=user.id, token=user.invitation_token())
    text = render_template('user.reset.email.haml', link=reset_link, is_plain_text=True)
    html = render_template('user.reset.email.haml', link=reset_link, is_plain_text=False)
    
    sent = flask.g.site.send_email(
      flask.g.site.chrome('admin_name'), 
      flask.g.site.chrome('admin_email'), 
      user.name or 'DataRoom User', 
      user.email, 
      "DataRoom Password Reset",
      text, html
    )
    if sent:
        print "send_reset_link DONE"
    else:
        print "send_reset_link FAIL"

def check_password_acceptable(path, user, p1, p2):
    valid = True
    if len(p1) < 5:
        valid=False
        Audit(flask.g, '', '/user/new', user.email, result='Password blank').write()
        flash("Password verification error : Passwords must be 5 characters or longer", 'error')
    if p1 != p2:
        valid=False
        Audit(flask.g, '', '/user/new', user.email, result='Password mis-match').write()
        flash("Password verification error : Passwords don't match", 'error')
    return valid

@app.route('/user/new/<int:user_id>/<string:token>', methods=['GET', 'POST'])
def user_invite_with_token(user_id, token):
    return create_password_form(user_id, token, is_new=True)
    
@app.route('/user/reset/<int:user_id>/<string:token>', methods=['GET', 'POST'])
def user_reset_password_with_token(user_id, token):
    return create_password_form(user_id, token, is_new=False)

## This is common code for both invited users and reset passwords
def create_password_form(user_id, token, is_new=True):
    next_url = request.args.get('next_url', '/')
    
    url_here = '/user/new' if is_new else '/user/reset'
    Audit(flask.g, '', url_here, '', result='Invite start').write()
    
    # Sign the user out (just to make sure)
    session.pop('userid', None)
    
    form=dict(email='', password='', password2='')
    
    valid=False
    if is_new:
        msg = "Error : Your invitation is invalid - please ask for a new one"
    else:
        msg = "Error : This is not a valid password reset link"
    
    user = User.get(user_id)
    if user:
        token_target = user.invitation_token()
        if token_target.lower()==token.lower():
            form['email']=user.email
            valid=True
            Audit(flask.g, '', url_here, user.email, result='Arrived').write()
            
            if is_new :
                if not user.password_unset(): # This invitation has already been consumed...
                    Audit(flask.g, '', url_here, '', result='Invitation already used up').write()
                    valid=False
                    msg="Your invitation has already been used once - please use the Login tab above"
            else:
                user.password=None
                Audit(flask.g, '', url_here, '', result='Resetting Password').write()
                User.commit()
                
    if valid :
        if  request.method == 'POST':  # user has good data in it
            form['password']=request.form['password'].strip()
            valid=check_password_acceptable(url_here, user, form['password'], request.form['password2'])
            
            if 'ts_and_cs' in request.form:
                Audit(flask.g, '', url_here, user.email, result='Accepted Ts and Cs').write()
            else:
                valid=False
                Audit(flask.g, '', url_here, user.email, result='Did not accept Ts and Cs').write()
                flash("The Terms and Conditions must be accepted to continue", 'error')
                
            if valid: # HUGE success
                user.set_password(form['password'])
                User.commit()
                
                # Now log this user in too
                flask.g.user = user # Fix up g, so that Audit works
                Audit(flask.g, '', url_here, user.email, result='Set password').write()
                session['userid']=user.id
                
                return redirect(url_for('edit_profile', next_url=next_url))
    else:
        Audit(flask.g, '', url_here, "%d/%s" % (user_id, token, ) , result='Failure').write()
        flash(msg, 'error')
    
    return render_template('user.create-password.haml', form=form, next_url=next_url, is_new=is_new)
    

@requires_auth
@app.route('/user/profile', methods=['GET', 'POST'])
def edit_profile():
    here = url_for('edit_profile')
    next_url = request.args.get('next_url', here)  # This is circular
    user = flask.g.user

    Audit(flask.g, '', '/user/profile', '', result='').write()
    
    form=dict()
    form['password']=''
    form['password2']=''
    
    if request.method == 'POST': 
        valid = True
        if request.form['name']:
            user.name = request.form['name']
        else:
            valid = False
            flash(u'Error: you have to provide a contact name', 'error')

        if request.form['email']:
            user.email = request.form['email']
        else:
            valid = False
            flash(u'Error: you have to provide a contact email', 'error')
            
        if request.form['company']:
            user.set_data('company', request.form['company'])
        else:
            flash(u'Please provide a company name', 'warning')
            
        if request.form['phone']:
            user.set_data('phone', request.form['phone'])
        else:
            flash(u'Please provide a phone number', 'warning')
            
        if request.form['mobile']:
            user.set_data('mobile', request.form['mobile'])
            # Optional
            
        if valid:
            User.commit()
            if next_url == here:  # only flash if we're coming back here...
                Audit(flask.g, '', '/user/profile', '', result='Update Success').write()
                flash(u'Profile successfully updated', 'success')
            return redirect(next_url)
    
    form['name']=user.name
    form['email']=user.email
    form['company']=user.get_data('company', '')
    form['phone']  =user.get_data('phone', '')
    form['mobile'] =user.get_data('mobile', '')
        
    return render_template('user.profile.haml', form=form)
    
# @app.route('/user/request') ??  TODO

@app.route('/user/logout')
def logout():
    next_url = request.args.get('next_url', '/')
    session.pop('userid', None)
    flash(u'You have been signed out')
    Audit(flask.g, '', '/user/logout', '', result='').write()
    return redirect(next_url)

