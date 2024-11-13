from enum import Enum
import click
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from modem_client import ModemClient
from s_registers import SRegisters

# [Previous Enums and ParameterConstraints stay the same]

class CLI:
    def __init__(self):
        self.client: Optional[ModemClient] = None
    
    def setup_logging(self, verbose: bool):
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level)
    
    def cleanup(self):
        """Cleanup resources"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logging.debug(f"Error during cleanup: {e}")

@click.group()
@click.option('--port', required=True, help='Serial port of modem')
@click.option('--baud-rate', default=57600, help='Baud rate')
@click.option('--timeout', default=1.0, help='Timeout in seconds')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
@click.pass_context
def main(ctx, port, baud_rate, timeout, verbose):
    """RFD900 Radio Modem Configuration Tool"""
    cli = CLI()
    cli.setup_logging(verbose)
    try:
        cli.client = ModemClient(port, baud_rate, timeout, line_break="\r\n")
        ctx.obj = cli
    except Exception as e:
        click.echo(f"Error initializing modem: {e}", err=True)
        ctx.exit(1)

def get_modem_response(cli: CLI, cmd: str) -> str:
    """Send command and get response, handling command echo"""
    try:
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