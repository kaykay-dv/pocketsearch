import datetime
import re
import sqlite3
import time


def convert_timestamp(value):
    '''
    Convert native sqlite timestamp value to datetime object
    '''
    return datetime.datetime.strptime(value.decode("utf-8").split(".")[0], "%Y-%m-%d %H:%M:%S")


def convert_date(value):
    '''
    Convert native sqlite date value to datetime object
    '''
    return datetime.datetime.strptime(value.decode("utf-8"), "%Y-%m-%d").date()


sqlite3.register_converter('timestamp', convert_timestamp)
sqlite3.register_converter('date', convert_date)


def normalize(value):
    '''
    Default text normalization.
    '''
    value = re.sub(r'\b((?:[A-Za-z]\.){2,}(?:[A-Za-z]\.?)?)', lambda m: m.group(1).replace('.', ''), value)
    return value


class Timer:
    '''
    A helper class that displays
    a progress bar in console.
    '''

    def __init__(self, precision=5):
        self.start = time.time()
        self.stop = self.start
        self.precision = precision
        self.total_time = 0
        self.laps = []
        self.snapshots = 0

    def lap(self, name):
        '''
        Add a lap to the timer. A lap has a name and is automatically
        associated with the the current time.
        '''
        if len(self.laps) > 0:
            self.total_time += time.time()-self.laps[-1:][0][1]
        self.laps.append((name, time.time()))

    def get_its(self):
        '''
        Returns current number of iterations per second
        '''
        return round(1/((self.stop-self.start)/self.snapshots), self.precision)

    def snapshot(self, more_info=""):
        '''
        Prints out the current iteration and statistics on time consumed.
        more_info maybe used on what is actually done.
        '''
        self.stop = time.time()
        self.snapshots = self.snapshots+1
        its = self.get_its()
        out = "%s iterations %s it/s %s s elapsed %s%s" % (self.snapshots, its,
                                                           round(self.stop-self.start,
                                                                 self.precision),
                                                           more_info, " "*15)
        print(out, end="\r", flush=True)

    def done(self):
        '''
        Prints a newline on console.
        '''
        print()

    def __str__(self):
        s = "----\n"
        longest_string, lap_time = max(self.laps, key=lambda x: len(x[0]))
        for lap_name, lap_time in self.laps:
            lap_name_display = lap_name + \
                (len(longest_string)-len(lap_name)) * " "
            s = s+"%s %s s\n" % (lap_name_display,
                                 round(lap_time, self.precision))
        s = s+"Total time: %s\n" % self.total_time
        s = s+"----\n"
        return s
