import json
import openvr
import sys
import os
import time
import traceback
import ctypes
import argparse
from pythonosc import udp_client


def get_absolute_path(relative_path) -> str:
    """
    Gets absolute path from relative path
    Parameters:
        relative_path (str): Relative path
    Returns:
        str: Absolute path
    """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def cls() -> None:
    """
    Clears Console.
    Returns:
        None
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def get_debug_string(parameter, value, floating="") -> str:
    """
    Gets a string for the debug output.
    Parameters:
        parameter (str): Name of the parameter
        value (any): Value of the parameter
        floating (str): Floating value of the parameter
    Returns:
        str: Debug output string
    """

    if isinstance(value, float):
        value = f"{value:.4f}"

    tmp = ""
    if floating != "" and float(floating) > 0:
        tmp = f"Floating: {floating}s"
    return f"{parameter.ljust(23, ' ')}\t{str(value).ljust(10, ' ')}\t{tmp}\n"


def print_debugoutput() -> None:
    """
    Prints the debugoutput string.
    Returns:
        None
    """
    global config
    
    _debugoutput = ""
    cls()

    _debugoutput += get_debug_string("ControllerType", config["ControllerType"]["last_value"])
    _debugoutput += get_debug_string("LeftThumb", config["LeftThumb"]["last_value"])
    _debugoutput += get_debug_string("RightThumb", config["RightThumb"]["last_value"])
    _debugoutput += get_debug_string("LeftABButtons", config["LeftABButtons"]["last_value"])
    _debugoutput += get_debug_string("RightABButtons", config["RightABButtons"]["last_value"])

    for action in actions:
        if action["enabled"]:
            if action["type"] == "vector2":
                _debugoutput += get_debug_string(action["osc_parameter"][0], action["last_value"][0], action["floating"][0])
                _debugoutput += get_debug_string(action["osc_parameter"][1], action["last_value"][1], action["floating"][1])
                if len(action["osc_parameter"]) > 2:
                    _debugoutput += get_debug_string(action["osc_parameter"][2], action["last_value"][2], action["floating"][2])
            else:
                _debugoutput += get_debug_string(action["osc_parameter"], action["last_value"], action["floating"])

    print(_debugoutput)


def get_value(action: dict) -> bool | float | tuple:
    """
    Gets the value of an action by querying SteamVR.
    Parameters:
        action (dict): Action
    Returns:
        any: Value of the action
    """
    match action['type']:
        case "boolean":
            return bool(openvr.VRInput().getDigitalActionData(action['handle'], openvr.k_ulInvalidInputValueHandle).bState)
        case "vector1":
            return float(openvr.VRInput().getAnalogActionData(action['handle'], openvr.k_ulInvalidInputValueHandle).x)
        case "vector2":
            tmp = openvr.VRInput().getAnalogActionData(action['handle'], openvr.k_ulInvalidInputValueHandle)
            return tmp.x, tmp.y
        case _:
            raise TypeError("Unknown action type: " + action['type'])


def get_controllertype() -> int:
    """
    Gets the type of controller from SteamVR.
    Returns:
        int: Type of controller (0 = Unknown, 1 = Knuckles, 2 = Oculus/Meta Touch)
    """
    for i in range(1, openvr.k_unMaxTrackedDeviceCount):
        device_class = openvr.VRSystem().getTrackedDeviceClass(i)
        if device_class == 2:
            match openvr.VRSystem().getStringTrackedDeviceProperty(i, openvr.Prop_ControllerType_String):
                case 'knuckles':
                    return 1
                case 'oculus_touch':
                    return 2
                case _:
                    return 0
    return 0


def send_parameter(parameter: str, value) -> None:
    """
    Sends a parameter to VRChat via OSC.
    Parameters:
        parameter (str): Name of the parameter
        value (any): Value of the parameter
        floating (str): Floating value of the parameter, just for for debug output
    Returns:
        None
    """
    oscClient.send_message(AVATAR_PARAMETERS_PREFIX + parameter, value)


def send_boolean_toggle(action: dict, value: bool) -> None:
    """
    Sends a boolean action as a toggle to VRChat via OSC.
    Parameters:
        action (dict): Action
        value (bool): Value of the parameter
    Returns:
        None
    """
    if not action["enabled"]:
        return
    
    if value:
        action["last_value"] = not action["last_value"]
        time.sleep(0.1)
    
    send_parameter(action["osc_parameter"], action["last_value"])


def send_boolean(action: dict, value: bool) -> None:
    """
    Sends a boolean action to VRChat via OSC.
    Parameters:
        action (dict): Action
        value (bool): Value of the parameter
    Returns:
        None
    """
    global curr_time

    if not action["enabled"]:
        return

    if action["floating"]:
        if value:
            action["timestamp"] = curr_time
        elif not value and curr_time - action["timestamp"] <= action["floating"]: 
            value = action["last_value"]
    
    action["last_value"] = value

    send_parameter(action["osc_parameter"], value)


def send_vector1(action: dict, value: float) -> None:
    """
    Sends a vector1 action to VRChat via OSC.
    Parameters:
        action (dict): Action
        value (float): Value of the parameter
    Returns:
        None
    """
    global curr_time

    if not action["enabled"]:
        return
    
    if action["floating"]:
        if value > action["last_value"]:
            action["timestamp"] = curr_time
        elif value < action["last_value"] and curr_time - action["timestamp"] <= action["floating"]: 
            value = action["last_value"]

    action["last_value"] = value

    send_parameter(action["osc_parameter"], value)


def send_vector2(action: dict, value: tuple) -> None:
    """
    Sends a vector2 action to VRChat via OSC.
    Parameters:
        action (dict): Action
        value (tuple): X and Y value of the parameter in a tuple
    Returns:
        None
    """
    global curr_time

    val_x, val_y = value
    tmp = (val_x > STICKTOLERANCE or val_y > STICKTOLERANCE) or (val_x < -STICKTOLERANCE or val_y < -STICKTOLERANCE)

    if action["floating"]:
        if val_x:
            action["timestamp"][0] = curr_time
        elif not val_x and curr_time - action["timestamp"][0] <= action["floating"][0]: 
            val_x = action["last_value"][0]
        if val_y:
            action["timestamp"][1] = curr_time
        elif not val_y and curr_time - action["timestamp"][1] <= action["floating"][1]:
            val_y = action["last_value"][1]
    action["last_value"] = [val_x, val_y, tmp]

    if action["enabled"][0]:
        send_parameter(action["osc_parameter"][0], val_x)
    if action["enabled"][1]:
        send_parameter(action["osc_parameter"][1], val_y)
    if len(action["osc_parameter"]) > 2 and action["enabled"][2]:
        if action["floating"]:
            action["last_value"][2] = tmp
        send_parameter(action["osc_parameter"][2], tmp)


def handle_input() -> None:
    """
    Handles SteamVR input and sends it to VRChat.
    Returns:
        None
    """
    global curr_time

    _event = openvr.VREvent_t()
    _has_events = True
    while _has_events:
        _has_events = application.pollNextEvent(_event)
    openvr.VRInput().updateActionState(actionsets)

    curr_time = time.time()

    if config["ControllerType"]["enabled"]:
        if curr_time - config["ControllerType"]["timestamp"] <= 10.0:
            _controller_type = config["ControllerType"]["last_value"]
        else:
            _controller_type = get_controllertype()
            config["ControllerType"]["timestamp"] = curr_time
            config["ControllerType"]["last_value"] = _controller_type
        send_parameter("ControllerType", _controller_type)
        

    _strinputs = ""
    for action in actions[:8]: # Touch Actions
        val = get_value(action)
        _strinputs += "1" if val else "0"
        if action["enabled"]:
            send_boolean(action, val)
    if config["LeftThumb"]["enabled"]:
        _leftthumb = _strinputs[:4].rfind("1") + 1
        config["LeftThumb"]["last_value"] = _leftthumb
        send_parameter("LeftThumb", _leftthumb)
    if config["RightThumb"]["enabled"]:
        _rightthumb = _strinputs[4:].rfind("1") + 1
        config["RightThumb"]["last_value"] = _rightthumb
        send_parameter("RightThumb", _rightthumb)
    if config["LeftABButtons"]["enabled"]:
        _leftab = _strinputs[0] == "1" and _strinputs[1] == "1"
        config["LeftABButtons"]["last_value"] = _leftab
        send_parameter("LeftABButtons", _leftab)
    if config["RightABButtons"]["enabled"]:
        _rightab = _strinputs[4] == "1" and _strinputs[5] == "1"
        config["RightABButtons"]["last_value"] = _rightab
        send_parameter("RightABButtons", _rightab)

    for action in actions[8:]:
        val = get_value(action)
        match action['type']:
            case "boolean":
                if action["floating"] == -1:
                    send_boolean_toggle(action, val)
                else:
                    send_boolean(action, val)
            case "vector1":
                send_vector1(action, val)
            case "vector2":
                send_vector2(action, val)
            case _:
                raise TypeError("Unknown action type: " + action['type'])

    if args.debug:
        print_debugoutput()


# Argument Parser
parser = argparse.ArgumentParser(description='ThumbParamsOSC: Takes button data from SteamVR and sends it to an OSC-Client')
parser.add_argument('-d', '--debug', required=False, action='store_true', help='prints values for debugging')
parser.add_argument('-i', '--ip', required=False, type=str, help="set OSC ip. Default=127.0.0.1")
parser.add_argument('-p', '--port', required=False, type=str, help="set OSC port. Default=9000")
args = parser.parse_args()

if os.name == 'nt':
    ctypes.windll.kernel32.SetConsoleTitleW("ThumbParamsOSC v1.3.2" + (" (Debug)" if args.debug else ""))

first_launch_file = get_absolute_path("bindings/first_launch")
config_path = get_absolute_path('config.json')
manifest_path = get_absolute_path("app.vrmanifest")
application = openvr.init(openvr.VRApplication_Utility)
openvr.VRInput().setActionManifestPath(config_path)
openvr.VRApplications().addApplicationManifest(manifest_path)
if os.path.isfile(first_launch_file):
    openvr.VRApplications().setApplicationAutoLaunch("i5ucc.thumbparamsosc", True)
    os.remove(first_launch_file)
action_set_handle = openvr.VRInput().getActionSetHandle("/actions/thumbparams")
actionsets = (openvr.VRActiveActionSet_t * 1)()
actionset = actionsets[0]
actionset.ulActionSet = action_set_handle

config = json.load(open(config_path))
actions = config["actions"]
for action in actions:
    action["handle"] = openvr.VRInput().getActionHandle(action['name'])

IP = args.ip if args.ip else config["IP"]
PORT = args.port if args.port else config["Port"]
oscClient = udp_client.SimpleUDPClient(IP, PORT)
POLLINGRATE = 1 / float(config['PollingRate'])
STICKTOLERANCE = int(config['StickMoveTolerance']) / 100
AVATAR_PARAMETERS_PREFIX = "/avatar/parameters/"

cls()
if not args.debug:
    print("ThumbParamsOSC running...\n")
    print("You can minimize this window.\n")
    print("Press CTRL+C to exit.\n")
    print(f"IP:\t\t\t{IP}")
    print(f"Port:\t\t\t{PORT}")
    print(f"PollingRate:\t\t{POLLINGRATE}s ({config['PollingRate']} Hz)")
    print(f"StickMoveTolerance:\t{STICKTOLERANCE} ({config['StickMoveTolerance']}%)")
    print("\nOpen Configurator.exe to change sent Parameters and other Settings.")

# Main Loop
while True:
    try:
        handle_input()
        time.sleep(POLLINGRATE)
    except KeyboardInterrupt:
        cls()
        sys.exit()
    except Exception:
        cls()
        print("UNEXPECTED ERROR\n")
        print("Please Create an Issue on GitHub with the following information:\n")
        traceback.print_exc()
        input("\nPress ENTER to exit")
        sys.exit()
