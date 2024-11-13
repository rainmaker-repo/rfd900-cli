from enum import Enum
import time
import click
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

import serial
from serial.tools import list_ports
from modem_client import ModemClient
from s_registers import SRegisters


@dataclass
class ParameterConstraints:
    """Constraints for each parameter"""
    min_val: int
    max_val: int
    default_val: int
    description: str
    requires_matching: bool  # Must be same at both ends of link

# Parameter constraints from the datasheet
PARAMETER_CONSTRAINTS: Dict[SRegisters, ParameterConstraints] = {
    SRegisters.FORMAT: ParameterConstraints(0, 0, 0, "EEPROM version (should not be changed)", False),
    SRegisters.SERIAL_SPEED: ParameterConstraints(2, 115, 57, "Serial speed (2=2400 ... 115=115200)", False),
    SRegisters.AIR_SPEED: ParameterConstraints(2, 250, 64, "Air data rate (2-250 kbps)", True),
    SRegisters.NETID: ParameterConstraints(0, 499, 25, "Network ID", True),
    SRegisters.TXPOWER: ParameterConstraints(0, 30, 20, "Transmit power in dBm", False),
    SRegisters.ECC: ParameterConstraints(0, 1, 1, "Error correcting code (0=disabled, 1=enabled)", True),
    SRegisters.MAVLINK: ParameterConstraints(0, 1, 1, "MAVLink framing (0=disabled, 1=enabled)", False),
    SRegisters.OP_RESEND: ParameterConstraints(0, 1, 1, "Opportunistic resend (0=disabled, 1=enabled)", False),
    SRegisters.MIN_FREQ: ParameterConstraints(902000, 927000, 915000, "Min frequency in KHz", True),
    SRegisters.MAX_FREQ: ParameterConstraints(903000, 928000, 928000, "Max frequency in KHz", True),
    SRegisters.NUM_CHANNELS: ParameterConstraints(5, 50, 50, "Number of frequency hopping channels", True),
    SRegisters.DUTY_CYCLE: ParameterConstraints(10, 100, 100, "Transmit duty cycle %", False),
    SRegisters.LBT_RSSI: ParameterConstraints(0, 1, 0, "Listen before talk threshold (do not change)", True),
    SRegisters.MANCHESTER: ParameterConstraints(0, 1, 0, "Manchester encoding (do not change)", True),
    SRegisters.RTSCTS: ParameterConstraints(0, 1, 0, "RTS/CTS flow control (do not change)", False),
    SRegisters.NODEID: ParameterConstraints(0, 29, 2, "Node ID (0=base node)", False),
    SRegisters.NODEDESTINATION: ParameterConstraints(0, 65535, 65535, "Remote node ID (65535=broadcast)", False),
    SRegisters.SYNCANY: ParameterConstraints(0, 1, 0, "Allow sending without base node sync", False),
    SRegisters.NODECOUNT: ParameterConstraints(2, 30, 3, "Total number of nodes in network", True),
}


class CLI:
    def __init__(self):
        self.client = None
    
    def setup_logging(self, verbose: bool):
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level)
    
    def connect(self, port: str, baud_rate: int, timeout: float):
        """Initialize connection to modem"""
        self.client = ModemClient(port, baud_rate, timeout, line_break="\r\n")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logging.debug(f"Error during cleanup: {e}")

def detect_modems(baud_rate: int = 57600, timeout: float = 1.0) -> List[Tuple[str, str]]:
    """
    Detect RFD900 modems connected to the system.
    Returns list of tuples (port_name, version_info)
    """
    modems = []
    
    # Get list of all serial ports
    ports = list_ports.comports()
    
    for port in ports:
        try:
            # Try to connect and enter command mode
            with serial.Serial(port.device, baud_rate, timeout=timeout) as ser:
                # Set DTR and wait
                ser.dtr = True
                time.sleep(0.1)
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Drop DTR to signal command mode entry
                ser.dtr = False
                time.sleep(0.1)
                
                # Send test command
                ser.write(b'ATI\r\n')
                ser.flush()
                
                # Read response
                response = b''
                start = time.time()
                while (time.time() - start) < 1.0:
                    if ser.in_waiting:
                        chunk = ser.read(ser.in_waiting)
                        response += chunk
                        # Check if it's an RFD modem by looking for typical response patterns
                        if b'RFD SiK' in response or b'RFD900' in response:
                            # Clean up the response
                            version_info = response.decode().strip().split('\r\n')[-1]
                            modems.append((port.device, version_info))
                            break
                    time.sleep(0.1)
                    
        except (serial.SerialException, Exception) as e:
            logging.debug(f"Failed to check port {port.device}: {e}")
            continue
            
    return modems

@click.group()
@click.option('--port', help='Serial port of modem (optional, will auto-detect if not specified)')
@click.option('--baud-rate', default=57600, help='Baud rate')
@click.option('--timeout', default=1.0, help='Timeout in seconds')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
@click.pass_context
def main(ctx, port, baud_rate, timeout, verbose):
    """RFD900 Radio Modem Configuration Tool"""
    cli = CLI()
    cli.setup_logging(verbose)
    ctx.obj = cli
    
    try:
        # If port is not specified, try to auto-detect
        if not port:
            modems = detect_modems(baud_rate, timeout)
            
            if not modems:
                click.echo("Error: No RFD900 modems detected", err=True)
                ctx.exit(1)
                
            if len(modems) > 1:
                click.echo("Multiple RFD900 modems detected:")
                for i, (port_name, version) in enumerate(modems, 1):
                    click.echo(f"{i}. Port: {port_name} ({version})")
                    
                # Prompt user to choose
                choice = click.prompt(
                    "Please choose a modem (1-{}) or 0 to cancel".format(len(modems)),
                    type=click.IntRange(0, len(modems))
                )
                if choice == 0:
                    ctx.exit(0)
                port = modems[choice - 1][0]
            else:
                port_name, version = modems[0]
                click.echo(f"Found RFD900 modem on port {port_name} ({version})")
                if not click.confirm("Would you like to use this modem?"):
                    ctx.exit(0)
                port = port_name
                
        
        # Connect to the selected/specified port
        cli.connect(port, baud_rate, timeout)
        
    except Exception as e:
        click.echo(f"Error initializing modem: {e}", err=True)
        ctx.exit(1)

def get_modem_response(cli: CLI, cmd: str) -> str:
    """Send command and get response, handling command echo"""
    try:
        if not cli.client:
            click.echo("Error: Not connected to modem", err=True)
            return ""
        response = cli.client.send(cmd)
        if not response:
            return ""
        
        # Split into lines and filter out command echo
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        # Remove the echoed command if present
        if lines and lines[0] == cmd:
            lines = lines[1:]
        
        return '\n'.join(lines)
    except Exception as e:
        logging.error(f"Error sending command {cmd}: {e}")
        return ""

@main.command()
@click.pass_obj
def info(cli: CLI):
    """Display modem information"""
    try:
        
        # ATI - Version info
        version = get_modem_response(cli, "ATI")
        if version:
            click.echo(f"Version: {version}")

        # ATI2 - Board type
        board = get_modem_response(cli, "ATI2")
        if board:
            click.echo(f"Board Type: {board}")

        # ATI3 - Board frequency
        freq = get_modem_response(cli, "ATI3")
        if freq:
            click.echo(f"Board Frequency: {freq}")

        # ATI4 - Board version
        board_ver = get_modem_response(cli, "ATI4")
        if board_ver:
            click.echo(f"Board Version: {board_ver}")

        # ATI5 - Parameters
        params = get_modem_response(cli, "ATI5")
        if params:
            click.echo("\nCurrent Parameters:")
            click.echo(params)

        # ATI6 - TDM timing
        timing = get_modem_response(cli, "ATI6")
        if timing:
            click.echo("\nTDM Timing:")
            click.echo(timing)

        # ATI7 - RSSI stats
        rssi = get_modem_response(cli, "ATI7")
        if rssi:
            click.echo("\nRSSI Statistics:")
            click.echo(rssi)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        cli.cleanup()

@main.command()
@click.pass_obj
def show(cli: CLI):
    """Show all current parameter values"""
    try:
        response = get_modem_response(cli, "ATI5")
        if response:
            click.echo(response)
    finally:
        cli.cleanup()

@main.command()
@click.argument('register', type=click.Choice([r.name for r in SRegisters]))
@click.argument('value', type=int)
@click.pass_obj
def set(cli: CLI, register: str, value: int):
    """Set parameter value (e.g., set TXPOWER 20)"""
    reg = SRegisters[register]
    constraints = PARAMETER_CONSTRAINTS[reg]
    
    if value < constraints.min_val or value > constraints.max_val:
        click.echo(f"Error: {register} value must be between {constraints.min_val} and {constraints.max_val}", err=True)
        return
    
    try:
        # Set the value
        cli.client.send(f"ATS{reg.value}={value}")
        
        # Write to EEPROM
        cli.client.send("AT&W")
        
        # Verify the change
        response = get_modem_response(cli, f"ATS{reg.value}?")
        if response:
            click.echo(f"Set {register} to {value}")
            if constraints.requires_matching:
                click.echo("Note: This parameter must be set to the same value on both modems")
    finally:
        cli.cleanup()

@main.command()
@click.argument('register', type=click.Choice([r.name for r in SRegisters]))
@click.pass_obj
def get(cli: CLI, register: str):
    """Get current parameter value"""
    reg = SRegisters[register]
    try:
        response = get_modem_response(cli, f"ATS{reg.value}?")
        if response:
            constraints = PARAMETER_CONSTRAINTS[reg]
            click.echo(f"{register} = {response}")
            click.echo(f"Description: {constraints.description}")
            click.echo(f"Valid range: {constraints.min_val} to {constraints.max_val}")
            click.echo(f"Default value: {constraints.default_val}")
            if constraints.requires_matching:
                click.echo("Note: Must be same on both modems")
    finally:
        cli.cleanup()

@main.command()
@click.pass_obj
def factory_reset(cli: CLI):
    """Reset all parameters to factory defaults"""
    try:
        cli.client.send("AT&F")
        cli.client.send("AT&W")
        click.echo("Reset to factory defaults")
    finally:
        cli.cleanup()

@main.command()
@click.pass_obj
def reboot(cli: CLI):
    """Reboot the modem"""
    try:
        cli.client.send("ATZ")
        click.echo("Modem rebooted")
    finally:
        cli.cleanup()

if __name__ == '__main__':
    main()