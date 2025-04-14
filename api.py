from flask import Flask, jsonify, request
app = Flask(__name__)
import octaveBattery
import datetime


"""
capacity_kwh: <int>
maximum_power_kw: <int>
battery_id: <str>
power: <int>
soc: <float>
cycles: <float
alert: <Boolean>
date: <date> YYYY-MM-DD
timestamp: <timestamp> ISO 8601
"""


batteries = []

def get_battery(id):
    """
    returns battery with the provided ID
    or None if not found
    """
    global batteries
    for battery in batteries:
        if str(battery.battery_ID) == str(id):
            return battery
    return None




@app.route('/', methods=['POST'])
def create_battery():
    """
    Endpoint: POST request to /
    Request Body:
    {
    "capacity_kwh": <int>,
    "maximum_power_kw": <int>
    }

    capacity_kwh: Energy capacity in kWh.
    maximum_power_kw: Maximum power in kW.
    Behavior:
    Creates a new battery with the provided parameters.
    Every new battery starts at 50% SoC and is idle.
    A unique battery_id is assigned.
    Response:
    {
    "capacity_kwh": <int>,
    "maximum_power_kw": <int>,
    "battery_id": <str>
    }
    """ 
    battery_args = request.get_json()
    capacity = battery_args["capacity_kwh"]
    max_power = battery_args["maximum_power_kw"]
    battery = octaveBattery.OctaveBattery(capacity_kwh = capacity, maximum_power_kw = max_power)
    batteries.append(battery)
    return jsonify(battery.get_values([octaveBattery.CAPACITY_KWH, octaveBattery.MAX_POWER, octaveBattery.ID]))




@app.route('/<battery_id>', methods=['DELETE'])
def remove_battery(battery_id):
    """
    - **Endpoint**: **DELETE** request to `/{battery_id}`
    - **Behavior**: Removes the battery with the matching `battery_id`.
    """
    global batteries
    battery = get_battery(battery_id) 
    if battery is not None:
        batteries.remove(battery)
        msg = "battery delete: " + battery_id
        return jsonify({'message': msg}), 200
        
    return jsonify({'message': 'Battery not found'}), 400

@app.route('/soc', methods=['GET'])
def get_soc():
    """
    - **Endpoint**: **GET** request to `/soc`
    - **Response Format** (for all batteries):
    
    ```json
    [
      {"battery_id": <id>, "soc": <soc>},
      {"battery_id": <id>, "soc": <soc>},
      {"battery_id": <id>, "soc": <soc>}
    ]
    ```
    
    - **Optional Filtering**:
    - You can include a `battery_id` query parameter (e.g., `/soc?battery_id=<id>`) to retrieve the SoC for a specific battery.
    """
    output = []
    global batteries

    args = request.args.get('battery_id', None)
    print(args)
    if args is None:
        #return all battery SoC's
        for battery in batteries:
            output.append(battery.get_values([octaveBattery.ID, octaveBattery.SOC]))
        return jsonify(output), 200
    else:
        # get SoC from specific battery
        id = args
        battery = get_battery(id)
        output.append(battery.get_values([octaveBattery.ID, octaveBattery.SOC]))
    return jsonify(output), 200

    # employee = next((emp for emp in employees if emp['id'] == employee_id), None)
    # if employee:
    #     return jsonify(employee)
    # return jsonify({'message': 'Employee not found'}), 404

@app.route('/update', methods=['PUT'])
def set_power():
    """
    - **Endpoint**: **PUT** request to:
    
    ```
    /update?battery_id=<id>&power=<int>
    ```
    
    - **Behavior**:
    - A **positive `power`** value initiates charging.
    - A **negative `power`** value initiates discharging.
    - the absolute value of power should be limited by the `maximum_power_kw`  of the battery system.
    """
    bat_id = request.args.get('battery_id', None)
    power_val = request.args.get('power', None)
    if bat_id is None or power_val is None:
        msg = "bad request, put format should be: /update?battery_id=<id>&power=<int>"
        return jsonify({'message': msg}), 500
    
    power_val = int(power_val)
    print( type(power_val))
    print(bat_id, power_val)
    battery = get_battery(bat_id)
    battery.setPower(power_val)
    vals = battery.get_values([octaveBattery.POWER])
    print("vals: ", vals)
    power_applied = vals[octaveBattery.POWER]
    msg = "charge value applied: " + str(power_applied)
    return jsonify({'message': msg}), 200

@app.route('/most_cycles', methods=['GET'])
def get_most_cycles():
    """
    Endpoint: GET request to /most_cycles
    Query Parameters:
    date (optional): A date string (e.g., YYYY-MM-DD) specifying the period for cycle aggregation. If not provided, the endpoint defaults to the current day.
    Functionality:
    Returns the battery that recorded the highest number of cycles on that day.
    Response Format:
    {
    "battery_id": <id>,
    "cycles": <cycles>,
    "date": "<date>"
    }
    """
    global batteries

    date_str = request.args.get('date', None)
    if date_str is None:
        #no specified day, default to today
        date = datetime.datetime.today()
    else:
        #select specific day
        date_format = '%Y-%m-%d'
        date = datetime.datetime.strptime(date_str, date_format)

    max_cycles = 0
    max_cycle_id = 0
    for battery in batteries:
        cycles = battery.getCycles(date)
        if cycles > max_cycles:
            max_cycles = cycles
            max_cycle_id = battery.battery_ID
    if max_cycle_id == 0:
        # no batteries applicable
        msg = "there were no batteries"
        return jsonify({'message': msg}), 500
    return_vals = get_battery(max_cycle_id).get_values([octaveBattery.ID, octaveBattery.CYCLES])
    return_vals["date"] = date
    return jsonify(return_vals), 200

@app.route('/cycles', methods=['GET'])
def get_cycles():
    """
    - **Endpoint**: **GET** request to `/cycles`
    - **Response Format** (for all batteries):
    [
      {"battery_id": <id>, "cycles": <cycles>},
      {"battery_id": <id>, "cycles": <cycles>},
      {"battery_id": <id>, "cycles": <cycles>}
    ]
    - **Optional Filtering**:
    - Including a `battery_id` query parameter (e.g., `/cycles?battery_id=<id>`) returns the cycle count for that specific battery.
    """
    output = []
    global batteries

    args = request.args.get('battery_id', None)
    print(args)
    if args is None:
        #return all battery SoC's
        for battery in batteries:
            output.append(battery.get_values([octaveBattery.ID, octaveBattery.CYCLES]))
        return jsonify(output), 200
    else:
        # get SoC from specific battery
        id = args
        battery = get_battery(id)
        output.append(battery.get_values([octaveBattery.ID, octaveBattery.CYCLES]))
    return jsonify(output), 200

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Endpoint: GET request to /alerts
    Query Parameters:
    timestamp (optional): A string representing a specific point in time (e.g., in ISO 8601 format). If not provided, the endpoint defaults to the current timestamp.
    Functionality:
    Retrieves all battery systems that were in an alert state at the specified timestamp.
    A system is considered to be in alert if its SoC was above 90% or below 10% at that timestamp.
    Response Format:
    [
    {"battery_id": <id>, "soc": <soc>, "alert": true, "timestamp": "<timestamp>"},
    {"battery_id": <id>, "soc": <soc>, "alert": true, "timestamp": "<timestamp>"},
    {"battery_id": <id>, "soc": <soc>, "alert": true, "timestamp": "<timestamp>"}
    ]
    """
    global batteries

    timestamp_str = request.args.get('timestamp', None)
    if timestamp_str is None: 
        #assume current time
        time = datetime.datetime.now()
    else:
        #get time from timestamp_str iso 8601 assumed
        time = datetime.datetime.fromisoformat(timestamp_str)
    alert_output = []
    for battery in batteries:
        output_row = battery.get_values([octaveBattery.ID, octaveBattery.SOC, octaveBattery.ALERT, octaveBattery.TIME], time)
        if output_row[octaveBattery.ALERT]:
            alert_output.append(output_row)
    return jsonify(alert_output), 200


if __name__ == '__main__':
    app.run(debug=True)


