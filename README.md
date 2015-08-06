# pio
Classes to control devices usig pigpio

This is a set of classes to control various devices.
The pigpio library is used to control the GPIO pins so these classes
can be used on a machine other than the raspberry pi.
Initialisation of the pigpio system is handled in the bas class Pio.
ADC controls a MCP3008 A to D chip
Motor can be used to control a DC motor
Servo controls a servo motor
Stepper controls a stepper motor using full or half steps
Currently the only function gives a single step.

