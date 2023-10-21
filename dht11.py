import RPi.GPIO as GPIO
import time
from typing import Tuple, List
from enum import Enum

class ReadStatus(Enum):
    OK = 0
    CHECKSUM_ERROR = 1
    NO_DATA_ERROR = 2
    SEQUENCE_ERROR = 3

class DHT11():

  def __init__(self, data_pin = 8, debug_mode = False) -> None:
    self.data_pin = data_pin
    self.UNCHANGED_COUNT_FOR_STOPPAGE = 100
    self.debug_mode = debug_mode

    if debug_mode:
      self.debug_file = open('debug.txt', 'w')

  def __del__(self):
    if self.debug_mode:
      self.debug_file.close()
    
  def setup_sensor(self):
    GPIO.setup(self.data_pin, GPIO.OUT)
    GPIO.output(self.data_pin, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(self.data_pin, GPIO.LOW)
    time.sleep(0.02)
    GPIO.output(self.data_pin, GPIO.HIGH)
    GPIO.setup(self.data_pin, GPIO.IN)

  def read_sensor_data(self) -> Tuple[ReadStatus, Tuple[float, float]]:
    self.setup_sensor()
    sensor_signal = self.read_signal()

    if len(sensor_signal) == 0:
      return (ReadStatus.NO_DATA_ERROR, (0.0 , 0.0))

    binary_signal = self.process_signal_into_binary(sensor_signal)

    return self.process_binary_signal(binary_signal)

  def read_signal(self):
    last_pin_value = 1
    successive_unchanged_input_count = 0
    sensor_signal = []

    while successive_unchanged_input_count != self.UNCHANGED_COUNT_FOR_STOPPAGE:
      current_pin_value = GPIO.input(self.data_pin)
      sensor_signal.append(current_pin_value)
      successive_unchanged_input_count = successive_unchanged_input_count + 1 if current_pin_value == last_pin_value else 0
      last_pin_value = current_pin_value

    if self.debug_mode:
      print('Raw signal: ', sensor_signal[:-self.UNCHANGED_COUNT_FOR_STOPPAGE], file=self.debug_file)

    return sensor_signal[:-self.UNCHANGED_COUNT_FOR_STOPPAGE]
  
  def process_signal_into_binary(self, signal) -> List[int]:
    last_val = signal[0]
    segment_lengths = []
    signal_length = 0

    for val in signal:
      if val != last_val:
        segment_lengths.append({ 'value': last_val, 'length': signal_length })
        signal_length = 0
      last_val = val
      signal_length += 1

    if self.debug_mode:
      print('Segment lengths', segment_lengths, file=self.debug_file)

    high_segments = list(filter(lambda segment : segment['value'] == 1, segment_lengths))
    max_high_segment_length = max(high_segments, key=lambda x : x['length'])['length']
    min_high_segment_length = min(high_segments, key=lambda x : x['length'])['length']

    binary_signal = []

    for segment in high_segments:
      # Check if length is closer to min (0) or max (1)
      dist_to_max = abs(segment['length'] - max_high_segment_length)
      dist_to_min = abs(segment['length'] - min_high_segment_length)  
      
      if dist_to_max < dist_to_min:
        binary_signal.append(1)
      else:
        binary_signal.append(0)

    if self.debug_mode:
      print('Binary signal: ', binary_signal, file=self.debug_file)
      print('Binary signal length:', len(binary_signal), file=self.debug_file)

    return binary_signal

  def process_binary_signal(self, binary_signal):
      # We need 40 segments, but first needs to be the first high signal sent by the sensor before starting
      if (len(binary_signal) != 41) and binary_signal[0] != 1:
        print('Sequence error', file=self.debug_file)
        return (ReadStatus.SEQUENCE_ERROR, (0.0, 0.0))
      
      # We don't actually need to process that first signal
      binary_signal = binary_signal[1:]

      # Some helper lambdas
      to_bin = lambda x : bin(int(''.join(map(str, x)), 2))
      to_int = lambda x : int(to_bin(x), 2)
      to_float = lambda integral_part, decimal_part : integral_part + (float(decimal_part) /10)

      rh_int = binary_signal[0:8]
      rh_dec = binary_signal[8:16]
      temp_int = binary_signal[16:24]
      temp_dec = binary_signal[24:32]
      checksum= binary_signal[32:40]
      checksum_received= to_int(to_bin(binary_signal[32:40]))
      checksum_calculated = (to_int(rh_int) + to_int(rh_dec) + to_int(temp_int) + to_int(temp_dec)) & 255

      if self.debug_mode:
        print('Binary signal (separated): ', to_bin(rh_int), to_bin(rh_dec), to_bin(temp_int), to_bin(temp_dec), to_bin(checksum), file=self.debug_file)
        print('Binary signal (to integer): ', to_int(to_bin(rh_int)), to_int(to_bin(rh_dec)), to_int(to_bin(temp_int)), to_int(to_bin(temp_dec)), checksum_received, file=self.debug_file)
        print('Checksum (received calculated): ', checksum_received, checksum_calculated, file=self.debug_file)
    
      if checksum_received != checksum_calculated:
        if self.debug_mode:
          print('Checksum error', file=self.debug_file)

        return (ReadStatus.CHECKSUM_ERROR, (0.0, 0.0))
      
      return (ReadStatus.OK, (to_float(to_int(to_bin(rh_int)), to_int(to_bin(rh_dec))), to_float(to_int(to_bin(temp_int)), to_int(to_bin(temp_dec)))))

