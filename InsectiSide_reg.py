import random


def generate_serial_number():
    return random.randint(1000000, 10000000)


def compute_registration_code(serial_number) -> int:
    return (serial_number % 199999) + 44


serial_number = generate_serial_number()
registration_code = compute_registration_code(serial_number)

print(f"Serial Number: {serial_number}\nRegistration Code: {registration_code}")
with open("data.nsd", "w", encoding="macroman") as file:
    file.write(
        f'[#mySerialNumber: {serial_number}, #myRegistrationNumber: "{registration_code}"]\r'
    )
