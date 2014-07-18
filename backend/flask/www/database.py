## http://flask.pocoo.org/docs/patterns/sqlalchemy/
# http://packages.python.org/Flask-SQLAlchemy/

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from www import app

### http://flask.pocoo.org/docs/patterns/sqlite3/
### http://www.tutorialspoint.com/sqlite/sqlite_python.htm



print "Engine created with DATABASE=%s" % (app.config['DATABASE'],)
engine = create_engine(app.config['DATABASE'], convert_unicode=True) #, echo=True) 
#engine = create_engine('mysql://USER:PASSWORD@localhost/hackathon', pool_recycle=3600, convert_unicode=True)

session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

class ORMClass(object):
    @classmethod
    def query(class_):
        return session.query(class_)
        
    @staticmethod
    def query_element(*e):
        return session.query(*e)

    @classmethod
    def get(class_, id):
        return session.query(class_).get(id)

    @classmethod
    def add(class_, instance):
        session.add(instance)

    @classmethod
    def delete(class_, instance):
        session.delete(instance)

    @classmethod
    def commit(class_):
        session.commit()

orm = declarative_base(cls=ORMClass)

def create():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling create()
    import www.models
    orm.metadata.create_all(bind=engine)
    
