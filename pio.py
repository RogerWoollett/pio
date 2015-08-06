# pio.py
# classes using Pigpio
# written by Roger Woollett
import pigpio as pg
import socket as soc

class Pio():
	# to override the default host name (ip address) and port
	# assign to Pio.host and/or Pio.port in the calling file
	
	# static data
	_started = False
	_refcount = 0
	
	def __init__(self):
		Pio._refcount += 1
		self._closed = False
		if not Pio._started:
			
			try:
				Pio.host
			except AttributeError:
				Pio.host = 'localhost'
				
			try:
				Pio.port
			except AttributeError:
				Pio.port = 8888
				
			# now see if daemon is running
			try:
				socket = soc.create_connection((Pio.host,Pio.port))
			except:
				dok = False
			else:
				socket.close()
				dok = True
			
			if not dok:
				self._closed = True
				raise RuntimeError('Cannot connect to pigpio daemon')
					
			Pio.pi = pg.pi(Pio.host,Pio.port)
			Pio._started = True
			
	def close(self):
		Pio._refcount -= 1
		self._closed = True

		if Pio._refcount == 0:
			Pio.pi.stop()
			Pio._started = False
			
	def __del__(self):
		if not self._closed:
			raise RuntimeError('Close not called in Pio object')

class ADC(Pio):
	# class to access a MCP3008 A to D converter
	# pins used are:
	# Name board(gpio) - chip pin
	# MOSI	19(GPIO10)	11 - data in
	# MISO	21(GPIO9)	12 - data out
	# SCLK	23(GPIO11)	13 - clock
	# CE0	24(GPIO8)	10 - chip select
	# CE1	26(GPIO7)	10 - chip select on second chip
	# There is a second set of pins used on A+ B+ and Pi2
	# This auxilliary port is not supported as yet
	def __init__(self,chip):
		Pio.__init__(self)
		# chip should be 0 (chip connected to CE0) or 1 (CE1)
		if chip < 0 or chip > 1:
			Pio.close(self)
			raise RuntimeError('chip must be 0 (CE0) or 1 (CE1)')
			
		self.handle = Pio.pi.spi_open(chip,50000,0)
		
	def close(self):
		Pio.pi.spi_close(self.handle)
		Pio.close(self)
		
	def read(self,channel):
		# channel corresponds to pins 1 (ch0) to 8 (ch7)
		# we have to send three bytes
		# byte 0 has 7 zeros and a start bit
		# byte 1 has the top bit set to indicate
		# single rather than differential operation
		# the next three bits contain the channel
		# the bottom four bits are zero
		# byte 2 contains zeros (don't care)
		# 3 bytes are returned
		# byte 0 is ignored
		# byte 1 contains the high 2 bits
		# byte 2 contains the low 8 bits
		if channel < 0 or channel > 7:
			raise RuntimeError('channel must be 0 - 7')
			
		(count,data) = Pio.pi.spi_xfer(self.handle,[1,(8 + channel) << 4,0])
		if count > 0:
			return (data[1] << 8) + data[2]
		else:
			return 0

class Motor(Pio):
	# Motor controls two pins which are connected to
	# one half of a dual H-Bridge controller
	# I use a SN74110NE
	def __init__(self,pin1,pin2,frequency = 15000):
		Pio.__init__(self)
		# For forward pwm to pin 1, 0 to pin2
		# for reverse pwm to pin 2, 0 to pin 1
		# speed (duty cycle) input is 0 - 100
		# When a change of direction is requested
		# the motor is stopped but only briefly.
		# Caller should arrange a longer spin down/up
		# time if required
		self._pin1 = pin1
		self._pin2 = pin2
		Pio.pi.set_mode(pin1,pg.OUTPUT)
		Pio.pi.set_mode(pin2,pg.OUTPUT)
		
		Pio.pi.set_PWM_range(pin1,100)
		Pio.pi.set_PWM_frequency(pin1,frequency)
		Pio.pi.set_PWM_range(pin2,100)
		Pio.pi.set_PWM_frequency(pin2,frequency)
		
		self._forward = True
		self.stop()
	
	def close(self):
		self.stop()
		Pio.close(self)
		
	def go(self,duty,forward = True):
		if self._forward != forward:
			self.stop()
			self._forward = forward
			
		if forward:
			Pio.pi.set_PWM_dutycycle(self._pin1,duty)
			Pio.pi.write(self._pin2,0)
		else:
			Pio.pi.set_PWM_dutycycle(self._pin2,duty)
			Pio.pi.write(self._pin1,0)
	
	def stop(self):
		Pio.pi.write(self._pin1,0)
		Pio.pi.write(self._pin2,0)
		
class Servo(Pio):
	# Drive a servo motor
	# pin should be connected to the control
	# wire to the servo
	# The ground servo wire must be connected to pi ground 
	def __init__(self,pin):
		Pio.__init__(self)
	
		self.pin = pin
		Pio.pi.set_mode(pin,pg.OUTPUT)
		
		# position 0 corresponds to 150 (1.5msec pulse)
		Pio.pi.set_PWM_range(pin,2000)
		
		# standard frequency for servos is 50Hz
		Pio.pi.set_PWM_frequency(pin,50)
		
		# make sure we start with servo off
		self.stop()
			
	def set(self,pos):
		# set servo position
		# pos should be in range -100 to 100
		duty = 150 + pos/2
		Pio.pi.set_PWM_dutycycle(self.pin,duty)
		
	def stop(self):
		# turn off pwm
		Pio.pi.set_PWM_dutycycle(self.pin,0)
				
	def close(self):
		# call this when program closes
		self.stop()
		Pio.close(self)
