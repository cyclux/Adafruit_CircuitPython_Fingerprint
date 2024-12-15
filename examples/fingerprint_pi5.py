# SPDX-FileCopyrightText: 2024 Adaptation for Raspberry Pi 5
# SPDX-License-Identifier: MIT

"""
Raspberry Pi 5 adaptation for MakerMind AS608 fingerprint sensor using the
Adafruit CircuitPython Fingerprint library. This version uses the recommended
libgpiod for GPIO control and proper UART configuration for Pi 5.

Prerequisite installation commands:
    sudo apt update
    sudo apt install gpiod libgpiod-dev
    pip3 install pyserial adafruit-circuitpython-fingerprint
"""

import time
import sys
import gpiod
import serial
import adafruit_fingerprint
from PIL import Image

# UART Configuration for Pi 5
SERIAL_PORT = "/dev/ttyAMA0"  # Primary UART port on Pi 5
BAUD_RATE = 57600

# GPIO Setup using libgpiod
CHIP = "gpiochip0"
LED_PIN = 18  # Example LED pin - adjust as needed


def setup_gpio():
    """Initialize GPIO using libgpiod"""
    try:
        chip = gpiod.Chip(CHIP)
        led_line = chip.get_line(LED_PIN)
        led_line.request(consumer="fingerprint", type=gpiod.LINE_REQ_DIR_OUT)
        return chip, led_line
    except Exception as e:
        print(f"GPIO Setup Error: {str(e)}")
        sys.exit(1)


def setup_uart():
    """Initialize UART communication for Pi 5"""
    try:
        uart = serial.Serial(
            port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=1, write_timeout=1
        )
        return uart
    except Exception as e:
        print(f"UART Setup Error: {str(e)}")
        sys.exit(1)


def get_fingerprint(finger):
    """Get a finger print image, template it, and see if it matches!"""
    print("Waiting for image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass

    print("Templating...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        return False

    print("Searching...")
    if finger.finger_search() != adafruit_fingerprint.OK:
        return False
    return True


def enroll_finger(finger, location):
    """Take a 2 finger images and template it, then store in 'location'"""
    for fingerimg in range(1, 3):
        if fingerimg == 1:
            print("Place finger on sensor...", end="")
        else:
            print("Place same finger again...", end="")

        while True:
            i = finger.get_image()
            if i == adafruit_fingerprint.OK:
                print("Image taken")
                break
            if i == adafruit_fingerprint.NOFINGER:
                print(".", end="", flush=True)
            elif i == adafruit_fingerprint.IMAGEFAIL:
                print("Imaging error")
                return False
            else:
                print("Other error")
                return False

        print("Templating...", end="")
        i = finger.image_2_tz(fingerimg)
        if i == adafruit_fingerprint.OK:
            print("Templated")
        else:
            if i == adafruit_fingerprint.IMAGEMESS:
                print("Image too messy")
            elif i == adafruit_fingerprint.FEATUREFAIL:
                print("Could not identify features")
            elif i == adafruit_fingerprint.INVALIDIMAGE:
                print("Image invalid")
            else:
                print("Other error")
            return False

        if fingerimg == 1:
            print("Remove finger")
            time.sleep(1)
            while i != adafruit_fingerprint.NOFINGER:
                i = finger.get_image()

    print("Creating model...", end="")
    i = finger.create_model()
    if i == adafruit_fingerprint.OK:
        print("Created")
    else:
        if i == adafruit_fingerprint.ENROLLMISMATCH:
            print("Prints did not match")
        else:
            print("Other error")
        return False

    print(f"Storing model #{location}...", end="")
    i = finger.store_model(location)
    if i == adafruit_fingerprint.OK:
        print("Stored")
    else:
        if i == adafruit_fingerprint.BADLOCATION:
            print("Bad storage location")
        elif i == adafruit_fingerprint.FLASHERR:
            print("Flash storage error")
        else:
            print("Other error")
        return False

    return True


def main():
    """Main program loop"""
    # Setup GPIO and UART
    chip, led_line = setup_gpio()
    uart = setup_uart()

    # Initialize fingerprint sensor
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

    # Verify sensor connection
    if finger.verify_password() != adafruit_fingerprint.OK:
        print("Did not find fingerprint sensor :(")
        sys.exit(1)

    print("Fingerprint sensor found!")

    while True:
        print("\n")
        print("----------------")
        if finger.read_templates() != adafruit_fingerprint.OK:
            raise RuntimeError("Failed to read templates")
        print("Fingerprint templates:", finger.templates)
        print("e) enroll print")
        print("f) find print")
        print("d) delete print")
        print("q) quit")
        print("----------------")

        c = input("> ").lower()

        if c == "e":
            # Turn on LED during enrollment
            led_line.set_value(1)
            location = int(input("Enter ID # (1-127): "))
            if location > 0 and location < 128:
                enroll_finger(finger, location)
            led_line.set_value(0)

        elif c == "f":
            # Turn on LED during search
            led_line.set_value(1)
            if get_fingerprint(finger):
                print("Found #", finger.finger_id, "with confidence", finger.confidence)
            else:
                print("Finger not found")
            led_line.set_value(0)

        elif c == "d":
            location = int(input("Enter ID # to delete (1-127): "))
            if location > 0 and location < 128:
                if finger.delete_model(location) == adafruit_fingerprint.OK:
                    print("Deleted!")
                else:
                    print("Failed to delete")

        elif c == "q":
            print("Exiting...")
            # Cleanup
            led_line.set_value(0)
            chip.close()
            uart.close()
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
