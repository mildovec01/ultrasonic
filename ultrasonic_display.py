from gpiozero import DistanceSensor
from time import monotonic, sleep
from RPLCD.i2c import CharLCD

# ---------- LCD ----------
# Nejčastěji adresa 0x27, někdy 0x3f. Když to nic nezobrazuje, změň.
lcd = CharLCD('PCF8574', address=0x27, port=1, cols=16, rows=2, charmap='A00')

def lcd_show(speed_kmh: float, label: str):
    # řádek 1: Your speed: 50.7
    # řádek 2: Too fast!
    lcd.clear()
    line1 = f"Your speed:{speed_kmh:5.1f}"
    line2 = label
    lcd.write_string(line1[:16])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:16])

def lcd_idle():
    lcd.clear()
    lcd.write_string("Ready...")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Pass A then B")

# ---------- SENSORY ----------
a_sensor = DistanceSensor(echo=27, trigger=17, max_distance=1)
b_sensor = DistanceSensor(echo=22, trigger=18, max_distance=1)

# vzdálenost mezi branama (metry)
distance_m = 0.40

# brána (metry)
a_sensor.threshold_distance = 0.25
b_sensor.threshold_distance = 0.25

# filtr na šum / double-trigger (sekundy)
min_dt = 0.03

# rychlostní “město” pravidla (km/h)
TOO_SLOW_MAX = 20.0     # pod 20: moc pomalu
NORMAL_MAX   = 50.0     # 20–50: ok, nad 50: moc rychle

start_time = None
stop_time = None

def start(t):
    if t is None and a_sensor.in_range:
        return monotonic()
    return t

def finish(t_stop, t_start):
    if t_start is not None and t_stop is None and b_sensor.in_range:
        return monotonic()
    return t_stop

def classify_speed(speed_kmh: float) -> str:
    if speed_kmh > NORMAL_MAX:
        return "Too fast!"
    if speed_kmh < TOO_SLOW_MAX:
        return "Too slow"
    return "Normal"

# ---------- RUN ----------
try:
    lcd_idle()

    # odjištění na startu (ať to nechytá samo)
    while a_sensor.in_range or b_sensor.in_range:
        sleep(0.05)

    while True:
        start_time = start(start_time)
        stop_time = finish(stop_time, start_time)

        if start_time is not None and stop_time is not None:
            dt = stop_time - start_time

            if dt >= min_dt:
                speed_m_s = distance_m / dt
                speed_kmh = speed_m_s * 3.6
                label = classify_speed(speed_kmh)

                print(f"dt = {dt:.3f} s | speed = {speed_kmh:.1f} km/h | {label}")
                lcd_show(speed_kmh, label)
            else:
                print(f"Ignored - dt too small: {dt:.4f} s")
                lcd.clear()
                lcd.write_string("Ignored noise")
                lcd.cursor_pos = (1, 0)
                lcd.write_string(f"dt:{dt:.4f}"[:16])

            # reset
            start_time = None
            stop_time = None

            # odjištění po průjezdu
            while a_sensor.in_range or b_sensor.in_range:
                sleep(0.02)

            # zpět do idle
            lcd_idle()

        sleep(0.02)

except KeyboardInterrupt:
    lcd.clear()
    lcd.write_string("Stopped.")
    print("Stopped.")
