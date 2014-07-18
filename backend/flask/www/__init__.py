from flask import Flask, request, Response, render_template, session
from werkzeug import ImmutableDict

import os # environ
import flask


if False:
  # https://github.com/Pitmairen/hamlish-jinja
  # http://overkrik.wordpress.com/2011/02/27/haml-and-flask/
  class FlaskWithHamlish(Flask):
      jinja_options = ImmutableDict(
          extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', 'hamlish_jinja.HamlishExtension']
      )
   
   
  #app = Flask(__name__)
  app = FlaskWithHamlish(__name__)
  app.jinja_env.hamlish_mode = 'indented' # if you want to set hamlish settings
  app.jinja_env.hamlish_indent_string = ' ' # Looking at source : https://github.com/Pitmairen/hamlish-jinja/blob/master/hamlish_jinja.py

  # New parameter
  app.jinja_env.hamlish_enable_div_shortcut=True


## This is jade by default now

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

app.secret_key = 'ENTER RANDOM STUFF HERE'
app.debug=True # Works in uwsgi environment

import platform
hostname = platform.uname()[1]

# See http://docs.sqlalchemy.org/ru/latest/dialects/sqlite.html#connect-strings
app.config['DATABASE'] = 'sqlite:///sqlite_hackathon.db' # Relative URL
app.config['SENDMAIL'] = False
app.config['SENDMAIL_FILE'] = 'mime_message.txt'
if hostname == 'example.com':
    app.config['DATABASE'] = 'sqlite:////home/USERNAME/hackathon-starter-flask-plus/backend/flask/sqlite_hackathon.db' # Absolute URL
    app.config['SENDMAIL'] = True
    # app.debug=False  # This appears to be safe under uwsgi - 

app.config['DATABASE'] = os.environ.get('FLASK_OVERRIDE_DB', app.config['DATABASE'])

# Pull in routes
import www.main
import www.auth
import www.admin

import www.database as db

@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()

@app.after_request
def after_request(response):
    db.session.commit()
    db.session.remove()
    return response

