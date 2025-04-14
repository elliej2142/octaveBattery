
"""
### Parameters

Each `OctaveBattery` instance is defined by:

- **Capacity**: The energy storage capacity in kilowatt-hours (kWh).
- **Maximum Power**: The highest power level (in kW) the battery can charge or discharge. (Assume charging and discharging share the same limit.)
"""
import uuid
import datetime
from datetime import timedelta
import pandas as pd
import numpy as np

#defining unique dict/json field names
CAPACITY_KWH = "capacity_kwh"
MAX_POWER = "maximum_power_kw"
ID = "battery_id"
POWER = "power"
SOC = "soc"
CYCLES = "cycles"
ALERT = "alert"
DATE = "date"
TIME = "timestamp"

#TODO remove prints

class OctaveBattery():
    pass
    initial_SOC = 0.5
    def __init__(self, capacity_kwh, maximum_power_kw):
        """
        self.Capacity : the storage capacity of the battery in Kilowatt-Hours
        self.Maximum_Power : The max charge/discharge rate in kW
        self.battery_ID : unique ID number for the battery
        self.history_table : all events where a charge value was set for battery and when

        """
        
        self.Capacity = capacity_kwh
        self.Maximum_Power = maximum_power_kw
        self.battery_ID = uuid.uuid4()
        start_date = datetime.datetime.now()
        self.history_df = pd.DataFrame({POWER: [0], TIME: [start_date]})


    def calc_cycles(self, events=None, initSOC = initial_SOC, request_time = None):
        """
        used to return the cycles and state of charge given "events"
        """
        if events is None:
            # assume they meant the values from the full history
            events = self.history_df
        
        if request_time is None:
            # calculating the values up to now
            request_time = datetime.datetime.now()
        last_power = events.loc[events[TIME].idxmax()][POWER]
        temp_event = pd.DataFrame({POWER : [last_power], TIME : [request_time]})
        events = pd.concat([events, temp_event])
        events.reset_index(inplace=True, drop=True)

        soc = initSOC
        cycles = 0
        events.sort_values(by=[TIME])
        for i in range(len(events) - 1):
            current_power = events.iloc[i][POWER]
            current_time = events.iloc[i][TIME]
            next_time = events.iloc[i+1][TIME]
            duration_hours = (next_time - current_time).total_seconds()/60/60
            if abs(current_power) > self.Maximum_Power:
                current_power = self.Maximum_Power * (current_power / abs(current_power))
                # check the power limit
            calced_charge = current_power * duration_hours
            if current_power == 0:
                # nothing to evaluate
                continue
            elif current_power > 0:
                #we're charging
                #get smaller value of the calculated charge and the max capacity
                if (soc*self.Capacity) + calced_charge > self.Capacity:
                    #if we applied the charge then we would exceed capacity, so we are charging to 100%
                    soc = 1.0
                else:
                    #apply actual charge
                    charge_in_percent = calced_charge / self.Capacity
                    soc = soc + charge_in_percent
            elif current_power < 0:
                #we're discharging
                if (soc*self.Capacity) + calced_charge < 0:
                    # applying this charge would drain this battery below 0, set to zero
                    # the cycles applied is just the previous soc
                    cycles = cycles + soc
                    soc = 0
                else:
                    # apply actual discharge value and cycles
                    charge_in_percent = calced_charge / self.Capacity #note, negative value
                    cycles = cycles + abs(charge_in_percent)
                    soc = soc + charge_in_percent

        return float(soc), float(cycles)

    def add_event(self, power, date_time=None):
        """
        power: int indicating set charge/discharge rate in kw that was set at event
        date_time: time that event happened
        soc: state of charge at event time
        """
        if date_time is None:
            date_time = datetime.datetime.now()
        add = pd.DataFrame({POWER : [power], TIME : [date_time]})
        self.history_df = pd.concat([self.history_df, add])
        self.history_df.reset_index(inplace=True, drop=True)
        return self.history_df

    def override_history(self, new_hist):
        """
        THIS IS ONLY FOR DEBUGGING
        new_hist: dataframe in format
        index         power       datetime
        """
        self.history_df = new_hist

    def getPower(self, date=None):
        if date is None:
            # just return the current power
            return self.history_df.loc[self.history_df[TIME].idxmax()][POWER] #returning power where the time is the latest
        else:
            # return power just before provided date
            before_events = self.history_df[self.history_df[TIME] < date]
            if len(before_events) == 0:
                return 0 # we picked a time before the battery existed
            else:
                return before_events.loc[before_events[TIME].idxmax()][POWER] #returning power where the time is the last before provided date

    def getAlert(self, timestamp):
        soc, cycles = self.calc_cycles(request_time=timestamp)
        if soc < 0.10 or soc > 0.90:
            return True
        
        return False

    def getCycles(self, date=None):
        """
        option 1: no dates, total cycle count 
        option 2: need cycles from particular day
        option 3: need cycles from today
        """
        selected_events = []
        if date is None:
            #we need to return total cycles
            return self.calc_cycles()
        else:
            # we only want the data from one day
            # we need to get the last event from the previous day (if there is one)
            
            # set initial soc_val to be correct one for start of provided day
            # create temporary event at the end of the provided day with the power value of the last event from provided day
            # calc cycles from all events of provided day
            delta = timedelta(days=1)
            before_events = self.history_df[self.history_df[TIME] < date]
            set_days_events = self.history_df[self.history_df[TIME].between(date, (date+delta))]
            if len(set_days_events) > 0:
                last_from_set_day = set_days_events.loc[set_days_events[TIME].idxmax()]
            else:
                last_from_set_day = None # other checks prevent this from being used

            if len(before_events) > 0:
                # we have events from before and we need to consider the chance that the battery was discharging at midnight
                latest_from_before = before_events.loc[before_events[TIME].idxmax()]
                temp_event = pd.DataFrame({POWER: [latest_from_before[POWER]], TIME: [date]})
                before_events = pd.concat([before_events, temp_event])
                set_days_events = pd.concat([temp_event, set_days_events])
                init_soc, cycles = self.calc_cycles(events=before_events, request_time=date)
            else:
                # there are no before events, we can assume the SoC value will be the standard start value
                init_soc = self.initial_SOC
            
            if len(set_days_events) == 0:
                # if there are still not events added to today, no cycles occured
                return 0
            
            if last_from_set_day is not None:
                if last_from_set_day[POWER] < 0:
                    # if the last event from the selected day is discharging, then we need to potentially extrapolate it for the rest of the day
                    if (date+delta) < datetime.datetime.now():
                        #the end of the selected day is before now, so we are going to extrapolate
                        temp_event = pd.DataFrame({POWER: last_from_set_day[POWER], TIME: (date+delta)})
                        set_days_events = pd.concat[temp_event, set_days_events]
            selected_events = set_days_events
            soc, cycles = self.calc_cycles(events=selected_events, initSOC=init_soc, request_time=(date+delta))
            return cycles



    def setPower(self, charge):

        if abs(charge) > self.Maximum_Power:
            charge = self.Maximum_Power * (charge/ abs(charge)) # limit to max charge while maintaining whether we are charging or discharging

        self.add_event(power=charge)
        return charge

    def get_values(self, key_list, time=None):
        """
        returns dict of requested battery data
        """
        data = {}
        if CAPACITY_KWH in key_list:
            data[CAPACITY_KWH] = self.Capacity
        if MAX_POWER in key_list:
            data[MAX_POWER] = self.Maximum_Power
        if ID in key_list:
            data[ID] = self.battery_ID
        if POWER in key_list:
            data[POWER] = self.getPower()
        if SOC in key_list or CYCLES in key_list:
            soc, cycles = self.calc_cycles(request_time=time) #limiting extra query
            if SOC in key_list:
                data[SOC] = soc
            if CYCLES in key_list:
                data[CYCLES] = cycles
        if ALERT in key_list and time is not None:
            data[ALERT] = self.getAlert(time)
            data[TIME] = time

        return data
    
if __name__ == '__main__':
    #debugging things
    test_capat = 1000
    test_max_pow = 200
    test_bat = OctaveBattery(test_capat, test_max_pow)
    test_hist = [
        {POWER : 0, TIME : datetime.datetime(year=2025, month=4, day=10, hour=19, minute=21, second=0)},
        {POWER : -50, TIME : datetime.datetime(year=2025, month=4, day=11, hour=19, minute=21, second=0)},
        {POWER : 50, TIME : datetime.datetime(year=2025, month=4, day=11, hour=21, minute=21, second=0)},
        {POWER : 200, TIME : datetime.datetime(year=2025, month=4, day=11, hour=22, minute=21, second=0)},
        {POWER : -200, TIME : datetime.datetime(year=2025, month=4, day=12, hour=3, minute=21, second=0)},
        {POWER : 0, TIME : datetime.datetime(year=2025, month=4, day=12, hour=8, minute=21, second=0)},
        {POWER : 200, TIME : datetime.datetime(year=2025, month=4, day=12, hour=10, minute=45, second=0)},
        {POWER : 0, TIME : datetime.datetime(year=2025, month=4, day=12, hour=15, minute=45, second=0)},
        {POWER : -250, TIME : datetime.datetime(year=2025, month=4, day=13, hour=3, minute=45, second=0)},
        {POWER : 250, TIME : datetime.datetime(year=2025, month=4, day=13, hour=9, minute=0, second=0)},
        {POWER : 0, TIME : datetime.datetime(year=2025, month=4, day=13, hour=14, minute=30, second=0)},
    ]
    test_bat.override_history(pd.DataFrame(test_hist))
    print(test_bat.history_df)
    print("total cycles: ", test_bat.getCycles(datetime.datetime(year=2025, month=4, day=12)))
    print("current power: ", test_bat.getPower())
    print("prev_power: ", test_bat.getPower(date= datetime.datetime(year=2025, month=4, day=13, hour=9, minute=5, second=0)))
    print("setting power: ", test_bat.setPower(charge=200))
    print("current power: ", test_bat.getPower())
    exit()