from collections import UserDict, defaultdict
import re
from datetime import datetime
import json

# --- Field classes ---

class Field:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    pass

class Phone(Field):
    def __init__(self, value):
        if not self.validate(value):
            raise ValueError("Phone number must have 10 digits.")
        self.value = value

    def validate(self, value):
        if re.match(r"^\d{10}$", value):
            return True
        return False

class Birthday(Field):
    def __init__(self, value):
        if not self.validate(value):
            raise ValueError("Birthday must be in the format DD.MM.YYYY")
        self.value = datetime.strptime(value, "%d.%m.%Y").date()

    def validate(self, value):
        try:
            datetime.strptime(value, "%d.%m.%Y")
            return True
        except ValueError:
            return False

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")

# --- Record class ---

class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []

    def add_phone(self, phone):
        self.phones.append(Phone(phone))

    def remove_phone(self, phone):
        for p in self.phones:
            if p.value == phone:
                self.phones.remove(p)

    def edit_phone(self, old_phone, new_phone):
        for index, phone in enumerate(self.phones):
            if phone.value == old_phone:
                self.phones[index] = Phone(new_phone)

    def add_birthday(self, birthday):
        self.birthday = Birthday(birthday)

    def get_birthday(self):
        return str(self.birthday) if hasattr(self, "birthday") else "Birthday not set"

    def __str__(self):
        return f"Contact name: {self.name.value}, phones: {'; '.join(p.value for p in self.phones)}"

# --- AddressBook class ---

class AddressBook(UserDict):
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name)

    def get_birthdays_per_week(self):
        users = [{'name': name, 'birthday': record.birthday} for name, record in self.data.items() if hasattr(record, 'birthday')]
        birthdays = defaultdict(list)
        today = datetime.today().date()

        for user in users:
            name = user["name"]
            birthday = user["birthday"].value
            birthday_this_year = birthday.replace(year=today.year)
            
            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            delta_days = (birthday_this_year - today).days

            if delta_days < 7:
                weekday = birthday_this_year.strftime('%A')
                if weekday in ['Saturday', 'Sunday']:
                    weekday = 'Monday'
                birthdays[weekday].append(name)

        return birthdays
    def save_to_disk(self, filename="addressbook.json"):
        with open(filename, "w") as file:
            json_data = {name: {
                            'phones': [phone.value for phone in record.phones],
                            'birthday': str(record.birthday) if hasattr(record, "birthday") else None
                          }
                         for name, record in self.data.items()}
            json.dump(json_data, file, indent=4)

    def load_from_disk(self, filename="addressbook.json"):
        try:
            with open(filename, "r") as file:
                json_data = json.load(file)
                for name, data in json_data.items():
                    record = Record(name)
                    for phone in data['phones']:
                        record.add_phone(phone)
                    if data['birthday']:
                        record.add_birthday(data['birthday'])
                    self.data[name] = record
        except FileNotFoundError:
            pass

# --- Bot functionality ---

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, IndexError) as e:
            return "Give me name and phone please."
        except KeyError:
            return "Contact not found."
        except Exception as e:
            return f"Unexpected error: {e}"
    return inner

@input_error
def hello(*args, book):
    return "How can I help you?"

@input_error
def add(*args, book):
    if len(args) < 2:
        raise ValueError
    username = args[0]
    phone = args[1]
    if username not in book:
        record = Record(username)
        book.add_record(record)
    else:
        record = book.find(username)
    record.add_phone(phone)
    return f"Added {username} with phone number {phone}"

@input_error
def change(*args, book):
    if len(args) < 2:
        raise ValueError
    username = args[0]
    phone = args[1]
    record = book.find(username)
    if not record:
        raise KeyError
    record.edit_phone(record.phones[0].value, phone)
    return f"Changed {username}'s phone number to {phone}"

@input_error
def phone(*args, book):
    if len(args) == 0:
        raise ValueError
    username = args[0]
    record = book.find(username)
    if not record:
        raise KeyError
    return record.phones[0].value

@input_error
def all_contacts(*args, book):
    if not book.data:
        return "No contacts saved"
    return "\n".join([str(record) for record in book.data.values()])

@input_error
def exit_bot(*args, book):
    return "Goodbye!"

@input_error
def add_birthday(*args, book):
    if len(args) < 2:
        raise ValueError
    username = args[0]
    bday = args[1]
    record = book.find(username)
    if not record:
        raise KeyError
    record.add_birthday(bday)
    return f"Added birthday {bday} for {username}"

@input_error
def show_birthday(*args, book):
    if len(args) == 0:
        raise ValueError
    username = args[0]
    record = book.find(username)
    if not record:
        raise KeyError
    return record.get_birthday()

@input_error
def birthdays(*args, book):
    bdays = book.get_birthdays_per_week()
    if not bdays:
        return "No birthdays in the coming week."
    return "\n".join([f"{weekday}: {', '.join(names)}" for weekday, names in bdays.items()])

def pars_command(command):
    parts = command.split(' ')
    first_part = parts[0]
    command_function = COMMANDS.get(first_part)
    if command_function:
        return command_function, parts[1:]
    else:
        return unknown_command, parts

@input_error
def unknown_command(*args, book):
    return f"Unknown command: {args[0]}"

@input_error
def save(*args, book: AddressBook):
    book.save_to_disk()
    return "Address book saved."

@input_error
def load(*args, book: AddressBook):
    book.load_from_disk()
    return "Address book loaded from disk."

COMMANDS = ({
    "hello": hello,
    "add": add,
    "change": change,
    "phone": phone,
    "all": all_contacts,
    "add-birthday": add_birthday,
    "show-birthday": show_birthday,
    "birthdays": birthdays,
    "close": exit_bot,
    "exit": exit_bot,
    "save": save,
    "load": load
})

def main():
    book = AddressBook()
    book.load_from_disk()  # Завантажити дані при запуску
    while True:
        user_input = input("Enter command: ").strip()
        command, data = pars_command(user_input)
        print(command(*data, book=book))

        if command == exit_bot:
            book.save_to_disk()  # Зберегти дані перед виходом
            break

if __name__ == "__main__":
    main()
