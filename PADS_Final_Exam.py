import time
import json
import os
import threading
import subprocess
import sys

"""
The system uses keyboard shortkeys in the UI. Therfore the following try exceot statement is used
to check id keyboard is installed, and installs thourgh pip if it is not
"""

try:
    import keyboard
except ImportError:
    print("The 'keyboard' module is not installed. Installing it now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "keyboard"])
    import keyboard

class Coffee:
    """
    Base coffee class holding generic coffee information.
    """
    def __init__(self, producer, name, country, method, grind_size):
        self.producer = producer
        self.name = name
        self.country = country
        self.method = method
        self.grind_size = grind_size

class SpecificCoffee(Coffee):
    """
    A subclass of Coffee representing a unique coffee bean identified by producer + name.
    This class also maintains a list of brew sessions for this specific coffee.
    """
    def __init__(self, producer, name, country, method, grind_size):
        super().__init__(producer, name, country, method, grind_size)
        self.brew_sessions = []

    def add_brew_session(self, brew_session):
        self.brew_sessions.append(brew_session)

class BrewSession:
    """
    Represents a single brew of a specific coffee bean.
    """
    def __init__(self):
        self.pour_times = []
        self.notes = ""
        self.rating = 0

    def record_pour(self, weight, pour_time):
        """Record a single pour with integer second timing."""
        self.pour_times.append({"weight": weight, "time": pour_time})

    def complete_brew(self, rating, notes):
        """Finalize the brew session with rating and notes."""
        self.rating = rating
        self.notes = notes

    def to_dict(self):
        """Convert brew session to dictionary for JSON serialization."""
        return {
            "pour_times": self.pour_times,
            "notes": self.notes,
            "rating": self.rating
        }

    @staticmethod
    def from_dict(data):
        """Recreate a BrewSession object from a dictionary."""
        b = BrewSession()
        b.pour_times = data.get("pour_times", [])
        b.notes = data.get("notes", "")
        b.rating = data.get("rating", 0)
        return b

class DataStorage:
    """
    Stores and loads data from JSON.
    Data is stored as a dictionary of coffee beans keyed by a unique string (producer|name).
    Each entry contains coffee details and a list of brew sessions.
    """
    def __init__(self, filename="brewing_data.json"):
        self.filename = filename
        self.coffees = self.load_data()

    def load_data(self):
        if not os.path.exists(self.filename):
            return {}
        try:
            with open(self.filename, "r") as file:
                content = file.read().strip()
                if not content:
                    return {}
                raw_data = json.loads(content)

            # Check if raw_data has the new structure
            if isinstance(raw_data, dict) and "coffee_beans" in raw_data:
                # New structure: Just load it
                return self._load_from_new_structure(raw_data)
            elif isinstance(raw_data, list):
                # Old structure: convert it
                return self._convert_old_data(raw_data)
            else:
                # Unrecognized structure, start fresh
                return {}

        except (json.JSONDecodeError, OSError):
            print(f"Error: {self.filename} contains invalid JSON. Resetting to an empty dictionary.")
            return {}

    def _load_from_new_structure(self, raw_data):
        coffees = {}
        coffee_beans = raw_data.get("coffee_beans", {})
        for key, value in coffee_beans.items():
            coffee_info = value["coffee"]
            sc = SpecificCoffee(
                producer=coffee_info["producer"],
                name=coffee_info["name"],
                country=coffee_info["country"],
                method=coffee_info["method"],
                grind_size=coffee_info["grind_size"]
            )
            # Load brew sessions
            for brew_data in value.get("brews", []):
                session = BrewSession.from_dict(brew_data)
                sc.add_brew_session(session)
            coffees[key] = sc
        return coffees

    def _convert_old_data(self, old_data_list):
        """
        Convert old list-based data structure into the new dictionary-based structure.
        """
        coffees = {}
        for brew in old_data_list:
            coffee_info = brew["coffee"]
            producer = coffee_info["producer"]
            name = coffee_info["name"]
            country = coffee_info.get("country", "")
            method = coffee_info.get("method", "")
            grind_size = coffee_info.get("grind_size", "")

            key = f"{producer.lower()}|{name.lower()}"

            if key not in coffees:
                sc = SpecificCoffee(producer, name, country, method, grind_size)
                coffees[key] = sc
            else:
                sc = coffees[key]

            # Convert brew to BrewSession
            session = BrewSession()
            session.pour_times = brew.get("pour_times", [])
            session.notes = brew.get("notes", "")
            session.rating = brew.get("rating", 0)
            sc.add_brew_session(session)

        return coffees

    def save_data(self):
        data = {"coffee_beans": {}}
        for key, coffee_bean in self.coffees.items():
            bean_data = {
                "coffee": {
                    "producer": coffee_bean.producer,
                    "name": coffee_bean.name,
                    "country": coffee_bean.country,
                    "method": coffee_bean.method,
                    "grind_size": coffee_bean.grind_size
                },
                "brews": [brew.to_dict() for brew in coffee_bean.brew_sessions]
            }
            data["coffee_beans"][key] = bean_data

        with open(self.filename, "w") as file:
            json.dump(data, file, indent=4)

    def get_or_create_coffee(self, producer, name, country, method, grind_size):
        """
        Retrieves a SpecificCoffee object if it exists, otherwise creates a new one.
        Key is a string "producer|name" for case-insensitive matching.
        """
        key = f"{producer.lower()}|{name.lower()}"
        if key not in self.coffees:
            self.coffees[key] = SpecificCoffee(producer, name, country, method, grind_size)
        return self.coffees[key]

    def find_coffee_brews(self, producer, name):
        """Find all brew sessions for a given producer and coffee name."""
        key = f"{producer.lower()}|{name.lower()}"
        return self.coffees.get(key, None)

def brew_timer():
    """
    Tracks and displays real-time total elapsed time since the brewing process started.
    Resets the elapsed time for each pour when the user presses Enter, and logs the time taken for each pour.
    """
    print("\nStarting the brew timer. Total elapsed time and time for each pour will be displayed.")
    print("Press Enter each time you finish a pour. Type 'done' when finished with all pours.")

    pours = []  # List to store the elapsed time for each pour
    start_time = time.time()  # Total brew start time
    last_pour_time = start_time  # Time when the last pour started
    stop_timer = False  # Flag to stop the timer thread

    def display_timer():
        """Continuously display the total elapsed time."""
        while not stop_timer:
            total_elapsed = int(time.time() - start_time)
            pour_elapsed = int(time.time() - last_pour_time)
            print(f"\rTotal elapsed time: {total_elapsed} seconds | Current pour time: {pour_elapsed} seconds", end="", flush=True)
            time.sleep(1)

    # Start the timer thread
    timer_thread = threading.Thread(target=display_timer)
    timer_thread.daemon = True
    timer_thread.start()

    while True:
        user_input = input("\nPress Enter to record a pour or type 'done' if finished: ").strip().lower()
        if user_input == "done":
            break
        pour_elapsed = int(time.time() - last_pour_time)  # Time elapsed since the last pour
        pours.append(pour_elapsed)
        last_pour_time = time.time()  # Reset the last pour time
        print(f"Pour recorded: {pour_elapsed} seconds.")

def brew_timer():
    """
    Tracks and displays real-time total elapsed time since the brewing process started.
    Resets the elapsed time for each pour when the user presses Space, and logs the time taken for each pour.
    Press Enter to finish the brewing process.
    """
    
    print("\nStarting the brew timer. Press Space to record a pour and Enter to finish.")
    print("Total elapsed time and time for each pour will be displayed.")

    pours = []  # List to store the elapsed time for each pour
    start_time = time.time()  # Total brew start time
    last_pour_time = start_time  # Time when the last pour started
    stop_timer = False  # Flag to stop the timer thread
    brewing_done = False  # Flag to indicate when brewing is complete

    def display_timer():
        """Continuously display the total elapsed time."""
        while not stop_timer:
            total_elapsed = int(time.time() - start_time)
            pour_elapsed = int(time.time() - last_pour_time)
            print(f"\rTotal elapsed time: {total_elapsed} seconds | Current pour time: {pour_elapsed} seconds", end="", flush=True)
            time.sleep(1)

    # Start the timer thread
    timer_thread = threading.Thread(target=display_timer)
    timer_thread.daemon = True
    timer_thread.start()

    print("\nPress Space to record a pour or Enter to finish.")
    while not brewing_done:
        if keyboard.is_pressed('space'):
            # Log the elapsed time for the pour
            pour_elapsed = int(time.time() - last_pour_time)
            pours.append(pour_elapsed)
            last_pour_time = time.time()  # Reset the last pour time
            print(f"\nPour recorded: {pour_elapsed} seconds.")
            time.sleep(0.2)  # Prevent multiple detections of the same keypress

        if keyboard.is_pressed('enter'):
            brewing_done = True
            break

    # Stop the timer thread
    stop_timer = True
    timer_thread.join()

    total_brewing_time = int(time.time() - start_time)
    print("\nBrewing session completed.")
    print(f"Total brewing time: {total_brewing_time} seconds")
    print("Pour timings:", pours)
    return pours

def main():
    storage = DataStorage()
    print("Welcome to the Interactive Coffee Brewing Assistant!")

    while True:
        print("\nMenu:")
        print("1. Brew a new coffee")
        print("2. View all stored data")
        print("3. Search for a coffee by producer and name")
        print("4. Exit")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            # Gather coffee details
            producer = input("Enter the producer: ").strip()
            coffee_name = input("Enter the coffee name: ").strip()
            country = input("Enter the country of origin: ").strip()
            method = input("Enter the production method (Washed, Anaerobic, Honey, Natural, etc.): ").strip()
            grind_size = input("Enter the grind size (e.g., Medium, Fine): ").strip()

            coffee_bean = storage.get_or_create_coffee(producer, coffee_name, country, method, grind_size)

            # Start the brew timer and record pours
            session = BrewSession()
            pours = brew_timer()
            for i, pour_time in enumerate(pours, start=1):
                while True:
                    weight_str = input(f"Enter the weight of water for pour {i} (in grams): ").strip()
                    if weight_str.isdigit():
                        weight = int(weight_str)
                        session.record_pour(weight, pour_time)
                        break
                    else:
                        print("Invalid input. Please enter an integer.")

            # Finish the brew
            rating_str = input("Rate the brew (1-100): ").strip()
            while not (rating_str.isdigit() and 1 <= int(rating_str) <= 100):
                print("Invalid rating. Please enter a number between 1 and 100.")
                rating_str = input("Rate the brew (1-100): ").strip()
            rating = int(rating_str)

            notes = input("Write any notes about the brew: ").strip()
            session.complete_brew(rating, notes)
            coffee_bean.add_brew_session(session)

            storage.save_data()
            print("Brew saved successfully!")

        elif choice == "2":
            # View all stored data
            if not storage.coffees:
                print("No brewing data found.")
            else:
                print("\nSaved Brewing Data:")
                for key, coffee_bean in storage.coffees.items():
                    print(f"\nCoffee: {coffee_bean.producer} - {coffee_bean.name}")
                    print(f"  Country: {coffee_bean.country}")
                    print(f"  Method: {coffee_bean.method}")
                    print(f"  Grind Size: {coffee_bean.grind_size}")
                    if not coffee_bean.brew_sessions:
                        print("  No brew sessions recorded yet.")
                    else:
                        for i, brew in enumerate(coffee_bean.brew_sessions, start=1):
                            print(f"\n  Brew {i}:")
                            print(f"    Rating: {brew.rating}/100")
                            print(f"    Notes: {brew.notes}")
                            if brew.pour_times:
                                print("    Pours:")
                                for pour in brew.pour_times:
                                    print(f"      - Weight: {pour['weight']}g, Time: {pour['time']}s")

        elif choice == "3":
            # Search for a coffee by producer and name
            search_producer = input("Enter the producer: ").strip()
            search_name = input("Enter the coffee name: ").strip()

            coffee_bean = storage.find_coffee_brews(search_producer, search_name)
            if coffee_bean is None:
                print("No records found for that coffee.")
            else:
                print(f"\nFound coffee: {coffee_bean.producer} - {coffee_bean.name}")
                print(f"  Country: {coffee_bean.country}")
                print(f"  Method: {coffee_bean.method}")
                print(f"  Grind Size: {coffee_bean.grind_size}")

                if not coffee_bean.brew_sessions:
                    print("  No brew sessions recorded yet.")
                else:
                    for i, brew in enumerate(coffee_bean.brew_sessions, start=1):
                        print(f"\n  Brew {i}:")
                        print(f"    Rating: {brew.rating}/100")
                        print(f"    Notes: {brew.notes}")
                        if brew.pour_times:
                            print("    Pours:")
                            for pour in brew.pour_times:
                                print(f"      - Weight: {pour['weight']}g, Time: {pour['time']}s")

        elif choice == "4":
            print("Goodbye! Enjoy your coffee!")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()