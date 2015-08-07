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
	# MOSI  38(GPIO20)  11 - data in
	# NISO  35(GPIO19)  12 - data out
	# SCLK  40(GPIO21)  13 - clock
	# CE0   19(GPIO18)	10 - chip select
	# CE1   11(GPIO17)  10 - chip select
	# CE2   36(GPIO16)	10 - chip select
	def __init__(self,ce,aux = False):
		# set aux true to use second port
		Pio.__init__(self)
		
		# standard port has two chip select, second port has three
		if aux:
			flags = 0x100	# set A bit
			if ce < 0 or ce > 2:
				Pio.close(self)
				raise RuntimeError('chip must be 0 (CE0), 1 (CE1) or 2 (CE2)')
		else:
			flags = 0
			if ce < 0 or ce > 1:
				Pio.close(self)
				raise RuntimeError('chip must be 0 (CE0) or 1 (CE1)')
					
		self.handle = Pio.pi.spi_open(ce,50000,flags)

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
		
# Using just the GPIO pins it is possible to drive
# a stepper motor in full or half steps.
# using four pins the two coils can be driven +, - or off
# if only fill steps are needed two pins can be saved by 
# using an inverter (e.g. 74HC04B1) to control the polarity
# of the 'other' end of the coilADC 
class Stepper(Pio):
	# Drive a stepper motor
	# Testing done with a SN754410 H-bridge
	# connections
	# GPIO    H-bridge     wire
	# pin1    7            green
	# pin2    2            red
	# pin3    15           yellow
	# pin4    9            blue
	#
	# Motor   H-bridge     wire
	#         6            green
	#         3            red
	#         14           yellow
	#         11           blue
	# 
	# pi 5v to pin 1 9 16
	# 12v to pin 8
	# states contains the sequence of pin states

	def __init__(self,pin1,pin2,pin3 = 0,pin4 = 0, halfstep = False):
		Pio.__init__(self)
		
		if pin3 == 0:
			# setup for 2 pin moded
			self.pins = (pin1,pin2)
			self.states = ((1,1),(0,1),(0,0),(1,0))
		else:
			# 4 pin full and half step
			self.pins = (pin1,pin2,pin3,pin4)
			if halfstep:
				self.states = ((1,0,0,0),(1,0,1,0),(0,0,1,0),(0,1,1,0), \
							   (0,1,0,0),(0,1,0,1),(0,0,0,1),(1,0,0,1))
			else:
				self.states = ((1,0,1,0),(0,1,1,0),(0,1,0,1),(1,0,0,1))		

		self.num_states = len(self.states)
		self.num_pins = len(self.pins)

		# set pins to output and low
		for pin in self.pins:
			Pio.pi.set_mode(pin,pg.OUTPUT)
			Pio.pi.write(pin,0)
		
		# start of with state 0
		self.state = 0
		
	def step(self,forward = True):
		# do one step in forward or reverse
		if forward:
			self.state += 1
			if self.state >= self.num_states:
				self.state = 0
		else:
			self.state -= 1
			if self.state < 0:
				self.state = self.num_states - 1
		
		# set local variable for efficiency
		state = self.states[self.state]
		
		# now set the pins according to state
		for i in range (0,self.num_pins):
			Pio.pi.write(self.pins[i],state[i])
		
	def stop(self):
		# set all pins low
		for i in range (0,self.num_pins):
			Pio.pi.write(self.pins[i],0)
			
	def close(self):
		# tidy up
		self.stop()
		Pio.close(self)
		
		
		
