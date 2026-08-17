"""
I've been having a bit of trouble sending hpgl files directly to the penplotter with the `cat` command. Despite setting the baudrate, some kind of delay keeps happening and instruction get lost. 
Figured the easiest way to get this working was to send the instructions and, on slower instructions, query and wait for the machine's location as to throttle our instruction outputs.
"""

import serial
import time
import sys


def plot_hpgl(filename, port='/dev/ttyUSB0', baudrate=9600):
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=10, # We're keep this fairly high so we assume a timeout if there is ever a command that takes a long time to execute.
            xonxoff=False 
        )
        # Force the read timeout to trigger on Carriage Return
        ser.terminator = b'\r' 
        
        print(f"Connected to {port}. Initializing...")
        ser.reset_input_buffer()
        ser.write(b'IN;\r') 
        time.sleep(0.5)

    except serial.SerialException as e:
        print(f"Error: {e}")
        sys.exit(1)

    with open(filename, 'r') as file:
        hpgl_data = file.read().replace('\n', '').replace('\r', '')
        commands = [cmd.strip() for cmd in hpgl_data.split(';') if cmd.strip()]

    print(f"Executing {len(commands)} commands...")

    # Commands that we want to wait for
    SLOW_COMMANDS = ('PA', 'PR', 'PD', 'PU', 'AA', 'AR', 'SP', 'CP')

    for idx, cmd in enumerate(commands):
        print(f"\rSending: {idx+1}/{len(commands)} (Current: {cmd})")

        # Send the command
        ser.write(f"{cmd};\r".encode('ascii'))

        # For commands identified as slow, we are appending a query for location and waiting for it. This is what throttles our output
        if cmd.startswith(SLOW_COMMANDS):
            ser.write(b'OA;\r')
            
            # This returns immediately when the plotter sends a carriage return '\r'. This plotter doesnt send newlines.
            response = ser.read_until(b'\r').decode('ascii').strip()
            
            if not response:
                print(f"\n[!] Real Timeout on command {idx+1}: {cmd}")
            
        # UI Feedback
        if idx % 5 == 0:
            sys.stdout.write(f"\rProgress: {idx+1}/{len(commands)} (Current: {cmd[:8]})")
            sys.stdout.flush()

    print("\n\nPlot Finished. Pen parked.")
    ser.write(b'PU;PA0,0;SP0;\r')
    ser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <file.hpgl>")
    else:
        plot_hpgl(sys.argv[1])