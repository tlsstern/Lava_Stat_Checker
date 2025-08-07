#!/usr/bin/env python3
"""
BedWars Stats Comparison Tool Launcher
Choose between Supabase (cloud) or local cache files
"""

import os
import sys

class C:
    """ANSI Color Codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'

def print_banner():
    """Prints a welcome banner."""
    print(f"{C.BOLD}{C.HEADER}╔{'═' * 52}╗{C.ENDC}")
    print(f"{C.BOLD}{C.HEADER}║ 📊 BedWars Stats Comparison Tool 📊              ║{C.ENDC}")
    print(f"{C.BOLD}{C.HEADER}╚{'═' * 52}╝{C.ENDC}")

def main():
    print_banner()
    print(f"\n{C.BOLD}{C.YELLOW}Choose data source:{C.ENDC}")
    print(f"  {C.CYAN}1{C.ENDC}) Supabase (Cloud) - View historical stats from database")
    print(f"  {C.CYAN}2{C.ENDC}) Local Cache Files - Compare JSON cache files")
    print(f"  {C.CYAN}3{C.ENDC}) Exit")
    
    while True:
        try:
            choice = input(f"\n{C.YELLOW}Enter your choice (1-3): {C.ENDC}")
            
            if choice == '1':
                # Import and run Supabase version
                try:
                    from compare_supabase import main as supabase_main
                    supabase_main()
                except ImportError as e:
                    print(f"{C.RED}Error: Could not import Supabase comparison tool.{C.ENDC}")
                    print(f"{C.RED}Make sure compare_supabase.py exists and dependencies are installed.{C.ENDC}")
                    print(f"{C.RED}Error details: {e}{C.ENDC}")
                except Exception as e:
                    print(f"{C.RED}Error running Supabase comparison: {e}{C.ENDC}")
                break
                
            elif choice == '2':
                # Import and run local cache version
                try:
                    # Add cache folder to path if needed
                    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
                    if cache_dir not in sys.path:
                        sys.path.insert(0, cache_dir)
                    
                    # Change to cache directory for file operations
                    original_dir = os.getcwd()
                    os.chdir(cache_dir)
                    
                    from compare import main as cache_main
                    cache_main()
                    
                    # Restore original directory
                    os.chdir(original_dir)
                except ImportError as e:
                    print(f"{C.RED}Error: Could not import cache comparison tool.{C.ENDC}")
                    print(f"{C.RED}Make sure cache/compare.py exists.{C.ENDC}")
                    print(f"{C.RED}Error details: {e}{C.ENDC}")
                except Exception as e:
                    print(f"{C.RED}Error running cache comparison: {e}{C.ENDC}")
                break
                
            elif choice == '3':
                print(f"{C.GREEN}Goodbye!{C.ENDC}")
                break
                
            else:
                print(f"{C.RED}Invalid choice. Please enter 1, 2, or 3.{C.ENDC}")
                
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}Exiting...{C.ENDC}")
            break
        except Exception as e:
            print(f"{C.RED}Unexpected error: {e}{C.ENDC}")
            break

if __name__ == "__main__":
    main()