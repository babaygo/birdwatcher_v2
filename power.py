import smbus
import time

I2C_AVAILABLE = True
try:
    _BUS = smbus.SMBus(1)
except Exception as e:
    print(f"Erreur sur le bus I2C : {e}")
    I2C_AVAILABLE = False

_REG_CONFIG = 0x00
_REG_SHUNTVOLTAGE = 0x01
_REG_BUSVOLTAGE = 0x02
_REG_POWER = 0x03
_REG_CURRENT = 0x04
_REG_CALIBRATION = 0x05


class INA219:
    def __init__(self, addr=0x43):
        self.addr = addr
        self._cal_value = 26868
        self._current_lsb = 0.1524
        self._power_lsb = 0.003048
        self.setup()

    def read(self, address):
        try:
            data = _BUS.read_i2c_block_data(self.addr, address, 2)
            return (data[0] << 8) | data[1]
        except IOError:
            return 0

    def write(self, address, data):
        try:
            temp = [(data >> 8) & 0xFF, data & 0xFF]
            _BUS.write_i2c_block_data(self.addr, address, temp)
        except IOError:
            pass

    def setup(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        self.write(_REG_CONFIG, 0x019F)

    def getBusVoltage_V(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        raw = self.read(_REG_BUSVOLTAGE)
        return (raw >> 3) * 0.004

    def getCurrent_mA(self):
        raw = self.read(_REG_CURRENT)
        if raw > 32767:
            raw -= 65536
        return raw * self._current_lsb

    def getPower_W(self):
        self.write(_REG_CALIBRATION, self._cal_value)
        raw = self.read(_REG_POWER)
        return raw * self._power_lsb


def get_lipo_percent(voltage):
    """
    Estime le pourcentage restant d'une batterie Li-Po 1S
    en utilisant une table de correspondance non-linéaire.
    """
    mapping = [
        (4.15, 100),
        (4.10, 95),
        (4.05, 90),
        (3.98, 80),
        (3.92, 70),
        (3.87, 60),
        (3.82, 50),
        (3.78, 40),
        (3.74, 30),
        (3.70, 20),
        (3.65, 10),
        (3.60, 5),
        (3.40, 0),
    ]

    if voltage >= mapping[0][0]:
        return 100
    if voltage <= mapping[-1][0]:
        return 0

    for i in range(len(mapping) - 1):
        v_high, p_high = mapping[i]
        v_low, p_low = mapping[i + 1]
        if v_high >= voltage >= v_low:
            ratio = (voltage - v_low) / (v_high - v_low)
            return int(p_low + (p_high - p_low) * ratio)
    return 0


_INA_INSTANCE = None


def get_battery_datas():
    global _INA_INSTANCE

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
        if _INA_INSTANCE is None:
            _INA_INSTANCE = INA219(addr=0x43)

        v = _INA_INSTANCE.getBusVoltage_V()
        c = _INA_INSTANCE.getCurrent_mA()
        p_watt = _INA_INSTANCE.getPower_W()

        percent = get_lipo_percent(v)

        return {
            "voltage": round(v, 2),
            "percent": percent,
            "current": int(c),  # En mA
            "power": round(p_watt, 2),  # En W
            "online": True,
        }

    except Exception as e:
        print(f"Erreur INA219: {e}")
        _INA_INSTANCE = None
        return default
