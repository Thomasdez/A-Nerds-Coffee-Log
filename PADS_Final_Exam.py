import time
import json
import os
import threading


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
    Tracks and displays total elapsed time and current pour time.
    Users can press Enter to log a pour and type 'done' to finish.
    The timer continuously updates without interfering with input.
    """

    print("\nStarting the brew timer. Press Enter to record a pour or type 'd' to finish.")
    print("Total elapsed time and current pour time will be displayed.\n")

    pours = []  # List to store elapsed times for pours
    start_time = time.time()
    last_pour_time = start_time
    stop_timer = False

    def display_timer():
        """Continuously display the total elapsed time."""
        while not stop_timer:
            total_elapsed = int(time.time() - start_time)
            pour_elapsed = int(time.time() - last_pour_time)
            print(f"\rTotal elapsed time: {total_elapsed} seconds | Current pour time: {pour_elapsed} seconds", end="    ", flush=True)
            time.sleep(1)

    # Start the timer display thread
    timer_thread = threading.Thread(target=display_timer)
    timer_thread.daemon = True
    timer_thread.start()

    # Input loop to log pours or finish
    # For future development this loop should be improved. However, i am out of time, and this makes the program run so i will stick to it
    while True:
        print()  # Move input below timer display
        user_input = input("Press Enter to log a pour or type 'd' to finish: ").strip().lower()
        if user_input == "":
            pour_elapsed = int(time.time() - last_pour_time)
            pours.append(pour_elapsed)
            last_pour_time = time.time()
            print(f"Pour recorded: {pour_elapsed} seconds.")
        elif user_input == "d":
            break

    # Stop the timer
    stop_timer = True
    timer_thread.join()

    # Log the final pour
    final_pour_elapsed = int(time.time() - last_pour_time)
    pours.append(final_pour_elapsed)

    total_brewing_time = int(time.time() - start_time)
    print("\nBrewing session completed.")
    print(f"Total brewing time: {total_brewing_time} seconds")
    print("Pour timings:", pours)
    return pours


#Main function that runs the script
def main():
    storage = DataStorage()
    print("Welcome to A Nerd's Coffee Log!")

    while True:
        print("\nMenu:")
        print("1. Brew a new coffee")
        print("2. View all stored data")
        print("3. Search for a coffee by producer and name")
        print("4. Ranking")
        print("5. Exit")
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

            # Give a small prompt and wait before asking for the weights
            print("\nNow you will be asked to enter the weight of water for each recorded pour.")
            input("Please enter the weight of water for each pour")

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
            # Ranking
            print("\nWhat ranking would you like to see?")
            print("1. Producers")
            print("2. Coffee Bean Names")
            print("3. Countries")
            print("4. Production Methods")
            rank_choice = input("Enter your choice: ").strip()

            # Prepare data structures to hold sums and counts
            category_sums = {}
            category_counts = {}

            # Depending on the user's choice, we'll pick the attribute from coffee beans
            attr = None
            if rank_choice == "1":
                attr = "producer"
            elif rank_choice == "2":
                attr = "name"
            elif rank_choice == "3":
                attr = "country"
            elif rank_choice == "4":
                attr = "method"
            else:
                print("Invalid choice. Returning to main menu.")
                continue

            # Compute sums and counts of ratings by the chosen category
            for key, coffee_bean in storage.coffees.items():
                # Get attribute value
                category_value = getattr(coffee_bean, attr, None)
                if category_value is None:
                    continue

                # Collect all ratings from brew sessions
                for brew in coffee_bean.brew_sessions:
                    if category_value not in category_sums:
                        category_sums[category_value] = 0
                        category_counts[category_value] = 0
                    category_sums[category_value] += brew.rating
                    category_counts[category_value] += 1

            # Compute averages
            averages = []
            for cat_val, total in category_sums.items():
                count = category_counts[cat_val]
                if count > 0:
                    avg = total / count
                    averages.append((cat_val, avg))

            # Sort by average descending
            averages.sort(key=lambda x: x[1], reverse=True)

            # Display results with numbering
            if not averages:
                print("No brew sessions recorded, or no data available for this category.")
            else:
                print(f"\nRanking by {attr.capitalize()}:")
                for i, (cat_val, avg) in enumerate(averages, start=1):
                    print(f"{i}. {cat_val}: {avg:.2f}")

        elif choice == "5":
            print("Goodbye! Enjoy your coffee!")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
