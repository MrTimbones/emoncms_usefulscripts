#!/usr/bin/python
# -*- coding: UTF-8 -*-
# ----------------------------------------------------------------------------------
# SDS011 Nova PM Sensor to Emoncms bridge
# ----------------------------------------------------------------------------------

emoncms_host = "http://localhost"
emoncms_apikey = "a351e81bed836fb7bd99d9767b136be5"
emoncms_nodename = "pmsensor"

import serial, time, struct, urllib2, time

ser = serial.Serial("/dev/ttyUSB0", baudrate=9600, stopbits=1, parity="N", timeout=2)

ser.flushInput()

byte, lastbyte = "\x00", "\x00"

# Reading arrive from SDS011 every second, we average 10 readings every 10 seconds and send the result to emoncms
pm_25_sum = 0
pm_10_sum = 0
count = 0

lasttime = 0

while True:
    lastbyte = byte
    byte = ser.read(size=1)
    
    # Valid packet header
    if lastbyte == "\xAA" and byte == "\xC0":
        sentence = ser.read(size=8) # Read 8 more bytes
        readings = struct.unpack('<hhxxcc',sentence) # Decode the packet - big endian, 2 shorts for pm2.5 and pm10, 2 reserved bytes, checksum, message tail
        
        pm_25 = readings[0]/10.0
        pm_10 = readings[1]/10.0
        
        pm_25_sum += pm_25
        pm_10_sum += pm_10
        count = count + 1
    
    # Send to emoncms every 10 seconds
    if (time.time()-lasttime)>=10.0:
        lasttime = time.time()
        if count>0:
            pm_25 = round(pm_25_sum/count,3)
            pm_10 = round(pm_10_sum/count,3)
            print "PM 2.5:",pm_25,"μg/m^3  PM 10:",pm_10,"μg/m^3"
            contents = urllib2.urlopen(emoncms_host+'/input/post?node='+emoncms_nodename+'&fulljson={"pm_25":'+str(pm_25)+',"pm_10":'+str(pm_10)+'}&apikey='+emoncms_apikey).read()


