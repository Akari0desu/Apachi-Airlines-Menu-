# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 20:24:33 2025

@author: computershop.mn
"""
#importing useful functions

import random
import sqlite3
import string
#creating a class to make it easier for usage
class SeatBookingSystem:
    # meal options for the customer
    MEAL_OPTIONS = [
        "Standard Meal",
        "Vegetarian", 
        "No Meal Preferred"
    ]

#starting the system 
    def __init__(self):
        """Initialize the seating system with proper Burak757 layout"""
        self.seats = self.create_seat_map()
        self.initialize_database()
        #verification step to ensure all seats were created properly
        expected_seats = 80 * 6 - 6  # 80 rows × 6 columns - 6 storage seats
        if len(self.seats) != expected_seats:
            print(f"Warning: Seat map initialization issue - expected {expected_seats} seats, got {len(self.seats)}")
    
    #function to show the main map of the plane
    def create_seat_map(self):
        """Create seat map matching Burak757 layout"""
        seat_map = {}
        
        #create all seats first (rows 1-80, columns A-F)
        for row in range(1, 81):
            for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat = f"{row}{col}"
                # Mark storage areas as "S"
                if row in [77, 78] and col in ['D', 'E', 'F']:
                    seat_map[seat] = 'S'
                else:
                    seat_map[seat] = 'F'  # Default to free
        
        return seat_map
    
    #creating the database
    def initialize_database(self):
        """Ensure database has correct structure with all 6 columns"""
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        
        #check if table exists and has correct columns
        c.execute("PRAGMA table_info(bookings)")
        columns = c.fetchall()
        
        #if table doesn't exist or is missing columns, recreate it
        if not columns or len(columns) != 6:
            c.execute("DROP TABLE IF EXISTS bookings")
            c.execute('''CREATE TABLE bookings (
                            seat TEXT PRIMARY KEY, 
                            reference TEXT, 
                            first_name TEXT, 
                            last_name TEXT, 
                            passport TEXT,
                            meal_preference TEXT)''')
            print("Database initialized with correct structure")
        
        #loading existing bookings into memory for faster access
        c.execute("SELECT seat, reference FROM bookings")
        for seat, ref in c.fetchall():
            self.seats[seat] = ref  # Store reference instead of 'R'
        
        conn.commit()
        conn.close()
        
    #function to create a booking reference with random
    def generate_booking_reference(self):
        """Generate random booking reference"""
        #using a loop to ensure we get a unique reference
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        
        while True:
            ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            c.execute("SELECT 1 FROM bookings WHERE reference = ?", (ref,))
            if not c.fetchone():
                conn.close()
                return ref
    
    #seat format validation helper function
    def is_valid_seat_format(self, seat):
        """Validate seat format (number followed by letter A-F)"""
        #detailed validation of seat number components
        if len(seat) < 2:
            return False
        try:
            row = int(seat[:-1])
            col = seat[-1].upper()
            return 1 <= row <= 80 and col in ['A', 'B', 'C', 'D', 'E', 'F']
        except ValueError:
            return False
    
    #function to check for available seats
    def check_availability(self, seat):
        """Check if seat is available"""
        #first validating seat format before checking availability
        if not self.is_valid_seat_format(seat):
            return False, "Invalid seat format (should be like 12A)"
        
        status = self.seats.get(seat)
        if status is None:
            return False, "Invalid seat"
        elif status == 'F':
            return True, "Available"
        elif status == 'S':
            return False, "Storage area"
        elif len(status) == 8:  # Booking reference
            conn = sqlite3.connect("bookings.db")
            c = conn.cursor()
            c.execute("SELECT reference, first_name, last_name FROM bookings WHERE seat = ?", (seat,))
            booking = c.fetchone()
            conn.close()
            if booking:
                return False, f"Booked (Ref: {booking[0]}, Passenger: {booking[1]} {booking[2]})"
            return False, "Invalid booking"
        else:
            return False, "Invalid seat status"
    
    #function to verify booking credentials
    def verify_booking(self, seat, first_name, reference):
        """Verify if provided first name and reference match the booking"""
        #using parameterized queries to prevent SQL injection
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        c.execute("""SELECT 1 FROM bookings 
                  WHERE seat = ? AND first_name = ? AND reference = ?""", 
                  (seat, first_name, reference))
        result = c.fetchone()
        conn.close()
        return result is not None
    
    #function to book a seat 
    def book_seat(self, seat, first_name, last_name, passport):
        """Book a specific seat with meal preference"""
        available, message = self.check_availability(seat)
        if not available:
            print(f"Cannot book seat {seat}: {message}")
            return
        
        #show meal options during booking
        print("\nAvailable Meal Options:")
        for i, option in enumerate(self.MEAL_OPTIONS, 1):
            print(f"{i}. {option}")
        
        #if the customer doesnt choose a meal dont input
        meal_pref = None
        while True:
            choice = input("\nEnter meal choice number (1-3) or press enter to skip: ")
            if not choice:
                break
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(self.MEAL_OPTIONS):
                    meal_pref = self.MEAL_OPTIONS[choice_num-1]
                    break
                #if the costumer enters wrong input
                else:
                    print("Please enter a number between 1 and 3.")
            except ValueError:
                print("Please enter a valid number.")
        
        reference = self.generate_booking_reference()
        self.seats[seat] = reference  # Store reference instead of 'R'
        
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?)",
                     (seat, reference, first_name, last_name, passport, meal_pref))
            conn.commit()
            print(f"\nSeat {seat} booked successfully. Reference: {reference}")
            if meal_pref:
                print(f"Meal preference: {meal_pref}")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.seats[seat] = 'F'  # Revert seat status
        finally:
            conn.close()

    #authenticated seat freeing function
    def authenticated_free_seat(self):
        """Free a booked seat after verifying customer credentials"""
        seat = input("Enter seat number to free (e.g., 12A): ").upper()
        
        #two-step verification - first seat status, then credentials
        if not self.is_valid_seat_format(seat):
            print(f"Invalid seat format: {seat}")
            return
        
        if self.seats.get(seat) == 'F':
            print(f"Seat {seat} is not currently booked.")
            return
        elif seat not in self.seats:
            print(f"Seat {seat} does not exist.")
            return
        
        #get authentication details
        print("\nPlease verify your booking:")
        first_name = input("Enter first name as it appears on booking: ")
        reference = input("Enter booking reference: ").upper()
        
        if not self.verify_booking(seat, first_name, reference):
            print("Authentication failed. The provided details don't match this booking.")
            return
        
        #proceed with freeing seat
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        try:
            c.execute("DELETE FROM bookings WHERE seat = ?", (seat,))
            if c.rowcount > 0:
                self.seats[seat] = 'F'
                print(f"Seat {seat} has been freed.")
            else:
                print("No booking found for this seat.")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    #function to show seats
    def display_seats(self):
        """Display all seats in a compact vertical layout"""
        print("\nApache Airlines Burak757 Seating Plan")
        print("F = Free, [Ref] = Booked (shows first 3 chars), S = Storage, X = Aisle\n")
        
        #group seats by sections
        left_cols = ['A', 'B', 'C']
        right_cols = ['D', 'E', 'F']
        
        #print column headers
        print("Row #  " + "Left Side".center(20) + "│" + "Right Side".center(20))
        print("       " + "─"*20 + "┼" + "─"*20)
        
        #print all 80 rows
        for row in range(1, 81):
            left_side = []
            right_side = []
            
            #left side seats (A-C)
            for col in left_cols:
                seat = f"{row}{col}"
                status = self.seats.get(seat, ' ')
                if status == 'F':
                    left_side.append(f"F-{seat}")
                elif status == 'S':
                    left_side.append(f"  {seat} ")
                else:
                    left_side.append(f"{status[:3]}-{seat}")  # Show first 3 chars of reference
            
            #right side seats (D-F)
            for col in right_cols:
                seat = f"{row}{col}"
                if row in [77, 78] and col in right_cols:
                    right_side.append("  S  ")
                else:
                    status = self.seats.get(seat, ' ')
                    if status == 'F':
                        right_side.append(f"F-{seat}")
                    elif status == 'S':
                        right_side.append(f"  {seat} ")
                    else:
                        right_side.append(f"{status[:3]}-{seat}")  # Show first 3 chars of reference
            
            #aisle separator
            aisle = "   X   " if row <= 76 else "       "
            
            #format the row display
            print(f"{row:3}   " + " ".join(left_side) + "  " + aisle + "  " + " ".join(right_side))

    #authenticated meal change function
    def authenticated_change_meal(self):
        """Change meal preference after verifying customer credentials"""
        seat = input("Enter seat number to update meal (e.g., 12A): ").upper()
        
        if not self.is_valid_seat_format(seat):
            print(f"Invalid seat format: {seat}")
            return
        
        if self.seats.get(seat) == 'F':
            print(f"Seat {seat} is not currently booked.")
            return
        elif seat not in self.seats:
            print(f"Seat {seat} does not exist.")
            return
        
        #get authentication details
        print("\nPlease verify your booking:")
        first_name = input("Enter first name as it appears on booking: ")
        reference = input("Enter booking reference: ").upper()
        
        if not self.verify_booking(seat, first_name, reference):
            print("Authentication failed. The provided details don't match this booking.")
            return
        
        #show meal options
        print("\nAvailable Meal Options:")
        for i, option in enumerate(self.MEAL_OPTIONS, 1):
            print(f"{i}. {option}")
        
        #get new meal preference
        while True:
            choice = input("\nEnter new meal choice number (1-3) or press enter to cancel: ")
            if not choice:
                print("Meal change cancelled.")
                return
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(self.MEAL_OPTIONS):
                    meal_pref = self.MEAL_OPTIONS[choice_num-1]
                    break
                print("Please enter a number between 1 and 3.")
            except ValueError:
                print("Please enter a valid number.")
        
        #update meal preference
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        try:
            c.execute("""UPDATE bookings SET meal_preference = ? 
                      WHERE seat = ? AND reference = ?""", 
                      (meal_pref, seat, reference))
            if c.rowcount > 0:
                print(f"\nMeal preference for seat {seat} updated to: {meal_pref}")
            else:
                print("Failed to update meal preference.")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    #main menu functions 
    def main(self):
        """Main menu interface"""
        while True:
            print("\nApache Airlines Booking Menu!")
            print("1. Check seat availability")
            print("2. Book a seat")
            print("3. Free a seat (requires authentication)")
            print("4. Show seating plan")
            print("5. Change meal preference (requires authentication)")
            print("6. Exit program")
            
            choice = input("Enter your choice (1-6): ")
            
            if choice == '1':
                seat = input("Enter seat number (e.g., 12A): ").upper()
                available, message = self.check_availability(seat)
                print(message)
            elif choice == '2':
                seat = input("Enter seat number to book (e.g., 12A): ").upper()
                first = input("Enter first name: ")
                last = input("Enter last name: ")
                passport = input("Enter passport number: ")
                self.book_seat(seat, first, last, passport)
            elif choice == '3':
                self.authenticated_free_seat()
            elif choice == '4':
                self.display_seats()
            elif choice == '5':
                self.authenticated_change_meal()
            elif choice == '6':
                print("Thank you for using Apache Airlines Booking Menu.")
                break
            else:
                print("Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    system = SeatBookingSystem()
    system.main()