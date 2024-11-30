# RFD900 Configuration Tool

This Python-based interactive CLI tool allows you to configure and retrieve settings from RFD900 modems. The tool provides an easy-to-use interface for managing modem parameters such as `NETID`, `SERIAL_SPEED`, `AIR_SPEED`, and more.

---

## Features

- **List Serial Ports**: Automatically detect available serial ports and connected devices.
- **Interactive Shell**: Configure and retrieve modem parameters in a user-friendly command mode.
- **Customizable Settings**: Modify and save modem configurations such as baud rate, frequency ranges, and transmission power.
- **Save Configurations**: Write changes to the modem's non-volatile memory.

---

## Prerequisites

Before using this tool, ensure you have the following installed:

- Python 3.6 or later
- [pyserial](https://pypi.org/project/pyserial/)
- [click](https://pypi.org/project/click/)

To install the dependencies, run:

```bash
pip install pyserial click
```

---

## Usage

### Running the Tool

1. Save the script as `rfd900_tool.py`.
2. Make the script executable:

   ```bash
   chmod +x rfd900_tool.py
   ```

3. Run the script:

   ```bash
   ./rfd900_tool.py
   ```

   You can specify a custom baud rate with the `--baudrate` option (default: 57600):

   ```bash
   ./rfd900_tool.py --baudrate 115200
   ```

---

### Commands in Interactive Shell

Once connected, the tool enters an interactive shell where you can execute the following commands:

| Command                          | Description                                                                 |
|----------------------------------|-----------------------------------------------------------------------------|
| `set {PARAM} {VALUE}`            | Set a modem parameter (e.g., `set NETID 5`).                                |
| `get {PARAM}`                    | Retrieve the current value of a parameter (e.g., `get NETID`).              |
| `params`                         | List all configurable parameters.                                           |
| `write`                          | Save changes to the modem's non-volatile memory.                            |
| `help`                           | Display a list of available commands.                                       |
| `exit` or `quit`                 | Exit the interactive shell and return to normal modem operation.            |

---

### Example Workflow

1. **List Serial Ports**:
   The tool will detect available serial ports and prompt you to select one.

2. **Enter Command Mode**:
   The tool automatically sends the `+++` command to enter command mode.

3. **Configure Parameters**:
   Use the `set` and `get` commands to modify and view parameters.

4. **Save Changes**:
   Run `write` to save your changes to the modem.

5. **Exit**:
   Type `exit` or `quit` to leave the interactive shell.

---

## Available Parameters

The following parameters can be configured:

- `NETID`
- `SERIAL_SPEED`
- `AIR_SPEED`
- `TXPOWER`
- `ECC`
- `MAVLINK`
- `MIN_FREQ`
- `MAX_FREQ`
- `NUM_CHANNELS`
- `DUTY_CYCLE`
- `NODEID`
- `NODEDESTINATION`
- `SYNCANY`
- `NODECOUNT`

---

## Error Handling

- If no serial ports are detected, the tool will display a message and exit.
- If communication with the modem fails, the tool provides descriptive error messages for troubleshooting.