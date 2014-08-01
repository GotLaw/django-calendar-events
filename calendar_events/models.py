from django.db import models
from django.contrib.auth.models import User
from dateutil.rrule import *
from datetime import datetime, timedelta
from django.utils.timezone import utc
from django.forms.util import from_current_timezone

# Create your models here.

FREQUENCY_CHOICES = (
    ('YEARLY','yearly'),
    ('MONTHLY','monthly'),
    ('WEEKLY','weekly'),
    ('DAILY','daily'),
)

class Event(models.Model):
    '''
    This class defines a calendar event instance, which may be one-time or recurring (using dateutil.rrule)
    '''
    name = models.CharField(max_length=36)
    startdatetime = models.DateTimeField(blank=True, null=True)
    enddatetime = models.DateTimeField(blank=True, null=True)
    allday = models.BooleanField(default=False)
    recurring = models.BooleanField(default=False)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, blank=True)
    byweekday = models.CharField(max_length=36, blank=True)
    until = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.allday == True:
            self.startdatetime = from_current_timezone(datetime(self.startdatetime.year, self.startdatetime.month, self.startdatetime.day))
            self.enddatetime = from_current_timezone(datetime(self.startdatetime.year, self.startdatetime.month, self.startdatetime.day + timedelta(days=1)))
        if self.until:
            self.until = from_current_timezone(self.until)
        super(Event, self).save(*args, **kwargs)

    def get_rule_params(self):
        return {
                'byweekday':[eval(day) if self.byweekday is not None else '' for day in eval(self.byweekday)],
                'until':self.until,
            }

    def get_recurrence_rule(self):
        '''
        Returns the dateutil.rrule object instance associated with this Event
        '''
        if self.rule:
            return rrule(eval(self.rule.frequency), dtstart=self.startdatetime, **self.get_rule_params())
        return None

    def get_event_occurrences(self, start, end):
        '''
        Accepts start and end datetime objects and returns a list of Event objects that fall between the start and end date arguments,
        representing occurrences of this particular event. 
        '''
        if self.rule:
            rule = self.get_recurrence_rule()
            recurrence_dates = rule.between(start, end, inc=True)
            duration = self.enddatetime - self.startdatetime
            events = [Event(
                id=self.id,
                name=self.name, 
                creator=self.creator, 
                rule=self.rule, 
                startdatetime=date,
                enddatetime=date+duration,
                allday=self.allday,
            ) for date in recurrence_dates]
            return events
        else:
            if (self.startdatetime >= start):
                return [self]
            else: 
                return []

    def get_occurrences(self, start, end):
        '''
        Accepts start and end datetime objects and returns a list of datetime objects that fall between the start and end date arguments
        according to this event's recurrence rule.
        '''
        rule = self.get_recurrence_rule()
        return rule.between(start, end, inc=True)

    def get_month_event_occurrences(self, *args, **kwargs):
        '''
        Takes a year and month as arguments and returns a list of datetime objects representing the 
        occurrences of the event during the specified month
        '''
        year = kwargs['year']
        month = kwargs['month']
        if month not in range(1, 13):
            raise Exception("Month must be between 1 and 12.")
        occurrences = self.get_occurrences(start=datetime(year, month, 1, tzinfo=utc), end=datetime(year, month+1, 1, tzinfo=utc))
        return occurrences 

    def get_week_event_occurrences(self, *args, **kwargs):
        '''
        Takes a year, and week as arguments and returns a list of datetime objects representing the occurrences 
        of the event during the specified week
        '''
        year = kwargs['year']
        week = kwargs['week']
        start_of_week = datetime.strptime(str(year) + str(week) +"0+0000","%Y%U%w%z")
        if week not in range(1,54):
            raise Exception("Week must be between 1 and 53")
        occurrences = self.get_occurrences(start=start_of_week, end=start_of_week+timedelta(weeks=1))
        return occurrences

    def to_fullcalendar(self):
        event_dict = {}
        event_dict['id'] = self.id
        event_dict['title'] = self.name
        event_dict['allDay'] = self.allday
        event_dict['start'] = self.startdatetime.isoformat()
        event_dict['end'] = self.enddatetime.isoformat()

        return event_dict

    def __str__(self):
        return self.name

class Occurrence(models.Model):
    '''
    Persists an occurrence instance of a recurring event to the database so that other objects can be associated to an occurrence.
    '''
    event = models.ForeignKey(Event)
