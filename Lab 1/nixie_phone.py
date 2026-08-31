from flask import Flask, request, jsonify, render_template_string
import socket
import threading

# ---------------------------------------------------------
# BASIC SERVER SETTINGS
# ---------------------------------------------------------

app = Flask(__name__)

PORT = 5001

# This dictionary remembers what the phone should display.
display_state = {
    "power": False,
    "digit": "",
    "version": 0
}

# This prevents two devices from changing the state
# at exactly the same moment.
state_lock = threading.Lock()


# ---------------------------------------------------------
# COMPLETE WEBPAGE
# HTML, CSS, AND JAVASCRIPT ARE ALL INSIDE THIS STRING.
# YOU DO NOT NEED SEPARATE WEB FILES.
# ---------------------------------------------------------

PAGE = r"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1,
        maximum-scale=1, user-scalable=no"
    >

    <title>Nixie Phone Controller</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html,
        body {
            width: 100%;
            min-height: 100%;
            margin: 0;
        }

        body {
            background: #080503;
            color: #ffd8ad;
            font-family: Arial, Helvetica, sans-serif;
        }

        button {
            border: 1px solid #ff9138;
            border-radius: 9px;
            padding: 14px 18px;
            background: #271309;
            color: #ffe0bd;
            font-size: 18px;
            cursor: pointer;
        }

        button:hover {
            background: #4b230d;
        }

        button:active {
            transform: scale(0.97);
        }

        .hidden {
            display: none !important;
        }

        /* ---------------------------------------------
           FIRST PAGE: CHOOSE LAPTOP OR PHONE MODE
        --------------------------------------------- */

        #choicePage {
            width: min(92%, 650px);
            margin: 60px auto;
            padding: 30px;
            text-align: center;
            border: 1px solid #6a371b;
            border-radius: 16px;
            background: #130c08;
            box-shadow: 0 0 30px rgba(255, 100, 20, 0.12);
        }

        #choicePage h1 {
            color: #ff9b45;
        }

        #choicePage button {
            display: block;
            width: 100%;
            margin: 18px 0;
            min-height: 65px;
        }

        /* ---------------------------------------------
           LAPTOP CONTROLLER
        --------------------------------------------- */

        #controllerPage {
            width: min(94%, 760px);
            margin: 25px auto;
            padding: 24px;
        }

        #controllerPage h1 {
            color: #ff9b45;
        }

        #powerControls {
            display: flex;
            gap: 12px;
            margin: 20px 0;
        }

        #powerControls button {
            flex: 1;
        }

        #numberButtons {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
        }

        .numberButton {
            min-height: 75px;
            font-size: 32px;
            font-weight: bold;
        }

        #blankButton {
            grid-column: span 5;
            min-height: 58px;
        }

        #controllerStatus {
            min-height: 30px;
            margin-top: 25px;
            padding: 14px;
            border: 1px solid #4e2a16;
            border-radius: 8px;
            background: #100a06;
            color: #ffad63;
        }

        #connectionStatus {
            color: #89dd89;
        }

        /* ---------------------------------------------
           PHONE NIXIE DISPLAY
        --------------------------------------------- */

        #displayPage {
            width: 100vw;
            height: 100vh;
            align-items: center;
            justify-content: center;
            overflow: hidden;

            background:
                radial-gradient(
                    circle at center,
                    #2e1405 0%,
                    #0c0602 43%,
                    #000000 100%
                );
        }

        #glassTube {
            position: relative;
            width: min(73vw, 350px);
            height: min(84vh, 650px);

            border: 5px solid rgba(255, 226, 185, 0.30);

            border-radius:
                46% 46% 18% 18% /
                20% 20% 8% 8%;

            background:
                linear-gradient(
                    90deg,
                    rgba(255, 255, 255, 0.08),
                    rgba(255, 255, 255, 0.01) 30%,
                    rgba(255, 110, 20, 0.03) 70%,
                    rgba(255, 255, 255, 0.08)
                ),
                #050301;

            box-shadow:
                inset 0 0 25px rgba(255, 220, 180, 0.08),
                0 0 20px rgba(255, 100, 20, 0.17);

            overflow: hidden;
        }

        #glassReflection {
            position: absolute;
            z-index: 4;
            top: 7%;
            left: 13%;
            width: 11%;
            height: 46%;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.10);
            filter: blur(4px);
            pointer-events: none;
        }

        #wireMesh {
            position: absolute;
            z-index: 3;
            inset: 13% 10% 16%;

            opacity: 0.16;

            background-image:
                linear-gradient(
                    rgba(255, 255, 255, 0.30) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255, 255, 255, 0.30) 1px,
                    transparent 1px
                );

            background-size: 15px 15px;

            pointer-events: none;
        }

        #nixieDigit {
            position: absolute;
            z-index: 2;
            inset: 0;

            display: flex;
            align-items: center;
            justify-content: center;

            padding-bottom: 7%;

            color: #ff8922;

            font-family:
                "Arial Narrow",
                "Roboto Condensed",
                Arial,
                sans-serif;

            font-size: min(58vh, 410px);
            font-weight: 300;
            line-height: 1;

            opacity: 1;

            text-shadow:
                0 0 2px #fff2d5,
                0 0 6px #ffc166,
                0 0 14px #ff7a14,
                0 0 30px #ed4b00,
                0 0 60px rgba(255, 65, 0, 0.78);

            transition:
                opacity 150ms ease,
                transform 150ms ease,
                filter 150ms ease;
        }

        #tubeBase {
            position: absolute;
            z-index: 5;
            left: 8%;
            right: 8%;
            bottom: 0;
            height: 13%;

            border-radius: 7px 7px 18px 18px;

            background:
                linear-gradient(
                    #514a44,
                    #1b1714 45%,
                    #000000
                );
        }

        #glassTube.powerOff #nixieDigit {
            opacity: 0;
        }

        #nixieDigit.changing {
            opacity: 0;
            transform: scale(0.96);
            filter: blur(5px);
        }

        #nixieDigit.igniting {
            animation: igniteDigit 500ms ease-out;
        }

        #glassTube.starting {
            animation: startTube 700ms steps(2, end);
        }

        #phoneMessage {
            position: fixed;
            z-index: 20;
            bottom: 12px;
            left: 0;
            width: 100%;
            text-align: center;
            color: rgba(255, 188, 125, 0.45);
           );
            font-size: 12px;
        }

        @keyframes igniteDigit {
            0% {
                opacity: 0;
                filter: blur(8px);
                transform: scale(0.93);
            }

            18% {
                opacity: 1;
            }

            32% {
                opacity: 0.30;
            }

            54% {
                opacity: 1;
                filter: blur(1px);
                transform: scale(1.02);
            }

            72% {
                opacity: 0.65;
            }

            100% {
                opacity: 1;
                filter: blur(0);
                transform: scale(1);
            }
        }

        @keyframes startTube {
            0%   { opacity: 0.12; }
            18%  { opacity: 1; }
            32%  { opacity: 0.22; }
            50%  { opacity: 0.90; }
            68%  { opacity: 0.42; }
            100% { opacity: 1; }
        }

        @media (max-width: 600px) {
            #numberButtons {
                grid-template-columns: repeat(2, 1fr);
            }

            #blankButton {
                grid-column: span 2;
            }
        }
    </style>
</head>

<body>

    <!-- FIRST PAGE -->

    <main id="choicePage">
        <h1>Nixie Phone</h1>

        <p>
            Choose how this device will be used.
        </p>

        <button id="chooseController">
            Use This Device as the Laptop Controller
        </button>

        <button id="chooseDisplay">
            Use This Device as the Phone Nixie Display
        </button>
    </main>


    <!-- LAPTOP CONTROLLER PAGE -->

    <main id="controllerPage" class="hidden">
        <h1>Nixie Tube Controller</h1>

        <p id="connectionStatus">
            Connected to the Python program.
        </p>

        <p>
            Click a button below. The phone should respond.
        </p>

        <div id="powerControls">
            <button id="powerOnButton">
                Power On
            </button>

            <button id="powerOffButton">
                Power Off
            </button>
        </div>

        <div id="numberButtons">
            <button class="numberButton" data-digit="0">0</button>
            <button class="numberButton" data-digit="1">1</button>
            <button class="numberButton" data-digit="2">2</button>
            <button class="numberButton" data-digit="3">3</button>
            <button class="numberButton" data-digit="4">4</button>
            <button class="numberButton" data-digit="5">5</button>
            <button class="numberButton" data-digit="6">6</button>
            <button class="numberButton" data-digit="7">7</button>
            <button class="numberButton" data-digit="8">8</button>
            <button class="numberButton" data-digit="9">9</button>

            <button id="blankButton">
                Blank Tube
            </button>
        </div>

        <p id="controllerStatus">
            Nothing has been sent yet.
        </p>
    </main>


    <!-- PHONE DISPLAY PAGE -->

    <main id="displayPage" class="hidden">
        <div id="glassTube" class="powerOff">
            <div id="glassReflection"></div>
            <div id="wireMesh"></div>
            <div id="nixieDigit"></div>
            <div id="tubeBase"></div>
        </div>

        <div id="phoneMessage">
            Nixie Phone Display
        </div>
    </main>


    <script>
        const choicePage =
            document.getElementById("choicePage");

        const controllerPage =
            document.getElementById("controllerPage");

        const displayPage =
            document.getElementById("displayPage");

        const glassTube =
            document.getElementById("glassTube");

        const nixieDigit =
            document.getElementById("nixieDigit");

        const controllerStatus =
            document.getElementById("controllerStatus");

        const numberButtons =
            document.querySelectorAll(".numberButton");

        let lastDigit = null;
        let lastPower = null;
        let changingTimer = null;


        // ------------------------------------------------
        // SELECT LAPTOP CONTROLLER MODE
        // ------------------------------------------------

        document
            .getElementById("chooseController")
            .addEventListener("click", () => {
                showController();
            });


        // ------------------------------------------------
        // SELECT PHONE DISPLAY MODE
        // ------------------------------------------------

        document
            .getElementById("chooseDisplay")
            .addEventListener("click", async () => {
                showDisplay();

                if (document.documentElement.requestFullscreen) {
                    try {
                        await document.documentElement.requestFullscreen();
                    } catch (error) {
                        console.log(
                            "Fullscreen was not available.",
                            error
                        );
                    }
                }
            });


        // ------------------------------------------------
        // AUTOMATIC MODE FROM THE WEB ADDRESS
        //
        // Example:
        // ?mode=controller
        // ?mode=display
        // ------------------------------------------------

        const parameters =
            new URLSearchParams(window.location.search);

        const requestedMode =
            parameters.get("mode");

        if (requestedMode === "controller") {
            showController();
        }

        if (requestedMode === "display") {
            showDisplay();
        }


        function showController() {
            choicePage.classList.add("hidden");
            displayPage.classList.add("hidden");
            controllerPage.classList.remove("hidden");
        }


        function showDisplay() {
            choicePage.classList.add("hidden");
            controllerPage.classList.add("hidden");
            displayPage.classList.remove("hidden");

            document.body.style.overflow = "hidden";

            refreshDisplay();

            setInterval(refreshDisplay, 250);
        }


        // ------------------------------------------------
        // LAPTOP NUMBER BUTTONS
        // ------------------------------------------------

        numberButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const digit = button.dataset.digit;

                sendCommand({
                    digit: digit
                });

                controllerStatus.textContent =
                    "Sent the number " + digit + " to the phone.";
            });
        });


        // ------------------------------------------------
        // POWER BUTTONS
        // ------------------------------------------------

        document
            .getElementById("powerOnButton")
            .addEventListener("click", () => {
                sendCommand({
                    power: true
                });

                controllerStatus.textContent =
                    "The tube was turned on.";
            });


        document
            .getElementById("powerOffButton")
            .addEventListener("click", () => {
                sendCommand({
                    power: false
                });

                controllerStatus.textContent =
                    "The tube was turned off.";
            });


        document
            .getElementById("blankButton")
            .addEventListener("click", () => {
                sendCommand({
                    digit: ""
                });

                controllerStatus.textContent =
                    "The tube was made blank.";
            });


        // ------------------------------------------------
        // SEND A COMMAND FROM THE LAPTOP TO PYTHON
        // ------------------------------------------------

        async function sendCommand(command) {
            try {
                const response = await fetch("/api/state", {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(command)
                });

                if (!response.ok) {
                    throw new Error(
                        "The Python server rejected the command."
                    );
                }
            } catch (error) {
                controllerStatus.textContent =
                    "ERROR: The command was not sent.";

                console.error(error);
            }
        }


        // ------------------------------------------------
        // PHONE CHECKS PYTHON FOR THE CURRENT NUMBER
        // ------------------------------------------------

        async function refreshDisplay() {
            try {
                const response = await fetch(
                    "/api/state?time=" + Date.now(),
                    {
                        cache: "no-store"
                    }
                );

                if (!response.ok) {
                    return;
                }

                const state = await response.json();

                updatePhone(state);

            } catch (error) {
                console.log(
                    "Waiting for the Python server...",
                    error
                );
            }
        }


        // ------------------------------------------------
        // UPDATE THE PHONE SCREEN
        // ------------------------------------------------

        function updatePhone(state) {
            if (state.power !== lastPower) {
                if (state.power) {
                    glassTube.classList.remove("powerOff");
                    glassTube.classList.add("starting");

                    setTimeout(() => {
                        glassTube.classList.remove("starting");
                    }, 700);
                } else {
                    glassTube.classList.add("powerOff");
                    nixieDigit.textContent = "";
                }

                lastPower = state.power;
            }

            if (!state.power) {
                lastDigit = state.digit;
                return;
            }

            if (state.digit !== lastDigit) {
                changeDigit(state.digit);
                lastDigit = state.digit;
            }
        }


        function changeDigit(newDigit) {
            if (changingTimer !== null) {
                clearTimeout(changingTimer);
            }

            nixieDigit.classList.add("changing");

            changingTimer = setTimeout(() => {
                nixieDigit.textContent = newDigit;

                nixieDigit.classList.remove("changing");
                nixieDigit.classList.remove("igniting");

                // This restarts the glow animation.
                void nixieDigit.offsetWidth;

                if (newDigit !== "") {
                    nixieDigit.classList.add("igniting");
                }

                changingTimer = null;
            }, 160);
        }
    </script>
</body>

</html>
"""


# ---------------------------------------------------------
# MAIN WEBPAGE
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template_string(PAGE)


# ---------------------------------------------------------
# PHONE ASKS FOR THE CURRENT DISPLAY STATE
# ---------------------------------------------------------

@app.route("/api/state", methods=["GET"])
def get_state():
    with state_lock:
        return jsonify(display_state)


# ---------------------------------------------------------
# LAPTOP SENDS A NEW DISPLAY STATE
# ---------------------------------------------------------

@app.route("/api/state", methods=["POST"])
def update_state():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({
            "ok": False,
            "error": "No valid data was received."
        }), 400

    with state_lock:
        if "power" in data:
            display_state["power"] = bool(data["power"])

            if display_state["power"] is False:
                display_state["digit"] = ""

        if "digit" in data:
            requested_digit = str(data["digit"])

            allowed_digits = [
                "",
                "0", "1", "2", "3", "4",
                "5", "6", "7", "8", "9"
            ]

            if requested_digit not in allowed_digits:
                return jsonify({
                    "ok": False,
                    "error": "Only the numbers 0 through 9 are allowed."
                }), 400

            display_state["digit"] = requested_digit

        display_state["version"] += 1

        return jsonify({
            "ok": True,
            "state": display_state
        })


# ---------------------------------------------------------
# FIND THE LAPTOP'S WI-FI ADDRESS
# ---------------------------------------------------------

def find_local_ip():
    test_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:
        # This normally discovers the active local network address.
        # It does not send your project data to Google.
        test_socket.connect(("8.8.8.8", 80))

        local_ip = test_socket.getsockname()[0]

    except OSError:
        local_ip = "127.0.0.1"

    finally:
        test_socket.close()

    return local_ip


# ---------------------------------------------------------
# START THE PROGRAM
# ---------------------------------------------------------

if __name__ == "__main__":
    local_ip = find_local_ip()

    print()
    print("====================================================")
    print("NIXIE PHONE IS RUNNING")
    print("====================================================")
    print()
    print("On this laptop, open:")
    print(
        f"http://127.0.0.1:{PORT}/?mode=controller"
    )
    print()
    print("On your phone, open:")
    print(
        f"http://{local_ip}:{PORT}/?mode=display"
    )
    print()
    print("Laptop and phone must use the same Wi-Fi.")
    print("Keep this Command Prompt window open.")
    print("Press Ctrl+C here when you want to stop.")
    print()

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        threaded=True
    )