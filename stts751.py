"""
.. module:: stts751

**************
STTS751 Module
**************

This module contains the driver for STMicroelectronics STTS751 temperature sensor. 

Its highlight is that it outputs its measurement in a 9-bit to 12-bit (configurable) resolution. (`datasheet <https://www.st.com/resource/en/datasheet/stts751.pdf>`_).
    """


import i2c

STTS751_MODEL_0 = 0x00  # Model 0 (default)
STTS751_MODEL_1 = 0x40  # Model 1 

STTS751_ADDRESS_0 = (0x48 << 1) # pull up resistor = 7.5K (default)
STTS751_ADDRESS_1 = (0x49 << 1) # pull up resistor = 12K
STTS751_ADDRESS_2 = (0x38 << 1) # pull up resistor = 20K 
STTS751_ADDRESS_3 = (0x39 << 1)

STTS751_RES_9  = 0x08 # 9 bits
STTS751_RES_10 = 0x00 # 10 bits (default)
STTS751_RES_11 = 0x04 # 11 bits
STTS751_RES_12 = 0x0c # 12 bits

ODR_AVAILABLE = {
    "ODR_OFF"      : 0x80,
    "ODR_ONE_SHOT" : 0x90,
    "ODR_62mHz5"   : 0x00,
    "ODR_125mHz"   : 0x01,
    "ODR_250mHz"   : 0x02,
    "ODR_500mHz"   : 0x03,
    "ODR_1Hz"      : 0x04,
    "ODR_2Hz"      : 0x05,
    "ODR_4Hz"      : 0x06,
    "ODR_8Hz"      : 0x07,
    "ODR_16Hz"     : 0x08,
    "ODR_32Hz"     : 0x09,
}

REG_TEMPERATURE_H    = 0x00
REG_STATUS           = 0x01
REG_TEMPERATURE_L    = 0x02
REG_CONFIGURATION    = 0x03
REG_CONV_RATE        = 0x04
REG_HIGH_LIMIT_H     = 0x05
REG_HIGH_LIMIT_L     = 0x06
REG_LOW_LIMIT_H      = 0x07
REG_LOW_LIMIT_L      = 0x08
REG_ONESHOT          = 0x0f
REG_THERM            = 0x20
REG_THERM_HYSTERESIS = 0x21
REG_SMBUS_TIMEOUT    = 0x22
REG_PRODUCT_ID       = 0xfd
REG_MFG_ID           = 0xfe
REG_REVISION_ID      = 0xff

CONF_MASK1     = 0x80
CONF_RUNSTOP   = 0x40
CONF_RES_MASK  = 0x0c
CONV_RATE_MASK = 0x0f

STATUS_BUSY  = 0x80
STATUS_THIGH = 0x40
STATUS_LOW   = 0x20
STATUS_THURM = 0x01


class STTS751():
    """

.. class:: STTS751(drvsel,address=0x48,clk=400000)

    Creates an intance of a new STTS751.

    :param drvsel: I2C Bus used `( I2C0 )`
    :param address: Slave address, default 0x48
    :param clk: Clock speed, default 400kHz

    Example: ::

        from stm.stts751 import stts751

        temp_sens = stts751.STTS751( I2C0 )
        temp = temp_sens.get_temp()

    """
    def __init__(self, drvsel, address=0x48, clk=400000):
        self.port             = i2c.I2C(drvsel, address, clk)
        self.odr              = ODR_AVAILABLE["ODR_125mHz"]
        self.resolution       = STTS751_RES_12
        self.low_th           = 1
        self.high_th          = 50
        self.int_enable       = False
        self.therm_limit      = 0
        self.therm_hyst_limit = 0
        self.timeout          = False

        try:
            self.port.start()
        except PeripheralError as e:
            print(e)

        self.enable(self.odr, self.resolution)
        self.set_low_temp_threshold(self.low_th)
        self.set_high_temp_threshold(self.high_th)
        self.set_event_interrupt(True)
        self.set_timeout(False)
        self.therm_limit = self._read(REG_THERM, 1)[0]
        self.therm_hyst_limit = self._read(REG_THERM_HYSTERESIS, 1)[0]

    def _write(self, addr, data):
        buffer = bytearray(1)
        buffer[0] = addr
        buffer.append(data)
        self.port.write(buffer)

    def _read(self, addr, num_bytes):
        return self.port.write_read(addr, num_bytes)

    def _set_resolution(self, nbit):
        try:
            conf = self._read(REG_CONFIGURATION, 1)[0]
            conf |= nbit
            self._write(REG_CONFIGURATION, conf)
            return True
        except Exception as e:
            # print(e)
            return False

    def _set_odr(self, odr):
        try:
            cr = self._read(REG_CONV_RATE, 1)[0]
            cr = odr & 0x0F
            self._write(REG_CONV_RATE, cr)
            conf = self._read(REG_CONFIGURATION, 1)[0]
            if (odr & 0x80) >> 7:
                conf |= 0x02
            else:
                conf &= 0xFD
            self._write(REG_CONFIGURATION, conf)
            if odr == ODR_AVAILABLE["ODR_ONE_SHOT"]:
                self._write(REG_ONESHOT, 0xAA)
            return True
        except Exception as e:
            # print(e)
            return False

    def enable(self, odr=ODR_AVAILABLE["ODR_125mHz"], resolution=STTS751_RES_12):
        """

.. method:: enable(odr=ODR_AVAILABLE["ODR_125mHz"], resolution=STTS751_RES_12)

        Sets the device's configuration registers.
    
        **Parameters:**
    
        * **odr** : sets the Output Data Rate of the device. Available values are:
    
            ====== ================= ===================================================
            Value  Output Data Rate  Constant Name
            ====== ================= ===================================================
            0x00   62,5 Mhz          ODR_AVAILABLE["ODR_62mHz5"]
            0x01   125 MHz           ODR_AVAILABLE["ODR_125mHz"]
            0x02   250 MHz           ODR_AVAILABLE["ODR_250mHz"]
            0x03   500 MHz           ODR_AVAILABLE["ODR_500mHz"]
            0x04   1 Hz              ODR_AVAILABLE["ODR_1Hz"] 
            0x05   2 Hz              ODR_AVAILABLE["ODR_2Hz"]
            0x06   4 Hz              ODR_AVAILABLE["ODR_4Hz"]
            0x07   8 Hz              ODR_AVAILABLE["ODR_8Hz"]  
            0x08   16 Hz             ODR_AVAILABLE["ODR_16Hz"]
            0x09   32 Hz             ODR_AVAILABLE["ODR_32Hz"]
            0x80   OFF               ODR_AVAILABLE["ODR_OFF"]
            0x90   ONE SHOT          ODR_AVAILABLE["ODR_ONE_SHOT"]
            ====== ================= ===================================================
        
        * **resolution** : sets the Resolution in bit of the conversion. Available values are:
    
            ====== ===================  ====================== =============
            Value  N bit                Costant Name           in °C/LSB
            ====== ===================  ====================== =============
            0x08   9                    STTS751_RES_9          0.5 °C/LSB
            0x00   10                   STTS751_RES_10         0.25 °C/LSB
            0x04   11                   STTS751_RES_11         0.125 °C/LSB
            0x0c   12                   STTS751_RES_12         0.0625 °C/LSB
            ====== ===================  ====================== =============
    
        Returns True if configuration is successful, False otherwise.


        """
        if odr not in [x for x in ODR_AVAILABLE.values()]:
            raise ValueError
        if odr == self.odr and resolution == self.resolution:
            return True
        if odr == ODR_AVAILABLE["ODR_16Hz"] and resolution == STTS751_RES_12:
            raise ValueError
        if odr == ODR_AVAILABLE["ODR_32Hz"] and resolution in (STTS751_RES_12, STTS751_RES_11):
            raise ValueError
        res = self._set_resolution(resolution)
        if res:
            res = self._set_odr(odr)
            if res:
                self.odr = odr
                self.resolution = resolution
        return res


    def disable(self):
        """

.. method:: disable()

        Disables the sensor.

        Returns True if configuration is successful, False otherwise.

        """
        if self.odr == ODR_AVAILABLE["ODR_OFF"]:
            return True
        res = self._set_odr(ODR_AVAILABLE["ODR_OFF"])
        if res:
            self.odr = ODR_AVAILABLE["ODR_OFF"]
        return res

    def get_status(self):
        """

.. method:: get_status()

        Retrieves the sensor flag status.

        Returns a dictionary with following key/value pairs:

            ====== =============================== 
            Key    Note             
            ====== =============================== 
            busy   If True, Sensor is Busy                  
            t_low  If True, Temp under threshold                   
            t_high If True, Temp over threshold
            therm  If True, High internal Temp                    
            ====== =============================== 

        """
        status = self._read(REG_STATUS, 1)[0]
        st_dict = {
            "busy"  : True if status & 0x80 >> 7 else False,
            "t_low" : True if status & 0x40 >> 6 else False,
            "t_high": True if status & 0x20 >> 5 else False,
            "therm" : True if status & 0x01 else False,
        }   
        return st_dict


    def get_sensor_id(self):
        """

.. method:: get_sensor_id()

        Retrieves product_id, manufacturer_id, revision_id in one call.

        Returns product_id, manufacturer_id, revision_id

        """
        product_id      = self._read(REG_PRODUCT_ID, 1)[0]
        manufacturer_id = self._read(REG_MFG_ID, 1)[0]
        revision_id     = self._read(REG_REVISION_ID, 1)[0]
        return product_id, manufacturer_id, revision_id

    def get_temp(self, raw=False):
        """

.. method:: get_temp(raw=False)

        Retrieves temperature in one call; if raw flag is enabled, returns raw register values.

        Returns temp

        """
        
        tmp_h = self._read(REG_TEMPERATURE_H, 1)[0]
        tmp_l = self._read(REG_TEMPERATURE_L, 1)[0]

        tmp_raw = (tmp_h << 8) + tmp_l
        if raw:
            return tmp_raw

        if ((tmp_raw & 0x8000) >> 15):
            tmp_raw = -(0x8000 - (0x7fff & tmp_raw))

        return tmp_raw / 256.0

    def set_low_temp_threshold(self, level):
        """

.. method:: set_low_temp_threshold(level)

        Sets the low temperature threshold. When real temperature goes down the low temperature level, if interrupt is enabled, the sensor send an interrupt signal in its interrupt pin.

        """
        raw = level * 256
        rl = raw & 0x00FF
        rh = (raw & 0xFF00) >> 8
        self._write(REG_LOW_LIMIT_L ,rl)
        self._write(REG_LOW_LIMIT_H ,rh)
        self.low_th = level

    def set_high_temp_threshold(self, level):
        """

.. method:: set_high_temp_threshold(level)

        Sets the high temperature threshold. When real temperature goes up the high temperature level, if interrupt is enabled, the sensor send an interrupt signal in its interrupt pin.

        """
        raw = level * 256
        rl = raw & 0x00FF
        rh = (raw & 0xFF00) >> 8
        self._write(REG_HIGH_LIMIT_L ,rl)
        self._write(REG_HIGH_LIMIT_H ,rh)
        self.high_th = level

    def set_event_interrupt(self, enable):
        """

.. method:: set_event_interrupt(enable)

        Enables the interrupt pin. Available values for 'enable' flag are 'True' or 'False'.

        """
        conf = self._read(REG_CONFIGURATION, 1)[0]
        if enable:
            conf &= 0b0111111
        else:
            conf |= 0b1000000
        self._write(REG_CONFIGURATION, conf)
        self.int_enable = enable  

    def set_therm_limit(self, level):
        """

.. method:: set_therm_limit(level)

        Sets the Thermal threshold. Whenever the temperature exceeds the value of the therm limit, the Addr/Therm output will be asserted (low)
        Available 'level' values are from -127 to 127 range.
        
        """
        if level < -127 or level > 127:
            raise ValueError
        self._write(REG_THERM, level)
        self.therm_limit = level

    def set_therm_hysteresis_limit(self, level):
        """

.. method:: set_therm_hysteresis_limit(level)

        Sets the Thermal hysteresis threshold. Once Therm output has asserted, it will not de-assert until the temperature has fallen below the respective therm limit minus the therm hysteresis value. 
        Available 'level' values are from -127 to 127 range.
        
        """
        if level < -127 or level > 127:
            raise ValueError
        self._write(REG_THERM_HYSTERESIS, level)
        self.therm_hyst_limit = level

    def set_timeout(self, enable):
        """

.. method:: set_timeout(enable)

        Enables the timeout for the sensor readings (from 25 to 35 ms). Available values for 'enable' flag are 'True' or 'False'.

        """
        reg = self._read(REG_SMBUS_TIMEOUT, 1)[0]
        if enable:
            reg &= 0b0111111
        else:
            reg |= 0b1000000
        self._write(REG_SMBUS_TIMEOUT, reg)
        self.timeout = enable    
        

