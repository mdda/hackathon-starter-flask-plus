from www import app
from www.auth import requires_auth, login, user_invite_with_token, user_reset_password_with_token, send_reset_link
from www.main import home_page

from flask import request, render_template, session
from flask import flash, redirect, url_for, abort
#from flask import jsonify
import flask # send_file and 'flask.g', Response

#import string # Template

from www.models import User, Site, SubSite, Audit

@requires_auth
@app.route('/admin/site', methods=['GET', 'POST'])
def admin_site():
    Audit(flask.g, '', '/admin/site', '').write()
    if not flask.g.user.can_siteadmin():
        Audit(flask.g, '', '/admin/site', '', result='NOT AUTHORIZED').write()
        return home_page()
    
    if request.method == 'POST':
        site = flask.g.site
        
        if request.form['name']:
            site.set_data('', 'name', request.form['name'])
        else:
            flash(u'Error: you have to provide a company name for your site', 'section_header')
            
        if request.form['admin_name']:
            site.set_data('', 'admin_name', request.form['admin_name'])
        else:
            flash(u'Error: you have to provide a contact name for your site', 'section_header')

        if request.form['admin_phone']:
            site.set_data('', 'admin_phone', request.form['admin_phone'])
        else:
            flash(u'Error: you have to provide a contact phone number for your site', 'section_header')

        if request.form['admin_email']:
            site.set_data('', 'admin_email', request.form['admin_email'])
        else:
            flash(u'Error: you have to provide a contact email address for your site', 'section_header')


        if request.form['about']:
            site.set_data('', 'about', request.form['about'])
        else:
            flash(u'Error: you have to have some \'about\' text', 'section_footer')
            
        if request.form['footer']:
            site.set_data('', 'footer', request.form['footer'])
        else:
            flash(u'Error: you have to have some footer text', 'section_footer')
            
        Site.commit()
            
    form=dict()
    for item in ['name','admin_name', 'admin_phone', 'admin_email', 'about', 'footer']:
        form[item]=flask.g.site.chrome(item)
            
    return render_template('admin.site.haml', form=form)
        
        
@requires_auth
@app.route('/admin/room', methods=['GET', 'POST'])
def admin_room_add():
    Audit(flask.g, None, '/admin/room', '*ADD*').write()
    if not flask.g.user.can_siteadmin():
        Audit(flask.g, None, '/admin/room', '*ADD*', result='NOT AUTHORIZED').write()
        return home_page()
        
    # TODO : Charge more??
    #print "adding a room"
    
    form=dict()
    form['name']=''
    
    if request.method == 'POST':
        site = flask.g.site
        
        proj_new = request.form['name'].strip()
        form['name']=proj_new
        
        if len(proj_new)==0: 
            flash(u'Error: you have to provide a project room name', 'section_create')
        elif proj_new == '..':
            flash(u'Error: invalid project room name', 'section_create')
        else:
            valid=True
            for c in '\\/*?#\'\"':
                if c in proj_new:
                    valid=False
                    flash(u'Error: project room name contains invalid character " %s "' % (c,), 'section_create')
            
            if valid:
                # Check whether this exists already
                if proj_new in flask.g.user.list_projects():
                    valid=False
                    flash(u'Error: project room already exists', 'section_create')
                    
            if valid:
                # Create entries for this 'siteadmin' user for the new project
                user = flask.g.user
                user.grant_permission(proj_new, 'access')
                user.grant_permission(proj_new, 'invite')
                user.grant_permission(proj_new, 'files')
                user.grant_permission(proj_new, 'admin')
                
                # Create entries in site for the new project
                site = flask.g.site
                site.set_data(proj_new, 'name', proj_new)
                site.set_data(proj_new, 'summary', '')
                
                site.set_data(proj_new, 'watermark', '$date : $email @ $ip')
                site.set_data(proj_new, 'invite_subject', 'Invitation to access a DataRoom')
                site.set_data(proj_new, 'invite_body', """
$name:

Please use the following link to become a user of the DataRoom service :

$link

If you would like assistance, please do not hesitate to contact the administrator listed at the top of the website.
""".strip())
                
                # and a directory on disk...
                DataRoom(user, proj_new).ensure_path()
                
                User.commit()
                Site.commit()
                
                return redirect(url_for('admin_room_edit', proj=proj_new))
    
    return render_template('admin.room.haml', create_proj=True, form=form)
        
@requires_auth
@app.route('/admin/room/<proj>', methods=['GET', 'POST'])
def admin_room_edit(proj):
    Audit(flask.g, proj, '/admin/room', '').write()
    if not flask.g.user.has_permission(proj, 'admin'):
        Audit(flask.g, proj, '/admin/room', '', result='NOT AUTHORIZED').write()
        return home_page()
        
    #print "editing a room"
    
    if request.method == 'POST':
        site = flask.g.site
        if request.form['summary']:
            site.set_data(proj, 'summary', request.form['summary'])
        else:
            flash(u'Error: you have to provide a summary for each room', 'section_summary')
            
        if request.form['invite_subject']:
            site.set_data(proj, 'invite_subject', request.form['invite_subject'])
        else:
            flash(u'Error: you should add an email invitation subject line for each room (can be personalized later)', 'section_invite')
            
        site.set_data(proj, 'watermark', request.form['watermark'])
            
        if request.form['invite_body']:
            site.set_data(proj, 'invite_body', request.form['invite_body'])
        else:
            flash(u'Error: you should add boilerplate email invitation body text for each room (can be personalized later)', 'section_invite')
            
        Site.commit()
            
    form=dict()
    for item in ['summary', 'watermark', 'invite_subject', 'invite_body']:
        form[item]=flask.g.site.get_data(proj, item)
            
    return render_template('admin.room.haml', create_proj=False, proj=proj, form=form)
        
        
@requires_auth
@app.route('/admin/users', methods=['GET', 'POST'])
@app.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
def admin_users(user_id=0):
    Audit(flask.g, None, '/admin/users', '').write()
    if not flask.g.user.can_siteadmin():
        Audit(flask.g, None, '/admin/users', '', result='NOT AUTHORIZED').write()
        return home_page()
        
    form=dict()
    
    if user_id==0:
        user = None
    else:
        user = User.get(user_id)
        print "Email='%s' :: perms='%s'" % (user.email, user.bundle['perms'], )
        
    rights = ['access', 'invite', 'files', 'admin']
    projects=[]
    for i,proj in enumerate(sorted(flask.g.user.list_projects('access'))):
        d = { 'i':i, 'name':proj, 'disabled':'', }
        for r in rights:
            d[r]=''
        projects.append(d)
    
    if user and user.site_tag == flask.g.site.tag: # Check that a user is selected and we can edit them
        Audit(flask.g, None, '/admin/users', 'user_id=%d' % (user.id,), result='accessing').write()
        if request.method == 'POST':
            valid = True
            if request.form['email']:
                if user.email != request.form['email']:
                    user.email = request.form['email']
                    flash(u'Email address updated', 'section_success')
            else:
                valid = False
                flash(u'Error: you have to provide an email address', 'section_edit')
                
            if request.form['name']:
                if user.name != request.form['name']:
                    user.name = request.form['name']
                    flash(u'User name updated', 'section_success')
            else:
                valid = False
                flash(u'Error: you have to provide the user\'s name', 'section_edit')
            
            if user.id != flask.g.user.id:  # Don't alter your own permissions!
                update = False
                for p in projects:
                    for r in rights:
                        if 'proj%d_%s' % (p['i'],r) in request.form:  # http://nesv.blogspot.com/2011/10/flask-gotcha-with-html-forms-checkboxes.html
                            #print "project[%s] %s checked" % (p['name'], r, )
                            if user.grant_permission(p['name'], r):
                                update = True
                        else:
                            #print "project[%s] %s unchecked" % (p['name'], r, )
                            if user.revoke_permission(p['name'], r):
                                update = True
    
                if update:
                    flash(u'Access Rights updated', 'section_success')
                
            if valid:
                User.commit()
                Audit(flask.g, None, '/admin/users', 'user_id=%d' % (user.id,), result='updated').write()
            else:
                Audit(flask.g, None, '/admin/users', 'user_id=%d' % (user.id,), result='FAILURE').write()

            if 'password_reset' in request.form:
                User.commit()  # In case the email address was updated
                send_reset_link(user)
                flash(u'Password Reset Email : Sent', 'section_success')

        form['user_id']=user.id 
        form['name']=user.name
        form['email']=user.email
        
        for p in projects:
            for r in rights:
                if user.has_permission(p['name'], r):
                    p[r]='checked'
            if user.id == flask.g.user.id:  # Don't alter your own permissions!
                p['disabled']='disabled'
    
    else:
        form['user_id']=0 # Zero is unassigned - and removes a lot of the RHS
        for i in ['name', 'email']:
            form[i] = ''
            
    # Build a list of users for this site_tag - for showing on the LHS
    users = []
    for u in flask.g.site.list_users():
        users.append({  # Flatten out the data (?WHY?)
         'id':u.id,
         'email':u.email,
         'name':u.name,
        })

    return render_template('admin.users.haml', form=form, users=users, projects=projects, rights=rights)

@requires_auth
@app.route('/admin/invite/<proj>', methods=['GET', 'POST'])
def admin_invite(proj):
    Audit(flask.g, proj, '/admin/invite', '').write()
    if not flask.g.user.has_permission(proj, 'invite'):
        Audit(flask.g, proj, '/admin/invite', '', result='NOT AUTHORIZED').write()
        return home_page()
        
    form=dict()
    form['mode']='form'
    form['invite_name']=''
    form['invite_email']=''
    
    form['invite_subject']=flask.g.site.get_data(proj, 'invite_subject', '')
    form['invite_body']   =flask.g.site.get_data(proj, 'invite_body', '')
    
    #print flask.g.site.bundle
    
    if request.method == 'POST':
        valid=True
        
        form['invite_email'] = request.form['invite_email'].lower().strip()
        if len(form['invite_email'])==0:
            flash(u'Error: you have to provide an email address', 'section_invite')
            valid=False
            
        form['invite_name'] = request.form['invite_name'].strip()
        if len(form['invite_name'])==0:
            flash(u'Error: you have to provide the user\'s name', 'section_invite')
            valid=False
        
        form['invite_subject'] = request.form['invite_subject']
        if len(form['invite_subject'])==0:
            flash(u'Error: you have to provide text for the email subject line', 'section_invite')
            valid=False
        
        form['invite_body'] = request.form['invite_body']
        if len(form['invite_body'])==0:
            flash(u'Error: you have to provide text for the email body', 'section_invite')
            valid=False
        
        if valid :
            email_to   = '&quot;%s&quot; &lt;%s&gt;' % (form['invite_name'], form['invite_email'], )
            email_from = '&quot;%s&quot; &lt;%s&gt;' % (flask.g.site.chrome('admin_name'), flask.g.site.chrome('admin_email'), )
            
            if request.form['mode']=='check':
                #print "FORM BUTTON : %s" % (request.form['check_button'],)
                if request.form['check_button']=='send':
                    user = User(flask.g.site.tag, form['invite_email'], form['invite_name'])
                    user.grant_permission(proj, 'access')
                    #user.set_password('')  # No password : user will be prompted (all attempts will fail)
                    
                    User.add(user)
                    User.commit()  # This sets up the user_id
                    
                    invite_link = url_for('user_invite_with_token', _external=True, user_id=user.id, token=user.invitation_token())
                    
                    for s in ['invite_subject', 'invite_body']:
                        #form[s+'_actual'] = Site.string.Template(request.form[s]).safe_substitute(
                        form[s+'_actual'] = Site.substitute_dollar_strings(request.form[s], flask.g,
                          link = invite_link,
                          name = form['invite_name'], 
                          email = form['invite_email'],
                        )
                    
                    sent = flask.g.site.send_email(
                      flask.g.site.chrome('admin_name'), 
                      flask.g.site.chrome('admin_email'), 
                      form['invite_name'], 
                      form['invite_email'], 
                      form['invite_subject_actual'],
                      form['invite_body_actual'],
                    )
                    
                    Audit(flask.g, proj, '/admin/invite', email_to, result='sent').write()
                    if sent :
                        flash(u'Email sent to %s !' % (email_to,), 'section_sent')
                    else:
                        flash(u'Email NOT sent to %s !' % (email_to,), 'section_invite')  # Looks like an error
                    
                    # Blank out the name and email addresses
                    form['invite_name']=''
                    form['invite_email']=''
                    
                else: # This will default to going back to the entry form
                    Audit(flask.g, proj, '/admin/invite', email_to, result='re-entry').write()
                    pass
                
            else: # if valid form entries, go into check mode for email
                form['mode']='check'
                form['email_to']=email_to
                form['email_from']=email_from
                
                for s in ['invite_subject', 'invite_body']:
                    #form[s+'_actual'] = string.Template(request.form[s]).safe_substitute(
                    form[s+'_actual'] = Site.substitute_dollar_strings(request.form[s], flask.g,
                      #link = 'http://THIS-SITE/user/new/0/123456789',
                      link = url_for('user_invite_with_token', _external=True, user_id=0, token='SAMPLE-ONLY'),
                      name = form['invite_name'], 
                      email = form['invite_email'],
                    )
                    
                Audit(flask.g, proj, '/admin/invite', email_to, result='checking').write()


        else: # Form was invalid, redo
            pass
    
    return render_template('admin.invite.haml', form=form, proj=proj) # proj is there to generate menu entry...

@requires_auth
@app.route('/admin/audit', methods=['GET', 'POST'])
def admin_audit():
    criteria=dict()
    for c in ['proj', 'email', 'action']:
        criteria[c] = request.form.get(c, None)
        if criteria[c]=='EMPTY': criteria[c]=None
    
    proj = criteria['proj']
    Audit(flask.g, proj, '/admin/audit', '').write()
    if not flask.g.user.can_siteadmin():
        Audit(flask.g, proj, '/admin/audit', '', result='NOT AUTHORIZED').write()
        return home_page()
        
    form = dict()
    crit_site = ( Audit.site_tag == flask.g.site.tag )
    
    form['projects']= Audit.query_element(Audit.project.distinct()).filter(crit_site).order_by(Audit.project).all()
    form['emails']  = Audit.query_element(Audit.user_id.distinct(), User.email).filter(crit_site).join(User, Audit.user_id == User.id).order_by(User.email).all()
    form['actions'] = Audit.query_element(Audit.action.distinct()).filter(crit_site).order_by(Audit.action).all()

    # http://stackoverflow.com/questions/2678600/how-do-i-construct-a-slightly-more-complex-filter-using-or-or-and-in-sqlalchem
    crit_extra = True
    clause=''
    
    if criteria['proj'] is not None:
        crit_extra = (Audit.project == criteria['proj'].strip()) 
        clause = ': Project = "%s"' % (criteria['proj'],)
        
    if criteria['email'] is not None:
        user = User.get(criteria['email'])
        if user and user.site_tag == flask.g.site.tag:
            crit_extra = (Audit.user_id == user.id) 
            clause = ': Email = "%s"' % (user.email,)
        
    if criteria['action'] is not None:
        crit_extra = (Audit.action == criteria['action'].strip()) 
        clause = ': Action = "%s"' % (criteria['action'],)
        
    trail = Audit.query_element(Audit, User.email).filter(crit_site).filter(crit_extra).order_by(Audit.ts.desc()).join(User, Audit.user_id == User.id).limit(100).all()
    
    form['clause']=clause
    return render_template('admin.audit.haml', form=form, trail=trail)


import os # path.normpath, path.isdir, path.join
from werkzeug import secure_filename
import json

### This is accessed from jQuery-File-Upload
@requires_auth
@app.route('/admin/upload/<proj>/', methods=['POST'])
@app.route('/admin/upload/<proj>/<path:path>', methods=['POST'])
def subsite_upload(proj, path=''):
    path = os.path.normpath(path)
    if path == '.': path=''
        
    print "Uploading to project(%s) : %s" % (proj, path, )
    #Audit(flask.g, proj, '/data', path, result='').write()
    
    if not flask.g.user.has_permission(proj, 'files'):
        Audit(flask.g, proj, '/admin/upload', '', result='NOT AUTHORIZED').write()
        return home_page()
    
    full_path = DataRoom(flask.g.user, proj).absolute_filename(path)
    print "Full Path : %s" % (full_path,)
    if not os.path.isdir(full_path):
        return "FAILURE"
    
    ### Code taken from http://stackoverflow.com/questions/11817182/uploading-multiple-files-with-flask
    response_data = []
    for f in request.files.getlist("files[]"):
        name_secure = secure_filename(f.filename)
        response_data.append(dict(
          name=name_secure ,
          size=f.content_length,
          type=f.content_type,
        ))
        f.save(os.path.join(full_path, name_secure))
        Audit(flask.g, proj, '/admin/upload/', os.path.join(path, name_secure), result='Ok').write()
    
    # See : http://stackoverflow.com/questions/12435297/how-do-i-jsonify-a-list-in-flask
    #return jsonify(response_data)
    return flask.Response(json.dumps(response_data),  mimetype='application/json')

