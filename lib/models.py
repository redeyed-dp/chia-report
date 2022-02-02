from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy import create_engine, event, Column, Integer, String, ForeignKey, Enum

engine = create_engine('sqlite:///cache.db')

# Foreign key isn't work in SQLite without this
def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('pragma foreign_keys=ON')
event.listen(engine, 'connect', _fk_pragma_on_connect)

Base = declarative_base()
session = Session(engine)

class Disk(Base):
    __tablename__ = 'disk'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(15), nullable=False)
    name = Column(String(10), nullable=False)
    description = Column(String(32))
    vendor = Column(String(32))
    product = Column(String(32))
    serial = Column(String(32))
    size = Column(String(32))
    partitions = relationship('Partition', backref="partitions", cascade='all,delete')

class Partition(Base):
    __tablename__ = 'partition'
    id = Column(Integer, primary_key=True)
    disk = Column(Integer, ForeignKey('disk.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(10), nullable=False)
    mountpoint = Column(String(128))
    size = Column(String(32))
    used = Column(String(32))
    available = Column(String(32))
    usage = Column(Integer)
    label = Column(String(32))
    uuid = Column(String(36))
    partuuid = Column(String(36))
    fstab = Column(Integer, default=0)

class Fstab(Base):
    __tablename__ = 'fstab'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(15), nullable=False)
    # Number of string in file
    sn = Column(Integer)
    # Type: comment, config or unknown
    st = Column(Enum('comment', 'config', 'unknown'))
    # Cleared string
    ss = Column(String(128), nullable=True)
    # Error description
    error = Column(String(128), nullable=True)

class Directory(Base):
    __tablename__ = 'directory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(15), nullable=False)
    path = Column(String(4096))
    used = Column(Integer, default=0)

class Pool(Base):
    __tablename__ = 'pool'
    id = Column(Integer, primary_key=True)
    ip = Column(String(15), nullable=False)
    pool = Column(String(32))
    errors = Column(String(2048))

# Create all tables
Base.metadata.create_all(engine)