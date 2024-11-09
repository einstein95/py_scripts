import random


def new_serial_number():
    return random.randint(1000000, 10000000)


def calculate_registration_number(serial_number) -> int:
    return (serial_number % 199999) + 44


serial = new_serial_number()
regcode = calculate_registration_number(serial)

print(f"Serial Number: {serial}\nRegistration Code: {regcode}")
with open("data.nsd", "w", encoding="utf-8") as f:
    f.write(f"[#mySerialNumber: {serial}, #myRegistrationNumber: \"{regcode}\"]\r")
