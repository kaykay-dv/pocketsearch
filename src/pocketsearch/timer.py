import time

class Timer:

    def __init__(self,precision=5):
        self.start=time.time()
        self.precision = precision
        self.total_time = 0
        self.laps = []
        self.snapshots = 0 

    def lap(self,name):
        if len(self.laps) > 0:
            self.total_time+=time.time()-self.laps[-1:][0][1]        
        self.laps.append((name,time.time()))

    def snapshot(self,more_info=""):
        stop = time.time()
        self.snapshots=self.snapshots+1
        its = round(1/((stop-self.start)/self.snapshots),self.precision)
        out = "%s iterations %s it/s %s s elapsed %s%s" % (self.snapshots,its,round(stop-self.start,self.precision),more_info," "*15)
        print(out,end="\r",flush=True)

    def done(self):
        print()

    def __str__(self):
        s="----\n"
        longest_string, lap_time = max(self.laps, key=lambda x: len(x[0]))
        for lap_name , lap_time in self.laps:
            lap_name_display = lap_name + (len(longest_string)-len(lap_name)) * " "
            s=s+"%s %s s\n" % (lap_name_display , round(lap_time,self.precision))
        s=s+"Total time: %s\n" % self.total_time
        s=s+"----\n"
        return s  