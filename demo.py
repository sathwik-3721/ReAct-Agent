import wikipediaapi
import requests
import urllib3
import time

# Suppress warnings for cleaner output
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_wikipedia_content(page_title, retries=3, delay=2):
    """
    Fetch Wikipedia content with retry mechanism and improved error handling.
    
    Args:
        page_title (str): Title of the Wikipedia page
        retries (int): Number of retry attempts
        delay (int): Delay between retries in seconds
        
    Returns:
        str: Page summary or error message
    """
    # Modern user agent that mimics Google Chrome browser
    user_agent = "ReAct Agents (sathwik3721@gmail.com)"
    
    for attempt in range(retries):
        try:
            # Create a fresh session for each attempt
            session = requests.Session()
            session.headers.update({"User-Agent": user_agent})
            session.timeout = 20  # Increased timeout
            
            # Create Wikipedia API instance
            wiki = wikipediaapi.Wikipedia(
                user_agent=user_agent,
                language="en"
            )
            wiki._session = session
            
            # Fetch the page
            page = wiki.page(page_title)
            
            # Check if the page exists
            if page.exists():
                print(f"Success on attempt {attempt + 1}")
                return page.summary
            else:
                return f"Page '{page_title}' not found on Wikipedia"
                
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                return f"Failed after {retries} attempts: Connection error"
                
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                return f"Failed after {retries} attempts: {str(e)}"

if __name__ == "__main__":
    # Try to fetch the Wikipedia page
    result = get_wikipedia_content("FIFA World Cup")
    
    # Print the summary or error message
    print("\nResult:")
    print(result)
