import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


PATH = f"/home/{os.getlogin()}/TiktokAutoUploader"


class YouTubeConnector:
    """
    A class to connect to the YouTube API and retrieve videos from a channel.
    """

    def __init__(self, ytb_channel_id) -> None:
        # If modifying these scopes, delete the file token.pickle.
        self.SCOPES = ['https://www.googleapis.com/auth/youtube']
        self.WishYouBest_id = ytb_channel_id
        self.service = self.connect_youtube()

    def connect_youtube(self) -> object:
        """
        Connects to the YouTube API.
        :return: The YouTube API service object.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(PATH + "/creds/token_youtube.json"):
            creds = Credentials.from_authorized_user_file(
                        PATH + "/creds/token_youtube.json", self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    PATH + "/creds/credentials.json", self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(PATH + "/creds/token_youtube.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build('youtube','v3', credentials=creds)
        except Exception as e:
            print(f"An error occurred: {e}")
            service = None
        return service

    def get_videos(self, param:list = []) -> list:
        """
        Lists the videos in the YouTube channel by iterating all pages.
        :return: The list of videos in the channel.
        """
        if param != []:
            return param
        titles = []
        urls = []
        next_page_token = None
        while True:
            request = self.service.search().list(
                part="snippet",
                channelId=self.WishYouBest_id,
                maxResults=50,
                pageToken=next_page_token,
                order="date"
            )
            response = request.execute()
            for item in response["items"]:
                if item["id"]["kind"] == "youtube#video":
                    urls.append(
                        f"http://www.youtube.com/shorts/{item['id']['videoId']}")
                titles.append(item["snippet"]["title"])
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        titles.remove("Best Cities all Around World")
        titles.remove("WishYouBest")
        # remove if includes "Amazing Places, Foods, Hotels and More in"
        remove_list = []
        for idx in range(len(titles)):
            if "Amazing Places, Foods, Hotels and More in" in titles[idx]:
                remove_list.append(idx)
        for idx in reversed(remove_list):
            titles.pop(idx)
            urls.pop(idx)
        r = []
        for url, title in zip(urls, titles):
            r.insert(0, (url, title))
        return r


class TikTokScraper:
    """
    A class to scrape video titles from a TikTok user's profile page.
    """

    def __init__(self, username: str) -> None:
        self.url = f"https://www.tiktok.com/@{username}"
        self.driver = None
        self.wait = None

    def setup_driver(self) -> None:
        # Set up the Selenium WebDriver with custom options (user-agent, etc.)
        options = webdriver.ChromeOptions()
        agents = [
            "Mozilla/5.0",
            "(Windows NT 10.0; Win64; x64)",
            "AppleWebKit/537.36",
            "(KHTML, like Gecko)",
            "Chrome/91.0.4472.124",
            "Safari/537.36"
        ]
        options.add_argument(f"user-agent={' '.join(agents)}")
        # Initialize the Chrome WebDriver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # Use stealth to bypass bot detection by making the browser appear more like a regular user
        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        
        # Open the target TikTok page
        self.driver.get(self.url)
        # Maximize the window to ensure all elements are visible
        self.wait = WebDriverWait(self.driver, 20)
    
    def scroll_page(self):
        """Scrolls the page to load more content."""
        scroll_pause_time = 2  # Pause time between scrolls (adjustable)
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight")
        
        while True:
            # Scroll down to the bottom of the page
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)  # Wait for the content to load
            
            # Calculate new scroll height and compare with the last scroll height
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight")
            if new_height == last_height:  # No more content to load
                break
            last_height = new_height

    def extract_titles(self):
        """Extracts video titles from the TikTok page."""
        try:
            # Wait for the presence of div elements with the class 'css-41hm0z'
            div_blocks = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'css-41hm0z')))
            
            alt_texts = []  # List to store the video titles or alt text
            for div in div_blocks:
                try:
                    # Wait for the img tag inside each div and extract the alt text
                    img = WebDriverWait(div, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'img')))
                    alt_texts.append(img.get_attribute('alt'))
                except Exception as e:
                    print(f"Error processing div: {e}")
            
            return alt_texts  # Return the list of alt texts (video titles or descriptions)

        except Exception as e:
            print(f"Error finding video elements: {e}")
            return []

    def close_driver(self):
        """Closes the Selenium WebDriver instance."""
        if self.driver:
            self.driver.quit()

    def scrape_titles(self):
        """Main function to execute the scraping."""
        # Initialize and configure the WebDriver
        self.setup_driver()
        # Scroll the page to load content
        self.scroll_page()
        # Extract video titles
        titles = self.extract_titles()
        # Close the browser
        self.close_driver()
        
        return titles

    def get_titles(self):
        """Returns titles after postprocessing."""
        titles = self.scrape_titles()
        # remove after "FULL VIDEO:YouTube:WishYouBestt"
        for idx in range(len(titles)):
            if "FULL VIDEO:YouTube:WishYouBestt" in titles[idx]:
                titles[idx] = titles[idx].split(
                                "FULL VIDEO:YouTube:WishYouBestt")[0]
                titles[idx] += "FULL VIDEO:YouTube:WishYouBestt"
        return titles


class UploadOneShort:
    """
    A class to upload one YouTube short to TikTok.
    It selects the oldest YouTube short that is not in the TikTok account.
    Uploads the selected YouTube short to the TikTok account.
    """

    def __init__(self, tiktok_user_name: str, ytb_channel_id: str,
                  wait_time_in_hours: int, repeat_count: int) -> None:
        self.wait_time_in_hours = wait_time_in_hours
        self.repeat_count = repeat_count
        self.tiktok_user_name = tiktok_user_name
        self.youtube_titles_sorted_by_upload_date = []
        self.tiktok_titles = []
        self.ytb_con = YouTubeConnector(ytb_channel_id)
        self.tiktok_scraper = TikTokScraper(tiktok_user_name)

    @staticmethod
    def convert_title(title: str) -> str:
        # remove every none character from title and add # to every word    
        filtered_title = ''.join(e for e in title if e.isalnum() or e.isspace())
        title = '#' + ' #'.join(filtered_title.split()) + ' FULL VIDEO:YouTube:WishYouBestt'
        return title

    def add_hashtags(self, title: str) -> str:
        title += " #Adventure #AdventureAwaits #AdventureSeeker #AmazingPlaces"
        title += " #BestEats #BoutiqueHotels #BucketListDestinations"
        title += " #CulinaryJourney #DreamDestinations #EpicJourneys #ExoticEats"
        title += " #Explore #ExploreTheWorld #FoodExplorer #FoodieFinds"
        title += " #GlobalCuisine #HiddenGems #HotelLife #HotelLuxury"
        title += " #InspiringPlaces #LuxuryHotels #LuxuryTravel #MustVisitPlaces"
        title += " #SpectacularViews #Travel #TravelDiaries #TravelEnthusiast"
        title += " #TravelGoals #TravelInspiration #TravelVibes #UnforgettableExperiences"
        title += " #VacationDreams #VacationGoals #Wanderlust #WorldWonders #hi #world"
        return title

    def select_youtube_short(self) -> tuple:
        self.youtube_titles_sorted_by_upload_date = self.ytb_con.get_videos(self.youtube_titles_sorted_by_upload_date)
        #print(self.youtube_titles_sorted_by_upload_date)
        selection_list = [(url, self.convert_title(title)) for url, title in self.youtube_titles_sorted_by_upload_date]
        if self.tiktok_titles == []:
            self.tiktok_titles = self.tiktok_scraper.get_titles()

        # select the oldest youtube short that is not in tiktok_titles
        for url, title in selection_list:
           if title not in self.tiktok_titles:
                title = self.add_hashtags(title)
                # find index of url in self.youtube_titles_sorted_by_upload_date
                idx = 0
                for i, (u, t) in enumerate(self.youtube_titles_sorted_by_upload_date):
                    if u == url:
                        idx = i
                        break
                # remove the selected title from the list
                self.youtube_titles_sorted_by_upload_date.pop(idx)
                self.tiktok_titles.append(title)
                return url, title
        raise Exception("No new youtube short found")

    def upload_one_short(self, param:list = []) -> None:
        if param != []:
            self.youtube_titles_sorted_by_upload_date = param
        url, title = self.select_youtube_short()
        print(url, title)
        command = f"/home/alperenlcr/py_env/bin/python3.10 cli.py upload --user wishyouubest -yt \"{url}\" -t \"{title}\""
        os.system(command)
        print("Uploaded")
        time.sleep(self.wait_time_in_hours * 3600)
        if self.repeat_count > 0:
            self.repeat_count -= 1
            self.upload_one_short()


if __name__ == "__main__":
    wait_time_in_hours = 1
    repeat_count = 6
    tiktok_user_name = "wishyouubest"
    ytb_channel_id = "UCnoEfubD-FvugKnhCTEVXGQ"
    uploader = UploadOneShort(tiktok_user_name, ytb_channel_id,
                              wait_time_in_hours, repeat_count)
    uploader.upload_one_short()
