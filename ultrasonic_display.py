from gpiozero import DistanceSensor, TonalBuzzer
from gpiozero.tones import Tone
from RPLCD.i2c import CharLCD
from time import monotonic, sleep

# ---------------- LCD ----------------
# I2C LCD (address: 0x27, 16x2)
lcd = CharLCD('PCF8574', address=0x27, port=1, cols=16, rows=2, charmap='A00')
lcd.backlight_enabled = True

# ---------------- Ultrasonic Sensors ----------------
# Arduino TRIG1=4 ECHO1=3  -> RPi GPIO: nastav si podle svého zapojení
# Arduino TRIG2=11 ECHO2=10 -> RPi GPIO: nastav si podle svého zapojení
#
# TY ses držel: A: trigger=17 echo=27, B: trigger=18 echo=22
TRIG1, ECHO1 = 17, 27
TRIG2, ECHO2 = 18, 22

sensor1 = DistanceSensor(trigger=TRIG1, echo=ECHO1, max_distance=2.0)
sensor2 = DistanceSensor(trigger=TRIG2, echo=ECHO2, max_distance=2.0)

# ---------------- Passive Buzzer ----------------
# Arduino BUZZER_PIN=9 -> RPi GPIO: nastav si podle zapojení
BUZZER_PIN = 9
buzzer = TonalBuzzer(BUZZER_PIN)

# ---------------- Parameters ----------------
gate_distance_m = 1.30     # meters between sensors
speed_limit_kmh = 40.0     # speed limit
trigger_dist_cm = 15.0     # detection distance (cm)
min_dt_s = 0.05            # ignore false triggers

# threshold_distance expects meters
threshold_m = trigger_dist_cm / 100.0
sensor1.threshold_distance = threshold_m
sensor2.threshold_distance = threshold_m

# ---------------- State Variables ----------------
first_gate_triggered = False
speed_calculated = False
t1 = None
t2 = None

# ---------------- Helpers ----------------
def lcd_show(line1: str, line2: str = ""):
    # keep it simple & close to Arduino behavior
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(line1[:16].ljust(16))
    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:16].ljust(16))

def beep_3_times():
    for _ in range(3):
        buzzer.play(Tone(2000))  # ~2kHz
        sleep(0.2)
        buzzer.stop()
        sleep(0.2)

# ---------------- Startup ----------------
lcd_show("Speed Detector", "Waiting...")

try:
    while True:
        # Read distances (Arduino did: d1 -> delay(40ms) -> d2)
        d1_cm = sensor1.distance * 100.0
        sleep(0.04)
        d2_cm = sensor2.distance * 100.0

        # First sensor detects object
        if (not first_gate_triggered) and (0 < d1_cm < trigger_dist_cm):
            first_gate_triggered = True
            t1 = monotonic()

            lcd_show("Vehicle detected", "Measuring...")

        # Second sensor detects object
        if first_gate_triggered and (not speed_calculated) and (0 < d2_cm < trigger_dist_cm):
            t2 = monotonic()
            speed_calculated = True

            delta_t = t2 - t1 if (t1 is not None) else 0.0

            if delta_t > min_dt_s:
                speed_kmh = (gate_distance_m / delta_t) * 3.6

                # line1: Speed:xx.xkm/h
                line1 = f"Speed:{speed_kmh:5.1f}km/h"
                if speed_kmh > speed_limit_kmh:
                    lcd_show(line1, "Over Speed!")
                    beep_3_times()
                else:
                    lcd_show(line1, "Normal")
            else:
                lcd_show("Invalid data", "")

            sleep(3.0)

            # Reset system (same as Arduino)
            first_gate_triggered = False
            speed_calculated = False
            t1 = None
            t2 = None

            lcd_show("Speed Detector", "Waiting...")

        sleep(0.02)

except KeyboardInterrupt:
    lcd.clear()
    lcd.write_string("Stopped.".ljust(16))
    buzzer.stop()
