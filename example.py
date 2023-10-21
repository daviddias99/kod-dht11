import dht11
import RPi.GPIO as GPIO
import time

DATA_GPIO = 8
GPIO.setwarnings(False)
sensor = dht11.DHT11(DATA_GPIO, True)

for _ in range(25):
  GPIO.setmode(GPIO.BOARD)
  print(sensor.read_sensor_data())
  time.sleep(1)

GPIO.cleanup()

