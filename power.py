try:
    import smbus

    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

# Registres INA219
_REG_CONFIG = 0x00
_REG_SHUNTVOLTAGE = 0x01
_REG_BUSVOLTAGE = 0x02
_REG_POWER = 0x03
_REG_CURRENT = 0x04
_REG_CALIBRATION = 0x05


class BusVoltageRange:
    RANGE_16V = 0x00


class Gain:
    DIV_2_80MV = 0x01


class ADCResolution:
    ADCRES_12BIT_32S = 0x0D


class Mode:
    SANDBVOLT_CONTINUOUS = 0x07


class INA219:
    def __init__(self, i2c_bus=1, addr=0x43):
        self.bus = smbus.SMBus(i2c_bus)
        self.addr = addr
        self._current_lsb = 0.1  # 0.1mA per bit
        self._cal_value = 20480  # Calibration pour shunt 0.01 ohm
        self._power_lsb = 0.002  # 2mW per bit
        self.setup()

    def read(self, address):
        data = self.bus.read_i2c_block_data(self.addr, address, 2)
        return (data[0] * 256) + data[1]

    def write(self, address, data):
        temp = [(data & 0xFF00) >> 8, data & 0xFF]
        self.bus.write_i2c_block_data(self.addr, address, temp)

    def setup(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        config = (
            BusVoltageRange.RANGE_16V << 13
            | Gain.DIV_2_80MV << 11
            | ADCResolution.ADCRES_12BIT_32S << 7
            | ADCResolution.ADCRES_12BIT_32S << 3
            | Mode.SANDBVOLT_CONTINUOUS
        )
        self.write(_REG_CONFIG, config)

    def getBusVoltage_V(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        return (self.read(_REG_BUSVOLTAGE) >> 3) * 0.004

    def getCurrent_mA(self):
        value = self.read(_REG_CURRENT)
        if value > 32767:
            value -= 65535
        return value * self._current_lsb

    def getPower_W(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        value = self.read(_REG_POWER)
        if value > 32767:
            value -= 65535
        return value * self._power_lsb


def get_battery_datas():
    default = {
        "voltage": 0.0,
        "percent": 0,
        "current": 0,
        "power": 0.0,
        "online": False,
    }
    if not I2C_AVAILABLE:
        return default

    try:
        ina = INA219(addr=0x43)
        v = ina.getBusVoltage_V()
        p = int((v - 3.0) / 1.1 * 100)
        p = max(0, min(100, p))

        return {
            "voltage": round(v, 2),
            "percent": p,
            "current": int(ina.getCurrent_mA()),
            "power": round(ina.getPower_W(), 2),
            "online": True,
        }
    except Exception as e:
        print(f"Impossible de récupérer les valeurs de la batterie : {e}")
        return default
