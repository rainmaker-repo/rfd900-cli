from enum import Enum
class SRegisters(Enum):
    """The parameters that can be  set in the RFD900 modem
      and their corresponding Register Numbers"""
    FORMAT = 0
    SERIAL_SPEED = 1
    AIR_SPEED = 2
    NETID = 3
    TXPOWER = 4
    ECC = 5
    MAVLINK = 6
    OP_RESEND = 7
    MIN_FREQ = 8
    MAX_FREQ = 9
    NUM_CHANNELS = 10
    DUTY_CYCLE = 11
    LBT_RSSI = 12
    MANCHESTER = 13
    RTSCTS = 14
    NODEID = 15
    NODEDESTINATION = 16
    SYNCANY = 17
    NODECOUNT = 18