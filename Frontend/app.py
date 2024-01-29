from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, url_for, Response, session
from helper_class import helper
import os
from time import sleep
import re
import threading
import pymysql

helpers = helper()
bypass_backend = True
app = Flask(__name__)
satellite_id = 0
gs_id = 0
app.secret_key = "hejjohnni"
sleep(1)


@app.route('/favicon.ico')
def favicon():
    app_directory = os.path.dirname(os.path.abspath(__file__))
    favicon_filename = 'favicon.ico'
    favicon_path = os.path.join(app_directory, favicon_filename)
    return send_from_directory(os.path.dirname(favicon_path), os.path.basename(favicon_path), mimetype='image/vnd.microsoft.icon')

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

@app.route('/webcam', methods=['GET', 'POST'])
def webcam():
    return render_template('webcam/webcam.html')

@app.route('/stop_queue', methods=['POST'])
def stop_queue():
    print("Stopping queue - NOT WORKING!")
    return render_template('/')

@app.route('/start-check', methods=['POST'])
def start_check():
    data = request.json
    print(data)
    entry, prio, tracking_mode, sat_id = helpers.data_tunnel(data)
    session['entry'] = entry
    session['prio'] = prio
    session['tracking_mode'] = tracking_mode
    session['sat_id'] = sat_id
    return jsonify({
        'status': 'checking started',
        'entry': entry,
        'prio': prio,
        'tracking_mode': tracking_mode,
        'sat_id': sat_id
    })

@app.route('/check-status', methods=['GET'])
def check_status():
    entry = request.args.get('entry', type=int)
    entry, tasks_in_front = helpers.check_available(entry)

    if entry is None:
        helpers.open_tunnel(gs_id=gs_id)
        session['redirect_to_autotrack'] = True
        return jsonify({'conditionMet': True})

    return jsonify({
        'conditionMet': False,
        'place_in_queue': entry,
        'tasks_in_front': tasks_in_front
    })

@app.route('/mathinew', methods=['GET', 'POST'])
def mathinew():
    trackingmode = session.get('tracking_mode')
    print(trackingmode)
    if trackingmode == 'MANUAL':
        return redirect(url_for('manual'))
    elif trackingmode == 'AUTOTRACKING' or trackingmode == 'AUTOINPUT':
        return redirect(url_for('autotrack'))
    else:
        return redirect(url_for(''))

@app.route('/manual', methods=['GET', 'POST'])
def manual():
    new_dict = {"process": "START"}
    helpers.send_commands(command=new_dict)
    sleep(3)
    try:
        if request.method == 'POST':
            data = request.get_json()
            data = {key: value for key, value in data.items() if value != ''}
            response = helpers.send_commands(command=data)
            return render_template('manual/manual.html', endpointres=data)
    except Exception as e:
        print(f"Error in autotrack: {e}")
    return render_template('manual/manual.html', endpointres=None)

@app.route('/autotrack', methods=['GET', 'POST'])
def autotrack():
    sat_id = session.get('sat_id')
    if not bypass_backend:
        pass
        try:
            checklock_thread = threading.Thread(target=helpers.check_notrack, args=(sat_id, gs_id,))
            checklock_thread.start()
        except:
            pass
    new_dict = {"process": "START"}
    helpers.send_commands(command=new_dict)
    sleep(3)
    helpers.send_auto_command(sat_id)
    start, stop = helpers.get_timestamps_for_satID(sat_id)
    return render_template('autotrack/autotrack.html', satellite_name=sat_id,satellite_start=start,satellite_stop=stop)

@app.route('/get_orientation')
def get_orientation():
    commanden = {'key': "PP"}
    response = helpers.send_commands(command=commanden)
    try:
        pattern = re.compile(r"'azimuth': (?P<azimuth>[\d.]+), 'elevation': (?P<elevation>[\d.]+)")
        match = pattern.search(response[0])

        if match:
            azimuth = float(match.group("azimuth"))
            elevation = float(match.group("elevation"))
            print(f"Azimuth: {azimuth}, Elevation: {elevation}")
        else:
            print("No matching pattern found in the response.")
        return jsonify({'azimuth': azimuth, 'elevation': elevation})
    except Exception as e:
        print(e)
        response = None
        if response is None:
            azimuth = 0
            elevation = 0
            return jsonify({'azimuth': azimuth, 'elevation': elevation})

@app.route('/get-latest-status')
def get_latest_status():
    db_info = {
        "host": "system-database.cwctijm9dz2w.eu-central-1.rds.amazonaws.com",
        "user": "admin",
        "password": "SunsetBeer",
        "database": "gs_system_database",
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor
    }

    try:
        connection = pymysql.connect(**db_info)

        with connection.cursor() as cursor:
            sql = """
            SELECT Dump 
            FROM Dump_Table 
            WHERE Dump != 'RPI_TIME' 
            ORDER BY Log_ID DESC 
            LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            status = result['Dump'] if result else 'No status available'

        return jsonify({"status": status})

    except Exception as e:
        print(f"Database query failed: {e}")
        return jsonify({"status": "Error fetching status"})

    finally:
        if connection:
            connection.close()



if __name__ == '__main__':
    #from waitress import serve
    #serve(app, host="0.0.0.0", port=8080)
    try: 
        app.run(host='0.0.0.0', port=50005, debug=True, use_reloader=False)
    finally:
        helpers.close_connection()