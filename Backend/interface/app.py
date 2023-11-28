from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, url_for
from helper_class import helper
import os
from time import sleep
#import backend_rpi_tunnel as brt
import ast
import threading
#import satnogsApi as satApi

# for testing - delete later
import random
import re

helpers = helper()

app = Flask(__name__)
satellite_id = 0
gs_id = 0
#sat_list = satApi.get_satellites_list()
#satellite_name = [sat_list]
#print(satellite_name)

# with open('../config.json', 'r') as file:
#     config = load(file)
# db_name = config["database"]["db_name"]

@app.route('/favicon.ico')
def favicon():
    app_directory = os.path.dirname(os.path.abspath(__file__))
    favicon_filename = 'favicon.ico'
    favicon_path = os.path.join(app_directory, favicon_filename)
    return send_from_directory(os.path.dirname(favicon_path), os.path.basename(favicon_path), mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def home():
    global satellite_id
    global gs_id
    if request.method == 'POST':
        tracking_mode = request.form.get('tracking-mode')
        data = {'tracking_mode': tracking_mode}

        if tracking_mode == 'MANUAL':
            groundstation_id = request.form.get('groundstation-id')
            priority = request.form.get('priority-manual')
            data['groundstation_id'] = groundstation_id
            data['priority'] = priority
            helpers.data_tunnel(data)
            helpers.open_tunnel(gs_id)
            #print(data)
            new_dict = {"process": "START"}
            helpers.send_commands(command=new_dict)
            sleep(5)
            return render_template('manual/manual.html')
        
        elif tracking_mode == 'AUTOTRACKING':
            satellite_id = request.form.get('satellite-id')
            priority = request.form.get('priority-auto')
            data['satellite_id'] = satellite_id
            data['priority'] = priority
            #print(f"AT data {data}")
            gs_id = helpers.data_tunnel(data)
            
            print(f"GSid in app {gs_id}")
            # append selected groundstation to data
            data['gs_id'] = gs_id

            helpers.open_tunnel(gs_id=gs_id)
            new_dict = {"process": "START"}
            helpers.send_commands(command=new_dict)
            return redirect(url_for('autotrack'))
    return render_template('index.html')

@app.route('/webcam', methods=['GET', 'POST'])
def webcam():
    return render_template('webcam/webcam.html')

@app.route('/stop_queue', methods=['POST'])
def stop_queue():
    print("Stopping queue - NOT WORKING!")
    return render_template('/')


@app.route('/manual', methods=['GET', 'POST'])
def manual():
    try:
        if request.method == 'POST':
            # tracking_mode = request.form.get('tracking-mode')
            # data = {'tracking_mode': tracking_mode}
            data = request.get_json()
            data = {key: value for key, value in data.items() if value != ''}
            response = helpers.send_commands(command=data)
            return render_template('manual/manual.html', endpointres=data)
    except Exception as e:
        print(f"Error in autotrack: {e}")
    return render_template('manual/manual.html', endpointres=None)

@app.route('/autotrack', methods=['GET', 'POST'])
def autotrack():
    checklock_thread = threading.Thread(target=helpers.check_notrack, args=(satellite_id, gs_id,))
    checklock_thread.start()
    helpers.send_auto_command(satellite_id, gs_id)
    return render_template('autotrack/autotrack.html', satellite_name=satellite_id)


import json

@app.route('/get_orientation')
def get_orientation():
    commanden = {'key': "PP"}
    response = helpers.send_commands(command=commanden)
    try:
        pattern = re.compile(r"'azimuth': (?P<azimuth>[\d.]+), 'elevation': (?P<elevation>[\d.]+)")

        # Find the matched pattern in the response string
        match = pattern.search(response[0])

        if match:
            azimuth = float(match.group("azimuth"))
            elevation = float(match.group("elevation"))
            print(f"Azimuth: {azimuth}, Elevation: {elevation}")
        else:
            print("No matching pattern found in the response.")
        return jsonify({'azimuth': azimuth, 'elevation': elevation})
    except:
        response = None
        if response is None:
            azimuth = 0
            elevation = 0
            return jsonify({'azimuth': azimuth, 'elevation': elevation})


def get_autotracking_info():
    return {"status": "Active", "next_pass": "2023-11-15 15:30:00"}

# Route to fetch autotracking information
@app.route('/autotracking_info')
def autotracking_info():
    data = get_autotracking_info()
    return jsonify(data)



if __name__ == '__main__':
    #from waitress import serve
    #serve(app, host="0.0.0.0", port=8080)
    try: 
        app.run(host='0.0.0.0', port=50005, debug=True)
    finally:
        helpers.close_connection()