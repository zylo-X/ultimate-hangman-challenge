"""
Hangman Game
===========

A feature-rich implementation of the classic Hangman word-guessing game with
a console-based interface, sound effects, and persistent leaderboard.

Features:
- Multiple difficulty levels (Normal, Hard, Custom categories)
- Sound effects using pygame
- Persistent leaderboard with filtering by game mode
- Hint system for gameplay assistance
- ASCII art and colorful interface
- Cross-platform file handling

Author: ZyloX Studios (Reorganized and documented)
"""

# Standard library imports
import os
import sys
import time
import random
import pickle

# Third-party imports
import pygame
import appdirs
from termcolor import colored, cprint
from pyfiglet import figlet_format


###############################################################################
# File Path and Resource Management Utilities
###############################################################################

def get_data_directory():
    """
    Get a platform-specific directory for storing game data files.
    """
    if getattr(sys, 'frozen', False):
        # When frozen, keep data files next to the executable
        app_data_dir = os.path.dirname(sys.executable)
    else:
        # Running in a normal Python environment
        app_name = "HangmanGame"
        app_data_dir = appdirs.user_data_dir(app_name, "ZyloXStudios")
    
    # Create directory if it doesn't exist
    if not os.path.exists(app_data_dir):
        try:
            os.makedirs(app_data_dir)
            print(f"Created data directory: {app_data_dir}")
        except Exception as e:
            print(f"Failed to create data directory: {e}")
    
    return app_data_dir

def resource_path(relative_path):
    """
    Get absolute path to resource, works for development and PyInstaller.
    
    Handles file paths for read-only resources like word lists and sounds.
    
    Args:
        relative_path (str): Relative path to the resource
        
    Returns:
        str: Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
        
    # Handle data directory paths for read-only files
    if not relative_path.startswith("data/") and (
        relative_path.endswith(".txt") or 
        relative_path.endswith(".wav") or
        relative_path.endswith(".mp3") or
        relative_path.endswith(".ogg")):
        # Automatically prepend "data/" if needed
        relative_path = os.path.join("data", relative_path)
    
    return os.path.join(base_path, relative_path)


def get_save_file_path(filename):
    """
    Get the proper path for files that need to be saved/modified.
    
    Places them in the user's data directory rather than the application directory.
    
    Args:
        filename (str): Name of the file
        
    Returns:
        str: Absolute path to the save file location
    """
    # Get the data directory
    data_dir = get_data_directory()
    
    # Return the full path to the save file
    return os.path.join(data_dir, filename)


###############################################################################
# Sound Management Class
###############################################################################

class SoundManager:
    """
    Handles all game sounds using pygame mixer.
    
    Loads and plays sound effects for different game events like
    correct/incorrect guesses, hints, wins, and game over.
    """
    
    def __init__(self):
        """
        Initialize the sound system and load sound effects.
        
        Handles errors gracefully if sound initialization fails.
        """
        try:
            pygame.mixer.init()
            self.sound_enabled = True
            
            # Load all sound effects with descriptive names
            self.sounds = {
                "correct": pygame.mixer.Sound(resource_path("correct.ogg")),
                "incorrect": pygame.mixer.Sound(resource_path("incorrect.wav")),
                "hint": pygame.mixer.Sound(resource_path("hint.wav")),
                "win": pygame.mixer.Sound(resource_path("win.ogg")),
                "game_over": pygame.mixer.Sound(resource_path("gameover.ogg")),
                "menu_select": pygame.mixer.Sound(resource_path("menu_select.ogg"))
            }
            
            # Set volume levels (0.0 to 1.0)
            for sound in self.sounds.values():
                sound.set_volume(0.7)
            
        except Exception as e:
            print(f"Sound initialization failed: {e}")
            self.sound_enabled = False
    
    def play(self, sound_name):
        """
        Play a sound effect by name.
        
        Args:
            sound_name (str): The name of the sound to play
        """
        if not self.sound_enabled:
            return
            
        try:
            if sound_name in self.sounds:
                self.sounds[sound_name].play()
        except Exception as e:
            print(f"Error playing sound '{sound_name}': {e}")
    
    def stop_all(self):
        """
        Stop all currently playing sounds.
        
        Useful when transitioning between game states.
        """
        if not self.sound_enabled:
            return
            
        try:
            pygame.mixer.stop()
        except Exception:
            pass


###############################################################################
# Main Hangman Game Class
###############################################################################

class HangmanGame:
    """
    Main class for the Hangman game implementation.
    
    Handles game logic, user interface, file operations, and game flow.
    Provides multiple difficulty levels, custom word categories,
    and a persistent leaderboard system.
    """
    
    # ASCII art for hangman stages, showing progressive drawing of the hangman
    HANGMANPICS = ['''
  +---+
  |   |
      |
      |
      |
      |
=========''', '''
  +---+
  |   | 
  O   |
      |
      |
      |
=========''', '''
  +---+
  |   |
  O   |
  |   |
      |
      |
=========''', '''
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========''', '''
  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========''', '''
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========''', '''
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
=========''']

    #-------------------------------------------------------------------------
    # Initialization Methods
    #-------------------------------------------------------------------------
    
    def __init__(self):
        """
        Initialize the game with default values and setup.
        
        Sets up game state variables, loads word lists, and initializes sound.
        """
        # Game state variables
        self.level = 0
        self.global_score = 0
        self.level_score = 0
        self.hints = 1
        self.mode = "Unknown"
        self.first_time = True
        
        # Try to optimize display for better experience
        self.attempt_fullscreen()
        
        # Load word lists for different difficulty levels
        self.easy_words = self.load_word_list("Easywords.txt")
        self.hard_words = self.load_word_list("Hardwords.txt")

        # Initialize sound system
        self.sound_manager = SoundManager()
    
    def attempt_fullscreen(self):
        """
        Set the terminal to exclusive fullscreen mode using the keyboard library.
        
        Simulates pressing F11 to trigger fullscreen mode for a better gaming experience.
        Falls back gracefully if the operation fails.
        """
        try:
            import keyboard
            keyboard.press('f11')
            # Brief pause to allow the fullscreen transition to complete
            import time
            time.sleep(0.5)
            self.clear_screen()  # Clear screen to utilize the new display area
        except Exception as e:
            # Fallback if keyboard library fails
            print("For the best experience, press F11 to enter fullscreen mode.")
            time.sleep(2)
    
    #-------------------------------------------------------------------------
    # File Operations and Data Persistence Methods
    #-------------------------------------------------------------------------
    
    def load_word_list(self, filename):
        """
        Load word list from a file with error handling.
        
        Args:
            filename (str): Name of the word list file
            
        Returns:
            list: List of words loaded from the file, or default words if file not found
        """
        try:
            full_path = resource_path(filename)
            
            with open(full_path, 'r') as file:
                words = [line.strip().lower() for line in file if line.strip()]
                
            return words
        except FileNotFoundError:
            # Provide default words for each category
            print(f"Warning: {filename} not found. Using default words.")
            if filename == "Easywords.txt":
                return ["python", "hangman", "game", "computer", "programming", 
                        "simple", "basic", "easy", "word", "guess"]
            elif filename == "Hardwords.txt":
                return ["xylophone", "jazz", "pneumonia", "oxygen", "acquisition",
                       "cryptography", "philosophy", "psychology", "rhythm", "syndrome"]
            elif filename == "Animals.txt":
                return ["dog", "cat", "elephant", "tiger", "zebra", "lion", "giraffe", "monkey"]
            elif filename == "Countries.txt":
                return ["france", "germany", "italy", "japan", "brazil", "canada", "india"]
            elif filename == "Movies.txt":
                return ["avatar", "titanic", "jaws", "alien", "matrix", "frozen"]
            elif filename == "Mixed.txt":
                return ["apple", "house", "river", "music", "window", "doctor", "summer"]
            else:
                return ["hangman", "python", "game", "words", "guess"]
    
    def load_scores_pickle(self):
        """
        Load scores from pickle file in user data directory.
        
        Creates a new file if none exists.
        
        Returns:
            list: List of score entries with player name, score, and mode
        """
        try:
            # Get the proper path for the high scores file
            save_path = get_save_file_path("high_scores.pkl")
        
            # Log the path being used
            print(f"Loading scores from: {save_path}")
        
            # Load the scores
            with open(save_path, "rb") as file:
                return pickle.load(file)
        except (FileNotFoundError, EOFError):
            print("No existing scores file found. Creating a new one.")
            # Create an empty file
            self.save_score_pickle("DefaultPlayer", 0)
            return []  # Return an empty list if the file doesn't exist or is corrupt
    
    def save_score_pickle(self, player_name, player_score):
        """
        Save score to the pickle file with category information.
        
        Args:
            player_name (str): Name of the player
            player_score (int): Score to save
        """
        # Load existing scores
        scores = self.load_scores_pickle()

        # Create the score entry with more detailed mode info
        score_entry = {
            "name": player_name,
            "score": player_score,
            "mode": self.mode
        }

        scores.append(score_entry)

        # Get the proper save path
        save_path = get_save_file_path("high_scores.pkl")
    
        # Log the save operation
        print(f"Saving score for {player_name} ({player_score} points) to: {save_path}")
    
        try:
            # Save the scores
            with open(save_path, "wb") as file:
                pickle.dump(scores, file)
            print("Score saved successfully!")
        except Exception as e:
            print(f"Error saving score: {e}")
    
    def clear_leaderboard(self):
        """
        Clear the leaderboard with user confirmation.
        
        Completely resets the high scores file after confirmation.
        """
        os.system('cls' if os.name == 'nt' else 'clear')
        cprint("⚠️ WARNING: This will reset the leaderboard and delete all scores!", "red", attrs=["bold"])
        confirm = input("Are you sure you want to clear the leaderboard? (yes/no): ").strip().lower()
        if confirm == "yes":
            # Get the proper save path
            save_path = get_save_file_path("high_scores.pkl")
        
            with open(save_path, "wb") as file:
                pickle.dump([], file)  # Overwrite with an empty list
            cprint("Leaderboard has been cleared successfully!", "green", attrs=["bold"])
        else:
            cprint("Leaderboard reset canceled.", "yellow", attrs=["bold"])
        input("Press Enter to return to the main menu...")
        os.system('cls' if os.name == 'nt' else 'clear')
    
    #-------------------------------------------------------------------------
    # Sound Effect Methods
    #-------------------------------------------------------------------------
    
    def sfx_correct(self):
        """Play sound for correct letter guess."""
        self.sound_manager.play("correct")
    
    def sfx_incorrect(self):
        """Play sound for incorrect letter guess."""
        self.sound_manager.play("incorrect")
    
    def sfx_hint(self):
        """Play sound for using a hint."""
        self.sound_manager.play("hint")
    
    def sfx_win(self):
        """Play sound for winning the game."""
        self.sound_manager.play("win")
    
    def sfx_game_over(self):
        """Play sound for game over."""
        self.sound_manager.play("game_over")

    def menu_select(self):
        """Play sound for menu selection."""
        self.sound_manager.play("menu_select")
    
    #-------------------------------------------------------------------------
    # Display and UI Methods
    #-------------------------------------------------------------------------
    
    def clear_screen(self):
        """Clear the console screen in a cross-platform way."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def loading_screen(self):
        """
        Display initial loading screen with studio branding.
        
        Creates a visual introduction to the game with animated effects.
        """
        print("\n" * 6)
        cprint(figlet_format('    ZYLO_ X', font='starwars'), 'white', 'on_black', attrs=['blink'])
        cprint(figlet_format('STUDIOS', font='slant'), 'light_green', 'on_black', attrs=['blink'])
        print()
        time.sleep(1.5)
        self.clear_screen()

    def ascii_screen(self):
        """
        Display the game's ASCII art intro screen.
        
        Shows the game title and a hangman figure for atmosphere.
        """
        self.clear_screen()
        logo_text = '''                                                



                                        | |                                            
                                        | |__   __ _ _ __   __ _ _ __ ___   __ _ _ __  
                                        | '_ \ / _` | '_ \ / _` | '_ ` _ \ / _` | '_ \ 
                                        | | | | (_| | | | | (_| | | | | | | (_| | | | |
                                        |_| |_|\__,_|_| |_|\__, |_| |_| |_|\__,_|_| |_|
                                                            __/ |                      
                                                            |___/                       
                                                                   

'''
        logo_art = '''

                                                            +---+
                                                            |   |
                                                            O   |
                                                           /|\  |
                                                           / \  |
                                                                |
                                                         =========

                                                                 '''
        cprint(logo_text, "red")
        cprint(logo_art, "white")
        time.sleep(1.5)
        self.clear_screen()
    
    def strip_color_codes(self, text):
        """
        Remove ANSI color codes from text for proper length calculations.
        
        Args:
            text (str): Text with color codes
            
        Returns:
            str: Text without color codes
        """
        import re
        return re.sub(r'\x1b\[\d+m', '', text)
    
    def display_game_state(self, hidden_word, attempts_left, guessed_letters, wrong_guesses):
        """
        Display current game state with enhanced visuals.
        
        Shows the hangman figure, word progress, guessed letters, and game statistics
        in a visually appealing format with appropriate colors.
        
        Args:
            hidden_word (str): Current state of the word with some letters hidden
            attempts_left (int): Number of remaining incorrect guesses allowed
            guessed_letters (set): Set of letters that have been guessed
            wrong_guesses (int): Count of incorrect guesses
        """
        self.clear_screen()
        
        # Create a decorative border based on difficulty mode
        if self.mode == "Normal":
            border_color = "green"
            mode_display = "🟢 Normal MODE"
        elif self.mode == "Hard":
            border_color = "red"
            mode_display = "🔴 HARD MODE"
        else:
            border_color = "yellow"
            mode_display = "🟡 Custom-Game"       
        border = "═" * 70
        
        # Game header with level and difficulty information
        cprint(border, border_color)
        cprint(f"  LEVEL: {self.level+1}  |  {mode_display}  |  HINTS: {self.hints}", border_color, attrs=["bold"])
        cprint(border, border_color)
        
        # Create two-column layout for better space usage
        left_column = []
        right_column = []
        
        # Add hangman ASCII art to left column with appropriate coloring
        hangman_lines = self.HANGMANPICS[wrong_guesses].splitlines()
        danger_level = ["white", "green", "green", "yellow", "yellow", "red", "red"]
        hangman_color = danger_level[wrong_guesses] if wrong_guesses < len(danger_level) else "red"
        
        # Format hangman with color based on danger level
        for line in hangman_lines:
            left_column.append(colored(line, hangman_color))
        
        # Fill in remaining lines to align with right column
        while len(left_column) < 8:
            left_column.append("")
        
        # Create scoreboard for right column
        right_column.append(colored("📊 GAME STATS:", "cyan", attrs=["bold"]))
        right_column.append(colored("┌─────────────────────────────┐", "white"))
        right_column.append(colored(f"│ 🎮 Level Score: {self.level_score:<12}│", "light_cyan"))
        right_column.append(colored(f"│ 🏆 Total Score: {self.global_score:<12}│", "light_green"))
        right_column.append(colored(f"│ ❌ Wrong Guesses: {wrong_guesses:<10}│", hangman_color))
        right_column.append(colored(f"│ 🛡️ Attempts Left: {attempts_left:<10}│", "yellow"))
        right_column.append(colored("└─────────────────────────────┘", "white"))
        
        # Display the two columns side by side
        for idx in range(max(len(left_column), len(right_column))):
            left = left_column[idx] if idx < len(left_column) else ""
            right = right_column[idx] if idx < len(right_column) else ""
            
            # Calculate padding to align columns
            padding = " " * (40 - len(self.strip_color_codes(left)))
            print(f"{left}{padding}{right}")
        
        # Display word progress with letter spacing and visual enhancement
        cprint("\n WORD TO GUESS:", "cyan", attrs=["bold"])
        
        # Format the hidden word with spacing and highlighting
        formatted_word = ""
        for letter in hidden_word:
            if letter == "-":
                formatted_word += colored("_ ", "white")
            else:
                formatted_word += colored(f"{letter}  ", "yellow", attrs=["bold"])
        
        cprint(f"  {formatted_word}", "white")
        
        # Display guessed letters in a visually appealing way
        cprint("\n LETTERS TRIED:", "cyan", attrs=["bold"])
        
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        for idx, letter in enumerate(alphabet):
            # Create a new line every 9 letters for better formatting
            if idx % 9 == 0 and idx > 0:
                print()
                
            # Color and format based on guess status
            if letter in guessed_letters:
                if letter in hidden_word:
                    print(colored(f" {letter.upper()} ", "green", attrs=["bold"]), end="")
                else:
                    print(colored(f" {letter.upper()} ", "red"), end="")
            else:
                print(colored(f" {letter.upper()} ", "white", attrs=["dark"]), end="")
        
        # Game hints and instructions at the bottom
        cprint("\n\n" + border, border_color)
        cprint(" Guess a letter, type the full word, or use 'hint' for help", "white")
        cprint(" Type 'stp' to stop the game at any time", "yellow", attrs=["dark"])
        cprint(border, border_color)
        print()
    
    def display_game_rules(self):
        """
        Display game rules with enhanced visual elements.
        
        Shows comprehensive game information, scoring system, and menu options.
        Handles user navigation through the menu system.
        """
        while True:
            self.clear_screen()
            
            # Title Section with decorative border
            border = "=" * 70
            cprint(border, "cyan")
            cprint(figlet_format("HANGMAN", font="doom"), "red", attrs=["blink"])
            cprint(border, "cyan")
            
            # Welcome message with icon
            cprint("\n🎮  Welcome to the Ultimate Hangman Challenge! 🎮", "cyan", attrs=["bold"])
            
            # Game description
            cprint("\nTest your vocabulary and deduction skills in this classic word-guessing game.", "white")
            cprint("Can you save the hangman before it's too late?", "white")
            
            # Rules Section
            cprint("\n📋 GAME RULES:", "yellow", attrs=["bold"])
            cprint("─" * 60, "yellow")
            
            # Core gameplay rules
            rules = [
                "🎯 A random word will be chosen based on your selected difficulty.",
                "🔤 Guess one letter at a time or try to solve the whole word.",
                "❌ Each incorrect guess adds a piece to the hangman figure.",
                "⏱️ Complete the word before the hangman is fully drawn!",
                "💡 Use 'hint' to reveal a letter (limited hints available)."
            ]
            
            for rule in rules:
                cprint(f"  {rule}", "white")
            
            # Scoring System
            cprint("\n🏆 SCORING SYSTEM:", "green", attrs=["bold"])
            cprint("─" * 60, "green")
            
            scores = [
                "✅ +10 points for each correct letter guessed",
                "❌ -5 points for each incorrect guess (minimum score is 0)",
                "🌟 +20 points bonus for guessing the entire word correctly",
                "🎁 +1 hint for completing a word (accumulates for future games)"
            ]
            
            for score in scores:
                cprint(f"  {score}", "white")
            
            # Difficulty Levels
            cprint("\n🔥 DIFFICULTY LEVELS:", "magenta", attrs=["bold"])
            cprint("─" * 60, "magenta")
            
            difficulties = [
                "🟢 Normal: Common, everyday words",
                "🔴 Hard: More challenging, uncommon words",
                "🟡 Custom: Choose your category"
            ]
            
            for diff in difficulties:
                cprint(f"  {diff}", "white")
            
            # Menu Options
            cprint("\n⚙️ OPTIONS:", "blue", attrs=["bold"])
            cprint("─" * 60, "blue")
            
            cprint("  1. 🎮 Start Game", "green")
            cprint("  2. 🏆 View Leaderboard", "cyan")
            cprint("  3. 🗑️ Clear Leaderboard", "red")
            cprint("  4. ❓ How to Play (Extra Tips)", "yellow")
            cprint("  5. 👋🏻 Exit Game", "white")
            
            cprint("\n" + border, "cyan")
            
            # User input section with error handling
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == "1":
                    self.menu_select()
                    self.clear_screen()
                    return
                    
                elif choice == "2":
                    self.menu_select()
                    self.display_leaderboard()
                    
                elif choice == "3":
                    self.menu_select()
                    self.clear_leaderboard()
                    
                elif choice == "4":
                    self.menu_select()
                    self.display_extra_tips()
                    
                elif choice == "5":
                    self.menu_select()
                    self.clear_screen()
                    cprint("Exiting the game. Goodbye!", "red", attrs=["bold"])
                    time.sleep(1)
                    sys.exit(0)

                else:
                    cprint("\n❌ Invalid input. Please enter a number between 1 and 5.", "red")
                    time.sleep(1)
                    
            except Exception as e:
                cprint(f"\n❌ An error occurred: {e}", "red")
                time.sleep(1)
    
    def display_extra_tips(self):
        """
        Display additional gameplay tips and strategies.
        
        Provides strategic advice on letter frequency, word patterns,
        and hint usage to help players improve their skills.
        """
        self.clear_screen()
        
        # Title with decorative elements
        cprint("🔍 HANGMAN STRATEGIES & TIPS 🔍", "cyan", attrs=["bold", "underline"])
        print("")
        
        # Strategy sections
        cprint("📊 LETTER FREQUENCY STRATEGY:", "yellow", attrs=["bold"])
        cprint("─" * 60, "yellow")
        cprint("  Start with common vowels: E, A, O, I, U", "white")
        cprint("  Then try common consonants: T, N, S, R, H, L, D", "white")
        cprint("  Save rare letters (J, Q, X, Z) for last attempts", "white")
        
        print("")
        cprint("🧩 WORD PATTERN RECOGNITION:", "green", attrs=["bold"])
        cprint("─" * 60, "green")
        cprint("  Look for common prefixes (RE-, UN-, IN-) and suffixes (-ING, -ED, -LY)", "white")
        cprint("  Double letters are common (LL, EE, SS, OO)", "white")
        cprint("  Consonant clusters to watch for: TH, CH, SH, ST, PL", "white")
        
        print("")
        cprint("⚡ HINT USAGE STRATEGY:", "magenta", attrs=["bold"])
        cprint("─" * 60, "magenta")
        cprint("  Save hints for critical moments when you're truly stuck", "white")
        cprint("  Use hints to reveal positions of uncommon letters", "white")
        cprint("  Don't use hints too early - try common letters first", "white")
        
        print("")
        cprint("💭 WORD CATEGORIES TO CONSIDER:", "blue", attrs=["bold"])
        cprint("─" * 60, "blue")
        cprint("  Animals, countries, food, sports, hobbies", "white")
        cprint("  Common phrases and expressions", "white")
        cprint("  Seasonal or holiday-related words", "white")
        
        print("")
        cprint("Press Enter to return to the main menu...", "cyan")
        input()
    
    def display_leaderboard(self, filter_mode=None, show_all=False):
        """
        Display an enhanced leaderboard with filtering options.
        
        Shows player scores with rankings, supports filtering by game mode,
        and displays game statistics.
        
        Args:
            filter_mode (str, optional): Mode to filter scores by
            show_all (bool, optional): Whether to show all scores or just top 10
        """
        self.clear_screen()
    
        # Title and decorative elements
        if filter_mode:
            if filter_mode.startswith("Custom:"):
                category = filter_mode.split(":")[1]
                cprint(figlet_format(f"{category}", font="small"), "cyan", attrs=["bold"])
            elif filter_mode == "Normal":
                cprint(figlet_format("Normal MODE", font="small"), "green", attrs=["bold"])
            else:
                cprint(figlet_format("HARD MODE", font="small"), "red", attrs=["bold"])
        else:
            cprint(figlet_format("HALL OF FAME", font="small"), "cyan", attrs=["bold"])
    
        # Load all scores from the pickle file
        scores = self.load_scores_pickle()
    
        # Initialize sorted_scores as an empty list by default
        sorted_scores = []
    
        if not scores:
            # No scores available
            cprint("\n" + "═" * 60, "yellow")
            cprint("📜 LEADERBOARD EMPTY 📜", "yellow", attrs=["bold", "blink"])
            cprint("═" * 60, "yellow")
            cprint("\nNo champion has claimed their place in history yet!", "white")
            cprint("Be the first to set a high score and immortalize your name!", "white")
        else:
            # Filter scores if a mode is specified
            if filter_mode:
                # For custom categories, we need partial matching
                if filter_mode.startswith("Custom:"):
                    filtered_scores = [s for s in scores if s["mode"].startswith(filter_mode)]
                else:
                    filtered_scores = [s for s in scores if s["mode"] == filter_mode]
                
                if not filtered_scores:
                    cprint(f"\nNo scores found for {filter_mode} mode!", "yellow")
                    cprint("Try playing a game in this mode to be the first champion!", "white")
                
                    # Navigation options
                    cprint("\n" + "═" * 75, "cyan")
                    cprint("OPTIONS:", "cyan", attrs=["bold"])
                    cprint("1. Return to Main Menu", "white")
                    cprint("2. View All Scores", "white")
                    cprint("═" * 75, "cyan")
                
                    choice = input("\nEnter your choice (1-2): ").strip()
                    if choice == "2":
                        return self.display_leaderboard()  # Show all scores
                    else:
                        return  # Return to main menu
            
                sorted_scores = sorted(filtered_scores, key=lambda x: x["score"], reverse=True)
            else:
                # Sort scores in descending order
                sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)
        
            # Calculate statistics
            if filter_mode:
                if filter_mode.startswith("Custom:"):
                    relevant_scores = [s for s in scores if s["mode"].startswith(filter_mode)]
                else:
                    relevant_scores = [s for s in scores if s["mode"] == filter_mode]
                
                if relevant_scores:
                    avg_score = sum(entry["score"] for entry in relevant_scores) / len(relevant_scores)
                    highest_score = max(entry["score"] for entry in relevant_scores)
                else:
                    avg_score = 0
                    highest_score = 0
            else:
                avg_score = sum(entry["score"] for entry in scores) / len(scores)
                highest_score = sorted_scores[0]["score"] if sorted_scores else 0
        
            # Group by different categories for statistics
            easy_scores = [s for s in scores if s["mode"] == "Normal"]
            hard_scores = [s for s in scores if s["mode"] == "Hard"]
        
            # Group custom scores by category
            custom_scores = {}
            for score in scores:
                if score["mode"].startswith("Custom:"):
                    category = score["mode"].split(":")[1]
                    if category not in custom_scores:
                        custom_scores[category] = []
                    custom_scores[category].append(score)
        
            # Display leaderboard header with stats
            cprint("\n" + "═" * 75, "yellow")
            if filter_mode:
                display_mode = filter_mode.split(":")[1] if filter_mode.startswith("Custom:") else filter_mode
                cprint(f"📊 {display_mode.upper()} MODE: {len(relevant_scores)} RECORDS | 🏆 HIGHEST: {highest_score} | 📈 AVERAGE: {avg_score:.1f}", "white")
            else:
                cprint(f"📊 TOTAL RECORDS: {len(scores)} | 🏆 HIGHEST SCORE: {highest_score} | 📈 AVERAGE: {avg_score:.1f}", "white")
            cprint("═" * 75, "yellow")
        
            # Display top player special highlight
            if len(sorted_scores) > 0:
                champion = sorted_scores[0]
                # Format mode name for display
                display_mode = champion['mode']
                if display_mode.startswith("Custom:"):
                    display_mode = f"Custom ({display_mode.split(':')[1]})"
                
                cprint(f"\n👑 REIGNING CHAMPION: {champion['name']} - {champion['score']} points ({display_mode} mode)", 
                       "yellow", attrs=["bold"])
        
            # Main leaderboard table
            if show_all:
                cprint("\n🏅 ALL-TIME CHAMPIONS 🏅", "green", attrs=["bold"])
            else:
                cprint("\n🏅 TOP PLAYERS 🏅", "green", attrs=["bold"])
        
            cprint("┌" + "─" * 5 + "┬" + "─" * 20 + "┬" + "─" * 12 + "┬" + "─" * 25 + "┐", "white")
            cprint("│ RANK│ PLAYER NAME        │ SCORE      │ CATEGORY                │", "white", attrs=["bold"])
            cprint("├" + "─" * 5 + "┼" + "─" * 20 + "┼" + "─" * 12 + "┼" + "─" * 25 + "┤", "white")
        
            # Determine how many scores to display
            display_count = len(sorted_scores) if show_all else min(10, len(sorted_scores))
        
            # Display scores with rank, name, score, and mode
            for idx, entry in enumerate(sorted_scores[:display_count], start=1):
                # Determine row color based on rank
                if idx == 1:
                    row_color = "yellow"  # Gold for 1st place
                elif idx == 2:
                    row_color = "cyan"    # Silver for 2nd place
                elif idx == 3:
                    row_color = "red"     # Bronze for 3rd place
                else:
                    row_color = "white"   # Regular color for other ranks
            
                # Add medal emoji for top 3
                rank_display = f" {idx} "
                if idx == 1:
                    rank_display = " 1🥇"
                elif idx == 2:
                    rank_display = " 2🥈"
                elif idx == 3:
                    rank_display = " 3🥉"
            
                # Format the row with proper spacing
                name_display = entry['name'][:17] + "..." if len(entry['name']) > 17 else entry['name'].ljust(17)
                score_display = f"{entry['score']} pts"
            
                # Format mode display based on mode type
                mode = entry['mode']
                if mode.startswith("Custom:"):
                    category_name = mode.split(":")[1]
                    mode_display = f"🎲 Custom ({category_name})"
                elif mode == "Normal":
                    mode_display = "🟢 Normal"
                else:  # Hard
                    mode_display = "🔴 Hard"
            
                # Truncate if too long
                if len(mode_display) > 23:
                    mode_display = mode_display[:20] + "..."
            
                # Print the formatted row
                cprint(f"│{rank_display} │ {name_display}  │ {score_display.ljust(10)} │ {mode_display.ljust(23)}│", 
                       row_color)
        
            # Show a message if there are more scores not displayed
            if not show_all and len(sorted_scores) > 10:
                cprint("├" + "─" * 5 + "┼" + "─" * 20 + "┼" + "─" * 12 + "┼" + "─" * 25 + "┤", "white")
                cprint(f"│     │ ... and {len(sorted_scores) - 10} more players ...                              │", "white")
        
            cprint("└" + "─" * 5 + "┴" + "─" * 20 + "┴" + "─" * 12 + "┴" + "─" * 25 + "┘", "white")
        
            # Display mode-specific statistics (only on main view)
            if not filter_mode:
                # Standard modes
                if easy_scores:
                    easy_avg = sum(entry["score"] for entry in easy_scores) / len(easy_scores)
                    easy_best = max(entry["score"] for entry in easy_scores)
                    cprint(f"\n🟢 Normal Mode Stats: Avg: {easy_avg:.1f} | Best: {easy_best} | Players: {len(easy_scores)}", "green")
            
                if hard_scores:
                    hard_avg = sum(entry["score"] for entry in hard_scores) / len(hard_scores)
                    hard_best = max(entry["score"] for entry in hard_scores)
                    cprint(f"🔴 Hard Mode Stats: Avg: {hard_avg:.1f} | Best: {hard_best} | Players: {len(hard_scores)}", "red")
            
                # Add custom category stats
                for category, cat_scores in custom_scores.items():
                    if cat_scores:
                        cat_avg = sum(entry["score"] for entry in cat_scores) / len(cat_scores)
                        cat_best = max(entry["score"] for entry in cat_scores)
                        cprint(f"🎲 Custom ({category}) Stats: Avg: {cat_avg:.1f} | Best: {cat_best} | Players: {len(cat_scores)}", "cyan")
    
        # Create filter options based on available modes
        filter_options = []
        if scores:
            modes = set()
            custom_categories = set()
        
            # Collect all available modes
            for score in scores:
                mode = score["mode"]
                if mode.startswith("Custom:"):
                    custom_categories.add(mode.split(":")[1])
                else:
                    modes.add(mode)
        
            # Add standard modes
            if "Normal" in modes:
                filter_options.append(("Normal", "green"))
            if "Hard" in modes:
                filter_options.append(("Hard", "red"))
        
            # Add custom categories
            for category in sorted(custom_categories):
                filter_options.append((f"Custom:{category}", "cyan"))
    
        # Navigation options - always displayed regardless of empty scores
        cprint("\n" + "═" * 75, "cyan")
        cprint("OPTIONS:", "cyan", attrs=["bold"])
        cprint("1. Return to Main Menu", "white")
    
        # Only show these options if there are scores to display
        option_num = 2
        if len(sorted_scores) > 0:
            if not show_all and len(sorted_scores) > 10:
                cprint(f"{option_num}. View All-Time Hall of Fame", "white")
                option_num += 1
            elif show_all:
                cprint(f"{option_num}. View Top 10 Only", "white")
                option_num += 1
        
            if not filter_mode:
                # Display filter options based on available data
                for i, (mode, color) in enumerate(filter_options, start=option_num):
                    display_text = mode
                    if mode.startswith("Custom:"):
                        display_text = f"Filter by Custom: {mode.split(':')[1]}"
                    else:
                        display_text = f"Filter by {mode} Mode"
                    
                    cprint(f"{i}. {display_text}", color)
                option_num = option_num + len(filter_options)
            else:
                cprint(f"{option_num}. Show All Categories", "white")
                option_num += 1
    
        cprint("═" * 75, "cyan")
    
        # Handle user selection
        try:
            choice = input("\nEnter your choice: ").strip()
        
            # Process choice
            if choice == "1":
                # Return to main menu
                self.clear_screen()
                return
            
            # Only process other options if there are scores
            if len(sorted_scores) > 0:
                if choice == "2":
                    if not show_all and len(sorted_scores) > 10:
                        # Toggle between all scores and top 10
                        self.display_leaderboard(filter_mode, not show_all)
                    elif show_all:
                        # Toggle back to top 10
                        self.display_leaderboard(filter_mode, False)
                    elif filter_mode:
                        # Show all categories
                        self.display_leaderboard(None, show_all)
                    elif len(filter_options) > 0:
                        # Apply first filter
                        self.display_leaderboard(filter_options[0][0], show_all)
                elif not filter_mode:
                    # Check if it's a filter option
                    choice_idx = int(choice) - option_num + len(filter_options)
                    if 0 <= choice_idx < len(filter_options):
                        filter_mode = filter_options[choice_idx][0]
                        self.display_leaderboard(filter_mode, show_all)
                elif choice == "3" and filter_mode:
                    # Show all categories
                    self.display_leaderboard(None, show_all)
        except Exception as e:
            cprint(f"\nAn error occurred: {e}", "red")
            time.sleep(2)
            self.clear_screen()
    
    def check_game_status(self, hidden_word, word_to_guess, attempts_left, wrong_guesses, one_time_guess=False):
        """
        Check if the game has been won or lost and display appropriate screen.
        
        Args:
            hidden_word (str): Current state of the word with some letters hidden
            word_to_guess (str): The complete word to guess
            attempts_left (int): Number of remaining incorrect guesses allowed
            wrong_guesses (int): Count of incorrect guesses
            one_time_guess (bool, optional): Whether the player guessed the whole word in one go
            
        Returns:
            str: Game status ("win", "lose", or "continue")
        """
        if hidden_word == word_to_guess:
            # VICTORY SCREEN
            self.clear_screen()
            self.sfx_win()
            
            # Display victory ASCII art and animations
            victory_art = r"""
                .-=========-.
               \\'-=======-'/
                _|   .=.   |_
               ((|  {{1}}  |))
                \|   /|\   |/
                 \__ '`' __/
                   _`) (`_
                 _/_______\_
                /___________\
            """
            
            # Simulate confetti animation
            for _ in range(3):
                self.clear_screen()
                cprint(victory_art.replace("{{1}}", "\\o/"), "green")
                cprint("\n" + "🎊 " * 20, "yellow")
                time.sleep(0.3)
                
                self.clear_screen()
                cprint(victory_art.replace("{{1}}", " o "), "green")
                cprint("\n" + " 🎉 " * 20, "cyan")
                time.sleep(0.3)
            
            # Final victory screen
            self.clear_screen()
            
            # Trophy and confetti
            cprint(figlet_format("VICTORY!", font="stop"), "yellow", attrs=["bold"])
            
            border = "★" * 70
            cprint(border, "yellow")
            cprint(f"  🏆 Congratulations! You guessed the word correctly! 🏆", "green", attrs=["bold"])
            cprint(f"  ✨ The word was: {word_to_guess} ✨", "cyan", attrs=["bold"])
            
            # Show bonus information
            if one_time_guess:
                cprint("\n  🌟 PERFECT GUESS BONUS: +50 POINTS! 🌟", "yellow", attrs=["bold"])
            
            cprint(f"\n  You earned {self.level_score} points in this level", "white", attrs=["bold"])
            cprint(f"  Your total score is now {self.global_score+self.level_score}", "green", attrs=["bold"])
            cprint(f"  You've received +1 hint for the next level!", "cyan")
            
            cprint(border, "yellow")
            time.sleep(2)
            return "win"
            
        elif attempts_left == 0:
            # DEFEAT SCREEN
            self.clear_screen()
            self.sfx_game_over()
            
            # Display full hangman figure
            print(self.HANGMANPICS[wrong_guesses])
            
            # Game over title with flickering effect
            for _ in range(3):
                self.clear_screen()
                cprint(figlet_format("GAME OVER", font="doom"), "red", attrs=["bold"])
                time.sleep(0.3)
                self.clear_screen()
                cprint(figlet_format("GAME OVER", font="doom"), "dark_grey", attrs=["bold"])
                time.sleep(0.3)
            
            self.clear_screen()
            
            # Dramatic defeat display
            cprint(figlet_format("GAME OVER", font="doom"), "red", attrs=["bold"])
            
            # Hangman with red color for impact
            cprint(self.HANGMANPICS[6], "red")
            
            border = "☠️ " * 25
            cprint(border, "red")
            cprint(f"The word was: {word_to_guess}", "white", attrs=["bold"])
            cprint(f"Final score: {self.global_score}", "yellow", attrs=["bold"])
            cprint(border, "red")
            
            # Add a dramatic quote
            defeat_quotes = [
                "Even the best wordsmith faces defeat sometimes...",
                "The gallows claim another victim. Better luck next time!",
                "The man hangs, but your spirit lives to play another day.",
                "Words can be tricky beasts. This one got the better of you.",
                "The hangman claims victory this time..."
            ]
            cprint(f"\n\"{random.choice(defeat_quotes)}\"", "cyan", attrs=["bold"])
            
            time.sleep(2)
            return "lose"
            
        return "continue"

    #-------------------------------------------------------------------------
    # Difficulty and Game Settings Methods
    #-------------------------------------------------------------------------
    
    def select_difficulty(self):
        """
        Present an enhanced difficulty selection menu with custom play option.
        
        Returns:
            list: The appropriate word list based on player's choice
        """
        while True:
            self.clear_screen()
        
            # Title with decorative border
            border = "=" * 60
            cprint(border, "yellow")
            cprint("🎯  DIFFICULTY SELECTION  🎯", "yellow", attrs=["bold"])
            cprint(border, "yellow")
        
            # Description of difficulty impact
            cprint("\nYour choice will determine your path to victory!", "white")
            cprint("Choose wisely, brave wordsmith...", "white")
        
            # Option boxes with visual elements
            cprint("\n┌" + "─" * 56 + "┐", "green")
            cprint("│  1. 🟢 Normal MODE                                     │", "green")
            cprint("│     • Common, everyday words                           │", "green")
            cprint("│     • More forgiving gameplay +3 Hints                 │", "green")
            cprint("│     • Perfect for casual players or beginners          │", "green")
            cprint("└" + "─" * 56 + "┘", "green")
        
            cprint("\n┌" + "─" * 56 + "┐", "red")
            cprint("│  2. 🔴 HARD MODE                                       │", "red")
            cprint("│     • Uncommon and challenging words                   │", "red")
            cprint("│     • Test your vocabulary limits                      │", "red")
            cprint("│     • For experienced players seeking a challenge      │", "red")
            cprint("└" + "─" * 56 + "┘", "red")
        
            cprint("\n┌" + "─" * 56 + "┐", "cyan")
            cprint("│  3. 🎲 CUSTOM PLAY                                     │", "cyan")
            cprint("│     • Choose specific word categories                  │", "cyan")
            cprint("│     • Adjust difficulty to your preferences            │", "cyan")
            cprint("│     • Specialized gameplay experience                  │", "cyan")
            cprint("└" + "─" * 56 + "┘", "cyan")
        
            # Prompt for input with custom styling
            cprint("\n" + border, "yellow")
            difficulty = input("\nEnter your choice (1/2/3): ").strip().lower()
        
            # Sound effect and visual feedback based on selection
            if difficulty in ['easy', '1']:
                cprint("\n🎮 Normal mode selected! Good luck!", "green", attrs=["bold"])
                self.mode = "Normal"
                self.hints = 3
                self.menu_select()
                time.sleep(1)
                return self.easy_words
                
            elif difficulty in ['hard', '2']:
                cprint("\n🔥 Hard mode selected! Brave choice!", "red", attrs=["bold"])
                self.mode = "Hard"
                self.hints = 1
                self.menu_select()
                time.sleep(1)
                return self.hard_words
                
            elif difficulty in ['custom', '3']:
                self.mode = "Custom-Game"
                self.hints = 2
                self.menu_select()
                return self.select_word_category()
                
            else:
                cprint("\n❌ Invalid input! Please select 1, 2, or 3.", "red")
                self.sfx_incorrect()
                time.sleep(1)
    
    def select_word_category(self):
        """
        Allows players to choose from different word categories.
        
        Returns:
            list: The selected word list based on category
        """
        # Define available categories with their icons and file names
        categories = {
            "1": {"name": "Animals", "icon": "🐾", "file": "Animals.txt", "color": "green"},
            "2": {"name": "Countries", "icon": "🌎", "file": "Countries.txt", "color": "blue"},
            "3": {"name": "Movies", "icon": "🎬", "file": "Movies.txt", "color": "magenta"},
            "4": {"name": "Mixed", "icon": "🎲", "file": "Mixed.txt", "color": "yellow"}
        }
    
        while True:
            self.clear_screen()
        
            # Title section
            cprint(figlet_format("CATEGORY", font="small"), "cyan", attrs=["bold"])
            cprint("Select a category of words to play with:", "white")
        
            # Display each category with custom styling
            for key, category in categories.items():
                category_color = category["color"]
                cprint(f"\n {key}. {category['icon']} {category['name']}", category_color, attrs=["bold"])
            
                # Show stats about this category if available
                try:
                    word_count = len(self.load_word_list(category["file"]))
                    cprint(f"    • {word_count} words available", category_color)
                
                    # Calculate and display difficulty rating
                    if word_count > 0:
                        avg_length = self.calculate_avg_word_length(category["file"])
                        difficulty_rating = self.calculate_difficulty_rating(avg_length, word_count)
                        cprint(f"    • Difficulty: {difficulty_rating}/5", category_color)
                except:
                    cprint(f"    • File not loaded", "red")
        
            # Bottom border
            cprint("\n" + "=" * 60, "cyan")
        
            # Prompt for selection
            choice = input("\nEnter your category choice (1-4) or 'b' to go back: ").strip().lower()
        
            # Handle back option
            if choice == 'b':
                return self.select_difficulty()
        
            # Process category selection
            if choice in categories:
                selected = categories[choice]
                try:
                    word_list = self.load_word_list(selected["file"])
                    if not word_list:
                        cprint(f"\nError: No words found in {selected['name']} category!", "red")
                        time.sleep(1.5)
                        continue
                
                    cprint(f"\n{selected['icon']} {selected['name']} category selected!", selected["color"], attrs=["bold"])
                    self.mode = f"Custom:{selected['name']}"
                    time.sleep(1)
                    return word_list
                except Exception as e:
                    cprint(f"\nError loading word list: {e}", "red")
                    time.sleep(1.5)
                    continue
            else:
                cprint("Invalid choice! Please select a number between 1 and 4.", "red")
                time.sleep(1)             

    #-------------------------------------------------------------------------
    # Game Logic Methods
    #-------------------------------------------------------------------------
    
    def update_hidden_word(self, word_to_guess, hidden_word, guessed_letter):
        """
        Reveals all occurrences of a correctly guessed letter in the hidden word.
    
        Args:
            word_to_guess (str): The complete word to guess
            hidden_word (str): Current state of the word with some letters revealed
            guessed_letter (str): The letter that was guessed
    
        Returns:
            str: Updated hidden word with all instances of the guessed letter revealed
        """
        # Create a new string to store the updated hidden word
        new_hidden_word = ""
    
        # Replace all occurrences of the guessed letter in the hidden word
        for i in range(len(word_to_guess)):
            if word_to_guess[i] == guessed_letter:
                # Reveal this occurrence of the letter
                new_hidden_word += guessed_letter
            else:
                # Keep the current state of this position (revealed or hidden)
                new_hidden_word += hidden_word[i]
    
        return new_hidden_word
    
    def get_hint(self, word_to_guess, hidden_word):
        """
        Provide a hint by revealing one unrevealed letter.
        
        All occurrences of the chosen letter will be revealed.
    
        Args:
            word_to_guess (str): The complete word to guess
            hidden_word (str): Current state of the word with some letters revealed
    
        Returns:
            tuple: (updated_hidden_word, revealed_letter) - Updated hidden word with the
                  hinted letter revealed in all positions, and the letter that was revealed
        """
        if self.hints <= 0:
            cprint("No hints left!", "red")
            return hidden_word, None
    
        # Find all letter positions that are still hidden
        hidden_positions = [i for i, char in enumerate(hidden_word) if char == "-"]

        if not hidden_positions:
            cprint("All letters are already revealed!", "yellow")
            return hidden_word, None
    
        # Choose a random position to reveal
        position = random.choice(hidden_positions)

        # Get the letter at that position
        hint_letter = word_to_guess[position]

        # Reveal all occurrences of this letter
        new_hidden_word = self.update_hidden_word(word_to_guess, hidden_word, hint_letter)

        self.sfx_hint()
        cprint(f"Hint used! Letter '{hint_letter}' revealed.", "cyan")
        self.hints -= 1

        return new_hidden_word, hint_letter
    
    def play_game(self):
        """
        Main game loop that handles player input and game progression.
        
        Manages complete game flow including level progression, scoring,
        and end-game conditions.
        
        Returns:
            str: Game outcome ("restart", "quit", or "main-menu")
        """
        # Reset scores and initial setup for a new game
        if self.level == 0:
            self.global_score = 0
            
        # Select difficulty and corresponding word list
        word_list = self.select_difficulty()
        
        while True:
            # Initialize round variables
            guessed = 0
            one_time_guess = False
            self.level_score = 0
            
            # Pick a random word
            word_to_guess = random.choice(word_list).lower()
            hidden_word = "-" * len(word_to_guess)
            guessed_letters = set()
            attempts_left = 6
            wrong_guesses = 0
            
            # Main game loop for the current round
            while True:
                # Display current game state
                self.display_game_state(hidden_word, attempts_left, guessed_letters, wrong_guesses)
                
                # Get player input
                player_guess = input("Enter a letter, the full word, or type 'hint': ").lower()
                
                # Handle stop game command
                if player_guess == "stp":
                    self.clear_screen()
                    print("")
                    if self.global_score > 0:
                        player_name = input("Enter your name to save your score: ")
                        self.save_score_pickle(player_name, self.global_score)
                        print("")
                        cprint("Your score has been saved!", "green", attrs=["bold"])
                        print("")
                    self.clear_screen()
                    self.display_game_rules()
                    return "main-menu"
                
                # Handle hint request
                if player_guess == "hint":
                    if self.hints > 0:
                        # Get an updated hidden word with one letter revealed
                        old_hidden_word = hidden_word
                        hidden_word, revealed_letter = self.get_hint(word_to_guess, hidden_word)

                        # Check if hint was actually used (hint count would have been decremented)
                        if hidden_word != old_hidden_word and revealed_letter:
                            # Add the revealed letter to guessed_letters so it shows up in the alphabet panel
                            guessed_letters.add(revealed_letter)
                            guessed += 1
            
                            # Check if the word is fully revealed after hint
                            if hidden_word == word_to_guess:
                                self.level_score += 10  # Add points for the revealed letter
                                self.global_score += self.level_score
                                self.level += 1
                                self.hints += 1  # Add one hint for completing the word
        
                                # Show win screen
                                self.check_game_status(hidden_word, word_to_guess, attempts_left, wrong_guesses)
                                time.sleep(2)
                                break  # Exit to next level
                    else:
                        cprint("No hints left!", "red")
                        self.sfx_incorrect()

                    time.sleep(1)
                    continue          
                
                # Validate input for a single letter guess
                if len(player_guess) == 1 and player_guess.isalpha():
                    if player_guess in guessed_letters:
                        cprint("You already guessed that letter. Try again!", "red")
                        time.sleep(1)
                        continue  # Ask for input again without penalty
                    
                    guessed_letters.add(player_guess)
                    
                    if player_guess in word_to_guess:
                        hidden_word = self.update_hidden_word(word_to_guess, hidden_word, player_guess)
                        self.sfx_correct()
                        guessed += 1
                        self.level_score += 10  # Add points for correct guess
                    else:
                        self.sfx_incorrect()
                        cprint("Incorrect guess!", "red")
                        wrong_guesses += 1
                        attempts_left -= 1
                        self.level_score = max(0, self.level_score - 5)  # Deduct points, minimum 0
                        time.sleep(1)
                
                # Allow full word guesses
                elif len(player_guess) > 1 and player_guess.isalpha():
                    if player_guess == word_to_guess:
                        hidden_word = word_to_guess
                        if guessed <= 1:
                            one_time_guess = True
                            self.level_score += 50  # Bonus for guessing the whole word early
                        else:
                            self.level_score += 20  # Regular bonus for guessing the full word
                        self.sfx_correct()
                    else:
                        self.sfx_incorrect()
                        cprint("Incorrect word guess!", "red")
                        wrong_guesses += 1
                        attempts_left -= 1
                        self.level_score = max(0, self.level_score - 5)  # Deduct points, minimum 0
                        time.sleep(1)
                else:
                    cprint("Invalid input. Please guess a single letter, the full word, or type 'hint'.", "red")
                    time.sleep(1)
                    continue
                
                # Check game status after each guess
                status = self.check_game_status(hidden_word, word_to_guess, attempts_left, wrong_guesses, one_time_guess)
                
                if status in ("win", "lose"):
                    if status == "win":
                        print("")
                        if one_time_guess:
                            cprint("You got +50 Bonus 🎁", 'light_yellow')
                        print("")
                        self.global_score += self.level_score
                        cprint(f"Your score in this level: {self.level_score}", "white", attrs=["bold"])
                        print("")
                        cprint(f"Your Total Score: {self.global_score}", "yellow", attrs=["bold"])
                        self.level += 1
                        self.hints += 1  # Add hint for winning
                        time.sleep(2)
                        break  # Move to next level
                        
                    elif status == "lose":
                        cprint(f"Your final score: {self.global_score}", "red", attrs=["bold"])
                        self.level = 0  # Reset level
                        print("")
                        
                        if self.global_score > 0:
                            player_name = input("Enter your name to save your score: ")
                            self.save_score_pickle(player_name, self.global_score)
                            cprint("Your score has been saved!", "green", attrs=["bold"])
                            time.sleep(1.5)
                            self.clear_screen()

                        cprint("1- Start new game ", "green", attrs=["bold"])
                        cprint("2- Main-Menu", "yellow", attrs=["bold"])
                        cprint("3- Exit ", "red", attrs=["bold"])        
                        cprint("=================================", "white", attrs=["bold"])     
                        play_again = input("").strip().lower()

                        if play_again == "1":
                            return "restart"  # new game
                        elif play_again == "3":
                            print("")
                            cprint("Thanks for playing! Goodbye!", "red")
                            return "quit"  # Exit game
                        else:
                            cprint("Main-Menu Loading .....", "green")
                            return "main-menu"  # main-menu 
            
            # End of current level, continue to next level
            continue

    #-------------------------------------------------------------------------
    # Helper/Utility Methods
    #-------------------------------------------------------------------------
    
    def calculate_avg_word_length(self, filename):
        """
        Calculate the average word length in a word list file.
        
        Args:
            filename (str): Name of the word list file
            
        Returns:
            float: Average word length
        """
        words = self.load_word_list(filename)
        if not words:
            return 0
        return sum(len(word) for word in words) / len(words)

    def calculate_difficulty_rating(self, avg_length, word_count):
        """
        Calculate a difficulty rating (1-5) based on average word length and count.
        
        Longer words and smaller word pools generally mean higher difficulty.
        
        Args:
            avg_length (float): Average word length
            word_count (int): Number of words in the list
            
        Returns:
            str: Difficulty rating displayed as stars (e.g., "★★★☆☆")
        """
        # Base difficulty on average word length
        if avg_length < 4:
            length_score = 1
        elif avg_length < 5:
            length_score = 2
        elif avg_length < 6:
            length_score = 3
        elif avg_length < 8:
            length_score = 4
        else:
            length_score = 5
    
        # Adjust for word pool size (smaller pools can be harder due to obscurity)
        if word_count > 500:
            count_adj = -1
        elif word_count > 200:
            count_adj = 0
        elif word_count > 100:
            count_adj = 1
        else:
            count_adj = 2
    
        # Calculate final rating (1-5 range)
        rating = max(1, min(5, length_score + count_adj))
    
        # Convert to stars
        return "★" * rating + "☆" * (5 - rating)
    
    #-------------------------------------------------------------------------
    # Main Entry Point
    #-------------------------------------------------------------------------
    
    def run(self):
        """
        Main entry point to start the game.
        
        Initializes game environment and manages the overall game flow.
        """
        # Initialize high scores file if it doesn't exist
        if not os.path.exists(get_save_file_path("high_scores.pkl")):
            with open(get_save_file_path("high_scores.pkl"), "wb") as file:
                pickle.dump([], file)
                
        # Show intro screens on first run
        if self.first_time:
            self.loading_screen()
            self.ascii_screen()
            self.first_time = False
            self.display_game_rules()
        
        # Main game loop
        while True:
            result = self.play_game()
            
            if result == "quit":    
                break
            elif result == "restart":
                self.sound_manager.stop_all()
                continue
            else:  # main-menu
                self.sound_manager.stop_all()
                self.display_game_rules()


###############################################################################
# Main Execution Block
###############################################################################

if __name__ == "__main__":
    game = HangmanGame()
    game.run()