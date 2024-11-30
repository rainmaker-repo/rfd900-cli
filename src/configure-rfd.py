#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import time
import click
from s_registers import SRegisters

def list_serial_ports():
    """
    List all available serial ports along with additional information
    about the connected devices.
    """
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports detected.")
        return []
    
    port_info = []
    
    for port in ports:
        device_info = {
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid
        }
        port_info.append(device_info)
    
    return port_info

def send_command(ser, command, expected_response="OK"):
    """Send a command to the RFD900 modem and wait for a response."""
    click.echo("sending AT command: "+command)
    ser.write((command + "\r\n").encode())
    time.sleep(0.5)
    response = ser.readlines()
    response = [line.decode().strip() for line in response]
    return response

def interactive_shell(ser):
    """Interactive shell to configure and retrieve RFD900 parameters."""
    click.echo("Entering interactive shell. Type 'help' for a list of commands.")
    while True:
        try:
            command = click.prompt("rfd-config>", default="").strip()
            if not command:
                continue
            if command.lower() in ["exit", "quit"]:
                click.echo("Exiting command mode...")
                send_command(ser, "ATO")
                break
            elif command.lower() == "help":
                click.echo("""
Available Commands:
    set {PARAM} {VALUE}  - Set a modem parameter (e.g., set NETID 5)
    get {PARAM}          - Retrieve a modem parameter (e.g., get NETID)
    params               - List all configurable parameters
    write                - Save your changes to the modem.
    help                 - Show this help message
    exit / quit          - Exit the interactive shell
                """)
            elif command.lower() == "params":
                click.echo("""
Available Parameters:
    NETID, SERIAL_SPEED, AIR_SPEED, TXPOWER, ECC, MAVLINK, MIN_FREQ, MAX_FREQ,
    NUM_CHANNELS, DUTY_CYCLE, NODEID, NODEDESTINATION, SYNCANY, NODECOUNT
                """)
            elif command.lower().startswith("get "):
                _, param = command.split(" ", 1)
                register = getattr(SRegisters, param.upper()).value
                response = send_command(ser, f"ATS{str(register)}?")
                click.echo("\n".join(response))
            elif command.lower().startswith("set "):
                _, param, value = command.split(" ", 2)
                register = getattr(SRegisters, param.upper()).value
                send_command(ser, f"ATS{register}={value}")
                click.echo(f"Parameter {param} set to {value}.")
            elif command.lower() == "write":
                click.echo("Saving...")
                send_command(ser, "AT&W")
                click.echo("Saved your changes.")
                response = send_command(ser, "ATI5")
                click.echo("Updated Modem Parameters:")
                for line in response:
                    click.echo("line")
            else:
                click.echo("Unknown command. Type 'help' for a list of commands.")
        except Exception as e:
            click.echo(f"Error: {e}")


def enter_command_mode(ser):
    """
    Enter command mode by sending '+++'.
    Ensures there is a 1-second pause before and after sending the command.
    """
    click.echo("Preparing to enter command mode...")
    time.sleep(1)  # Ensure 1 second of inactivity
    ser.write(b"+++")
    time.sleep(1)  # Ensure 1 second of inactivity after
    click.echo("Sent '+++' to enter command mode.")
    response = ser.readlines()
    response = [line.decode().strip() for line in response]
    if "OK" in response:
        click.echo("Successfully entered command mode.")
    else:
        click.echo(f"Command mode entry response: {response}")

@click.command()
@click.option('--baudrate', default=57600, help='Baud rate for the connection (default: 57600).')
def rfd900_tool(baudrate):
    """Interactive tool to configure RFD900 modems."""
    ports_info = list_serial_ports()
    
    if not ports_info:
        return
    
    if len(ports_info) == 1:
        confirm = click.confirm(
            f"Found one serial port ({ports_info[0]['device']} - {ports_info[0]['description']}). Do you want to use it?", 
            default=True
        )
        if not confirm:
            click.echo("Exiting.")
            return
        selected_port = ports_info[0]['device']
    else:
        selected_port = click.prompt(
            "Select a port by number", 
            type=click.Choice([str(i + 1) for i in range(len(ports_info))])
        )
        selected_port = ports_info[int(selected_port) - 1]['device']
    
    try:
        with serial.Serial(selected_port, baudrate, timeout=1) as ser:
            click.echo(f"Connected to {selected_port} at {baudrate} baud.")
            
            # Enter command mode
            enter_command_mode(ser)
            
            # Launch interactive shell
            interactive_shell(ser)
    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    rfd900_tool()
