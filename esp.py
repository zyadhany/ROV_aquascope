from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------- Simulated ESP32 States ----------
default_speed = 200
right_speed_state = 0
left_speed_state = 0
pump_speed_state = 0
lamp_state = "OFF"
mock_temperature = "24.5"

def get_speed_from_request(default_val):
    """Helper to extract and safely parse the 'speed' query parameter"""
    speed_param = request.args.get('speed')
    if speed_param is not None:
        try:
            return int(speed_param)
        except ValueError:
            pass
    return default_val

# ======================================================
# ENDPOINT HANDLERS
# ======================================================

@app.route('/')
def handle_root():
    message = (
        "ESP32 Ready (Simulated)\n"
        "IP Address: 127.0.0.1\n"
        "Open URL: http://127.0.0.1:5000\n\n"
        "Movement:\n"
        "/forward\n"
        "/backward\n"
        "/left\n"
        "/right\n"
        "/stop\n\n"
        "Pump:\n"
        "/move_up\n"
        "/move_down\n"
        "/pump?speed=200\n"
        "/pump?speed=-200\n"
        "/pump?speed=0\n\n"
        "Motors direct speed:\n"
        "/motor/right?speed=200\n"
        "/motor/right?speed=-200\n"
        "/motor/right?speed=0\n"
        "/motor/left?speed=200\n"
        "/motor/left?speed=-200\n"
        "/motor/left?speed=0\n\n"
        "Slave Lamp:\n"
        "/light_on\n"
        "/light_off\n\n"
        "Status:\n"
        "/status\n"
    )
    return message, 200, {'Content-Type': 'text/plain'}

# ---------- MAIN MOVEMENT ----------

@app.route('/forward')
def handle_forward():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Forward, speed = {speed}")
    pump_speed_state = 0
    right_speed_state = -speed
    left_speed_state = speed
    
    return "Moving forward", 200, {'Content-Type': 'text/plain'}

@app.route('/backward')
def handle_backward():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Backward, speed = {speed}")
    pump_speed_state = 0
    right_speed_state = speed
    left_speed_state = -speed
    
    return "Moving backward", 200, {'Content-Type': 'text/plain'}

@app.route('/left')
def handle_left():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Left, speed = {speed}")
    pump_speed_state = 0
    right_speed_state = speed
    left_speed_state = speed
    
    return "Turning left", 200, {'Content-Type': 'text/plain'}

@app.route('/right')
def handle_right():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Right, speed = {speed}")
    pump_speed_state = 0
    right_speed_state = -speed
    left_speed_state = -speed
    
    return "Turning right", 200, {'Content-Type': 'text/plain'}

# ---------- PUMP ----------

@app.route('/move_up')
def handle_up():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Pump UP, speed = {speed}")
    right_speed_state = 0
    left_speed_state = 0
    pump_speed_state = -speed
    
    return "Pump UP", 200, {'Content-Type': 'text/plain'}

@app.route('/move_down')
def handle_down():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(default_speed)
    
    print(f"Command: Pump DOWN, speed = {speed}")
    right_speed_state = 0
    left_speed_state = 0
    pump_speed_state = speed
    
    return "Pump DOWN", 200, {'Content-Type': 'text/plain'}

# ---------- STOP ----------

@app.route('/stop')
def handle_stop():
    global right_speed_state, left_speed_state
    print("Motors Stop")
    right_speed_state = 0
    left_speed_state = 0
    return "Motors stopped", 200, {'Content-Type': 'text/plain'}

@app.route('/pump_stop')
def handle_pump_stop():
    global pump_speed_state
    print("Pump Stop")
    pump_speed_state = 0
    return "Pump stopped", 200, {'Content-Type': 'text/plain'}

# ---------- DIRECT SPEED CONTROL ----------

@app.route('/motor/right')
def handle_right_motor_speed():
    global right_speed_state
    speed = get_speed_from_request(0)
    
    print(f"Right motor speed = {speed}")
    right_speed_state = speed
    return "Right motor speed set", 200, {'Content-Type': 'text/plain'}

@app.route('/motor/left')
def handle_left_motor_speed():
    global left_speed_state, pump_speed_state
    speed = get_speed_from_request(0)
    
    print(f"Left motor speed = {speed}")
    pump_speed_state = 0
    left_speed_state = speed
    return "Left motor speed set", 200, {'Content-Type': 'text/plain'}

@app.route('/pump')
def handle_pump_speed():
    global right_speed_state, left_speed_state, pump_speed_state
    speed = get_speed_from_request(0)
    
    print(f"Pump speed = {speed}")
    right_speed_state = 0
    left_speed_state = 0
    pump_speed_state = speed
    return "Pump speed set", 200, {'Content-Type': 'text/plain'}

# ---------- STATUS & SENSORS ----------

@app.route('/status')
def handle_status():
    print("SlaveSerial Action: Sent 'TEMP' request packet")
    
    status = (
        "ESP32 Ready\n"
        "IP Address: 127.0.0.1\n"
        f"Network: Simulated_ROV_Network\n"
        f"Right motor speed: {right_speed_state}\n"
        f"Left motor speed: {left_speed_state}\n"
        f"Pump speed: {pump_speed_state}\n"
        f"Temperature: {mock_temperature} C\n"
    )
    return status, 200, {'Content-Type': 'text/plain'}

@app.route('/sensors')
def handle_sensors():
    # print("SlaveSerial Action: Sent 'TEMP' request packet via /sensors")
    json_data = {
        "depth": 0,
        "front_distance": 0,
        "temp": mock_temperature
    }
    return jsonify(json_data)

@app.route('/light_on')
def handle_slave_lamp_on():
    global lamp_state
    print("SlaveSerial Command Injected: LAMP_ON")
    lamp_state = "ON"
    return "Slave Lamp ON", 200, {'Content-Type': 'text/plain'}

@app.route('/light_off')
def handle_slave_lamp_off():
    global lamp_state
    print("SlaveSerial Command Injected: LAMP_OFF")
    lamp_state = "OFF"
    return "Slave Lamp OFF", 200, {'Content-Type': 'text/plain'}

# ======================================================
# APPLICATION EXECUTION
# ======================================================
if __name__ == '__main__':
    print("\n================================")
    print("ESP32 Simulated Environment Ready")
    print("WiFi Network: Simulated_ROV_Network")
    print("ESP IP: http://127.0.0.1:8000")
    print("================================\n")
    
    # Running on port 8000 (can switch to 80 if executed with administrative sudo privileges)
    app.run(host='0.0.0.0', port=7000, debug=True)