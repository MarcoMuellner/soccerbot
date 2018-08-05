from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Federations(Base):
    __tablename__ = 'federations'

    id = Column(String,primary_key=True)
    clear_Name = Column(String)

    def __repr__(self):
        return f"Federations(id={self.id},clearName={self.clear_Name})"


class Competitions(Base):
    __tablename__ = 'competitions'

    id = Column(Integer,primary_key=True)
    federations_id = Column(String,ForeignKey('federations.id'))
    clear_name = Column(String)

    federation = relationship("Federations",back_populates="competitions")

    def __repr__(self):
        return f"Competitions(id={self.id},clearName={self.clear_name})"

class Seasons(Base):
    __tablename__ = 'seasons'

    id = Column(Integer,primary_key=True)
    federations_id = Column(String,ForeignKey('federations.id'))
    competitions_id = Column(Integer,ForeignKey('competitions.id'))
    clear_name = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    federation = relationship("Federations", back_populates="seasons")
    competitions = relationship("Competitions", back_populates="seasons")

    def __repr__(self):
        return f"Seasons(id={self.id},clearName={self.clear_name})"

class Teams(Base):
    __tablename__ = 'teams'

    id = Column(Integer,primary_key=True)
    clear_name=Column(String)
    short_name=Column(String)

    def __repr__(self):
        return f"Teams(id={self.id},clearName={self.clear_name})"

class Matches(Base):
    __tablename__ = 'matches'

    id = Column(Integer,primary_key=True)
    competitions_id = Column(Integer, ForeignKey('competitions.id'))
    seasons_id = Column(Integer, ForeignKey('seasons.id'))
    home_team_id = Column(Integer, ForeignKey('teams.id'))
    away_team_id = Column(Integer, ForeignKey('teams.id'))
    matchday = Column(Integer)
    date = Column(DateTime)
    score_home_team = Column(Integer,nullable=True,default=None)
    score_away_team = Column(Integer,nullable=True,default=None)

    competitions = relationship("Competitions", back_populates="matches")
    seasons = relationship("Seasons", back_populates="matches")
    home_team = relationship("Teams", back_populates="matches")
    away_team = relationship("Teams", back_populates="matches")

    def __repr__(self):
        return f"Teams(id={self.id},homeTeam={self.home_team}, awayTeam={self.away_team},matchday={self.matchday})"

