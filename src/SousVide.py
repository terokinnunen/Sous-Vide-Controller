#!/usr/bin/env python

from getopt import getopt, GetoptError
import sys
import os
from Phidgets.Devices.TemperatureSensor import TemperatureSensor
from time import sleep, time

__author__ = 'Tero Kinnunen'
__version__ = '0.1'
__date__ = 'Jan 23 2011'

class PhidgetTemperatureSensor:
    MEAS_AVERAGE_COUNT = 5
    MEAS_AVERAGE_DELAY = 0.5
    
    def __init__(self, sensor_index=0):
        self.sensor_index = sensor_index
        self.temperatureSensor = TemperatureSensor()
        self.temperatureSensor.openPhidget()
        print("Waiting for attach....")
        self.temperatureSensor.waitForAttach(10000)
        print "Temperature sensor %s (serial %d)\nSensor type %s input %d" % \
            (self.temperatureSensor.getDeviceName(), 
             self.temperatureSensor.getSerialNum(), 
             self.temperatureSensor.getDeviceType(), 
             self.sensor_index)
    
    def close(self):
        self.temperatureSensor.closePhidget()
        
    def get_temperature(self):
        measurements = []
        debug_str = []
        for i in range(self.MEAS_AVERAGE_COUNT):
            t = self.temperatureSensor.getTemperature(self.sensor_index)
            measurements.append(t)
            debug_str.append("%.2f" % t)
            sleep(self.MEAS_AVERAGE_DELAY)
        temp = self._average(measurements)
        debug = " ".join(debug_str)
        return (temp, debug)
    
    def _average(self, values):
        return sum(values)/len(values)
    
    def _median(self, values):
        return sorted(values)[len(values)/2]

class PlugController:
    def __init__(self, controller_id):
        self.controller_id = controller_id
        self.on = True
        self.set_on(False)
    def set_on(self, on):
        if on != self.on:
            self.on = on
            if on:
                os.system("tdtool --on %s" % self.controller_id)
            else:
                os.system("tdtool --off %s" % self.controller_id)

class ControllerAlgorithm:
    def set_threshold(self, temperature):
        self.threshold = temperature
    def get_threshold(self):
        return self.threshold
    def get_setting(self, temperature):
        return temperature < self.threshold

class SousVide:
    def __init__(self, temperature_sensor, plug_controller, controller_algorithm):
        self.temperature_sensor = temperature_sensor
        self.plug_controller = plug_controller
        self.controller_algorithm = controller_algorithm
        self.update_interval = 10
        
    def start(self):
        start = int(time())
        log = open("SousVideLog.csv", "a")
        print " s\t  t    T   on/off  (measurements)"
        while True:
            round_time = int(time())
            t, debuginfo = self.temperature_sensor.get_temperature()
            on = self.controller_algorithm.get_setting(t)
            self.plug_controller.set_on(on)
            threshold = self.controller_algorithm.get_threshold()
            print "%d\t%.2f %.2f %s (%s)" % (round_time-start, t, threshold, str(on), debuginfo)
            log.write("%d\t%f\t%f\t%d\n" % (round_time, t, threshold, self._bool_int(on)))
            sleep(self.update_interval + round_time - time())
            
    def set_update_interval(self, seconds):
        self.update_interval = seconds
        
    def _bool_int(self, bool):
        if bool:
            return 1
        else:
            return 0


def usage():
    print """Usage: SousVide [options] temperature
    Options:
        -h, --help: Show help
        -p, --plug: Plug identifier for tdtool command (default=1)
        -s, --sensor: Temperature sensor index (default=0)
        -i, --interval: Update interval in seconds (default=10)
    """

if __name__ == "__main__":
    plugid = "1"
    sensor_index = 0
    update_interval = 10
    try:
        opts, args = getopt(sys.argv[1:], "hp:i:", ["help", "plug=", "interval="])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
            if opt in ("-p", "--plug"):
                plugid = arg
            if opt in ("-s", "--sensor"):
                sensor_index = int(arg)
            if opt in ("-i", "--interval"):
                update_interval = int(arg)
        if len(args) != 1:
            usage()
            sys.exit(1)
        else:
            temp = float(args[0])
    except GetoptError:
        usage()
        sys.exit(1)
    try:
        sensor = PhidgetTemperatureSensor(sensor_index)
        plug_controller = PlugController(plugid)
        controller = ControllerAlgorithm()
        controller.set_threshold(temp)
        sous_vide = SousVide(sensor, plug_controller, controller)
        print "Starting SousVide control. Use Ctrl-C to exit."
        sous_vide.start()
    except KeyboardInterrupt:
        pass
    except:
        print "Unexpected error:", sys.exc_info()[0]
    finally:
        print "Shutting down..."
        sensor.close()
    
