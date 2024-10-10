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


PATH = f"/home/{os.getlogin()}/TikTok_Uploader"


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
        options.add_argument("--headless")  # Run in headless mode (without a UI)
        options.add_argument("--no-sandbox")  # Disable sandboxing for increased stability
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        options.add_argument("--remote-debugging-port=9222")
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
        command = f"/home/{os.getlogin()}/py_env/bin/python3.10 ~/TikTok_Uploader/cli.py upload --user wishyouubest -yt \"{url}\" -t \"{title}\""
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
    param = [('http://www.youtube.com/shorts/BTJ191jkuyQ', 'New Delhi, India   Jantar Mantar'), ('http://www.youtube.com/shorts/2mbDDzMUHxw', 'New Delhi, India   Paratha'), ('http://www.youtube.com/shorts/MNkV8C4AJ6A', 'Lisbon, Portugal   Altis Avenida Hotel'), ('http://www.youtube.com/shorts/sjhY0nO1Las', 'Lisbon, Portugal   Memmo Alfama Hotel'), ('http://www.youtube.com/shorts/Isrd_mBAops', 'Lisbon, Portugal   Introduction'), ('http://www.youtube.com/shorts/yIdngDjXg1I', 'Copenhagen, Denmark   AC Hotel by Marriott Bella Sky Copenhagen'), ('http://www.youtube.com/shorts/HS7I59kvvk4', 'Copenhagen, Denmark   Public transportation tip2'), ('http://www.youtube.com/shorts/B1KPa2JOIIg', 'Munich, Germany   Sofitel Munich Bayerpost'), ('http://www.youtube.com/shorts/QZ-7bKmGuMo', 'Munich, Germany   Public transportation tip1'), ('http://www.youtube.com/shorts/fUsIwTSBLsY', 'Sydney, Australia   Bondi Beach'), ('http://www.youtube.com/shorts/mKtkF9AEzIg', 'Sydney, Australia   Introduction'), ('http://www.youtube.com/shorts/h12dall1ruI', 'Sydney, Australia   Sydney Harbour Bridge'), ('http://www.youtube.com/shorts/vkVvlDcRVy8', 'Cape Town, South Africa   Cape Malay Curry'), ('http://www.youtube.com/shorts/85d_-JEbSs0', 'Cape Town, South Africa   Mount Nelson Hotel'), ('http://www.youtube.com/shorts/TvyuT9ADXdU', 'Cape Town, South Africa   Robben Island'), ('http://www.youtube.com/shorts/ijNzM-7PJnU', 'Cape Town, South Africa   Castle of Good Hope'), ('http://www.youtube.com/shorts/4U4mlDyJc3o', 'Helsinki, Finland   Summary'), ('http://www.youtube.com/shorts/Ax4lugAh3zg', 'Helsinki, Finland   Public transportation tip4'), ('http://www.youtube.com/shorts/kRBwv1VImC4', 'Helsinki, Finland   Hotel Fabian'), ('http://www.youtube.com/shorts/-1K7oZV0UqY', 'Tel Aviv, Israel   Carlton Tel Aviv Hotel'), ('http://www.youtube.com/shorts/Gubaptw5ong', 'Tel Aviv, Israel   Market House Hotel'), ('http://www.youtube.com/shorts/AaX3PfEi8mw', 'Tel Aviv, Israel   Palmach Museum'), ('http://www.youtube.com/shorts/YTs5gPOopGo', 'London, United Kingdom   Sunday Roast'), ('http://www.youtube.com/shorts/xXrZzTSfa24', 'Dublin, Ireland   The Shelbourne Hotel'), ('http://www.youtube.com/shorts/nvDRtq9T5yw', 'Dublin, Ireland   The Westbury Hotel'), ('http://www.youtube.com/shorts/XIG4Ko9m-gg', 'Hanoi, Vietnam   JW Marriott Hotel Hanoi'), ('http://www.youtube.com/shorts/LiHtXKslS9o', 'Hanoi, Vietnam   Ho Chi Minh Mausoleum'), ('http://www.youtube.com/shorts/3CqnIeZ3pLw', 'Minsk, Belarus   Kalduny'), ('http://www.youtube.com/shorts/3UMtYfKlgFs', 'Minsk, Belarus   Public transportation tip4'), ('http://www.youtube.com/shorts/DBKY71wkngk', 'Minsk, Belarus   Hotel Europe'), ('http://www.youtube.com/shorts/CcLIaH24faQ', 'Minsk, Belarus   Botanical Garden'), ('http://www.youtube.com/shorts/0GKl8md6PJ0', 'Nairobi, Kenya   David Sheldrick Wildlife Trust'), ('http://www.youtube.com/shorts/EXd-YH-BCiE', 'Nairobi, Kenya   Public transportation tip3'), ('http://www.youtube.com/shorts/-M2t1872Qe8', 'Nairobi, Kenya   Giraffe Manor'), ('http://www.youtube.com/shorts/1kYG8_nSV_o', 'Nairobi, Kenya   Nyama Choma'), ('http://www.youtube.com/shorts/Qqx27dVyqtA', 'Alesund, Norway   Sunnmøre Museum'), ('http://www.youtube.com/shorts/YOP-gyPtgHo', 'Alesund, Norway   Quality Hotel Waterfront'), ('http://www.youtube.com/shorts/s85ZWL75yLk', 'Baku, Azerbaijan   The Landmark Hotel Baku'), ('http://www.youtube.com/shorts/uUVesTHaDmo', 'Baku, Azerbaijan   JW Marriott Absheron Baku'), ('http://www.youtube.com/shorts/5IzV3iMjE-8', 'Baku, Azerbaijan   Plov'), ('http://www.youtube.com/shorts/Jf3ZmzRqirs', 'Belgrade, Serbia   Knez Mihailova Street'), ('http://www.youtube.com/shorts/a22gQ-e7OxY', 'Belgrade, Serbia   Skadarlija'), ('http://www.youtube.com/shorts/Faqti4pnHIQ', 'Belgrade, Serbia   National Museum'), ('http://www.youtube.com/shorts/YHF37nwphW4', 'Santiago, Chile   Empanadas'), ('http://www.youtube.com/shorts/O5zGMp_Hq9E', 'Santiago, Chile   W Santiago'), ('http://www.youtube.com/shorts/unhpsibnZNQ', 'Santiago, Chile   Completo'), ('http://www.youtube.com/shorts/C98S4fgTEsc', 'Santiago, Chile   Public transportation tip4'), ('http://www.youtube.com/shorts/tyHpaZpdv5A', 'Colombo, Sri Lanka - Shangri-La Hotel Colombo'), ('http://www.youtube.com/shorts/NLig1vGFYtg', 'Colombo, Sri Lanka - Cinnamon Grand Colombo'), ('http://www.youtube.com/shorts/wFN5HuU45XY', 'Dubrovnik, Croatia - Summary'), ('http://www.youtube.com/shorts/qIHs-3fLy-w', 'Dubrovnik, Croatia - Public_transportation_tip1'), ('http://www.youtube.com/shorts/O8lZwv59Cik', 'Dubrovnik, Croatia - Black Risotto'), ('http://www.youtube.com/shorts/2SLNUprGO6E', 'Dubrovnik, Croatia - Hotel Excelsior'), ('http://www.youtube.com/shorts/uvHlxZJrMqI', 'Dubrovnik, Croatia - Banje Beach'), ('http://www.youtube.com/shorts/GRBB9w6M8G8', 'Buenos Aires, Argentina - Summary'), ('http://www.youtube.com/shorts/ekTM1kD6QS4', 'Buenos Aires, Argentina - Amazing Places to Visit'), ('http://www.youtube.com/shorts/2X9sYJNjfoc', 'Buenos Aires, Argentina - Transportation Tips'), ('http://www.youtube.com/shorts/1iJzd0qKNyo', 'Buenos Aires, Argentina - Best :waterfront'), ('http://www.youtube.com/shorts/s85ZWL75yLk', 'Baku, Azerbaijan   The Landmark Hotel Baku'), ('http://www.youtube.com/shorts/uUVesTHaDmo', 'Baku, Azerbaijan   JW Marriott Absheron Baku'), ('http://www.youtube.com/shorts/5IzV3iMjE-8', 'Baku, Azerbaijan   Plov'), ('http://www.youtube.com/shorts/Jf3ZmzRqirs', 'Belgrade, Serbia   Knez Mihailova Street'), ('http://www.youtube.com/shorts/a22gQ-e7OxY', 'Belgrade, Serbia   Skadarlija'), ('http://www.youtube.com/shorts/Faqti4pnHIQ', 'Belgrade, Serbia   National Museum'), ('http://www.youtube.com/shorts/YHF37nwphW4', 'Santiago, Chile   Empanadas'), ('http://www.youtube.com/shorts/O5zGMp_Hq9E', 'Santiago, Chile   W Santiago'), ('http://www.youtube.com/shorts/unhpsibnZNQ', 'Santiago, Chile   Completo'), ('http://www.youtube.com/shorts/C98S4fgTEsc', 'Santiago, Chile   Public transportation tip4'), ('http://www.youtube.com/shorts/tyHpaZpdv5A', 'Colombo, Sri Lanka - Shangri-La Hotel Colombo'), ('http://www.youtube.com/shorts/NLig1vGFYtg', 'Colombo, Sri Lanka - Cinnamon Grand Colombo'), ('http://www.youtube.com/shorts/wFN5HuU45XY', 'Dubrovnik, Croatia - Summary'), ('http://www.youtube.com/shorts/qIHs-3fLy-w', 'Dubrovnik, Croatia - Public_transportation_tip1'), ('http://www.youtube.com/shorts/O8lZwv59Cik', 'Dubrovnik, Croatia - Black Risotto'), ('http://www.youtube.com/shorts/2SLNUprGO6E', 'Dubrovnik, Croatia - Hotel Excelsior'), ('http://www.youtube.com/shorts/uvHlxZJrMqI', 'Dubrovnik, Croatia - Banje Beach'), ('http://www.youtube.com/shorts/GRBB9w6M8G8', 'Buenos Aires, Argentina - Summary'), ('http://www.youtube.com/shorts/ekTM1kD6QS4', 'Buenos Aires, Argentina - Amazing Places to Visit'), ('http://www.youtube.com/shorts/2X9sYJNjfoc', 'Buenos Aires, Argentina - Transportation Tips'), ('http://www.youtube.com/shorts/1iJzd0qKNyo', 'Buenos Aires, Argentina - Best Hotels to Stay'), ('http://www.youtube.com/shorts/Bru-0jeHphg', 'Cancun, Mexico - Public_transportation_tip1'), ('http://www.youtube.com/shorts/SwpVgK__Gmg', 'Cancun, Mexico - Live Aqua Beach Resort Cancun'), ('http://www.youtube.com/shorts/nmyrEMPU4kA', 'Cancun, Mexico - Summary'), ('http://www.youtube.com/shorts/Un5n3CMjZkQ', 'Cancun, Mexico - Poc Chuc'), ('http://www.youtube.com/shorts/lFAnbnHP7wo', 'Cancun, Mexico - Xel-Ha Park'), ('http://www.youtube.com/shorts/SYlswH_BDog', 'Buenos Aires, Argentina   Delicious Foods to Taste'), ('http://www.youtube.com/shorts/7M4xh_rv3v8', 'Riga, Latvia - Summary'), ('http://www.youtube.com/shorts/TElfcyU4XIo', 'Riga, Latvia - Public_transportation_tip1'), ('http://www.youtube.com/shorts/RMPbnTFL3d0', 'Riga, Latvia - Riga Black Balsam'), ('http://www.youtube.com/shorts/H9_FePo8Pt4', 'Riga, Latvia - Metropole Hotel by Semarah'), ('http://www.youtube.com/shorts/Z3R1H2VK0tY', 'Riga, Latvia   Latvian rye bread'), ('http://www.youtube.com/shorts/QU9kg1XMzvQ', 'Warsaw, Poland - Transportation Tips'), ('http://www.youtube.com/shorts/REYiUtxRSMg', 'Warsaw, Poland - Best Hotels to Stay'), ('http://www.youtube.com/shorts/IUUR_lgodI4', 'Warsaw, Poland - Amazing Places to Visit'), ('http://www.youtube.com/shorts/PC_ZH18oDmU', 'Warsaw, Poland   Delicious Foods to Taste'), ('http://www.youtube.com/shorts/EF5FlJnBonI', 'Santa Marta, Colombia - Taganga'), ('http://www.youtube.com/shorts/Onx_x_rEB0k', 'Santa Marta, Colombia - Summary'), ('http://www.youtube.com/shorts/zuv1u6b2XkM', 'Santa Marta, Colombia - Public_transportation_tip1'), ('http://www.youtube.com/shorts/tyRhWUsjPVY', 'Santa Marta, Colombia - Hotel Catedral Plaza'), ('http://www.youtube.com/shorts/C-S2zVYK0fw', 'Santa Marta, Colombia - Minca'), ('http://www.youtube.com/shorts/nYn4JwwJhzA', 'Casablanca, Morocco - Summary'), ('http://www.youtube.com/shorts/y8_WE-kpILc', 'Casablanca, Morocco - Transportation Tips'), ('http://www.youtube.com/shorts/pLCBuALpPeI', 'Casablanca, Morocco - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/fPj_qPcSff0', 'Casablanca, Morocco - Amazing Places to Visit'), ('http://www.youtube.com/shorts/-havff0vdv0', 'Seville, Spain - Museum of Fine Arts'), ('http://www.youtube.com/shorts/F-AfHYkSI_k', 'Seville, Spain - Hotel Palacio de Villapanés'), ('http://www.youtube.com/shorts/7OMDJblAvXU', 'Seville, Spain - Public_transportation_tip1'), ('http://www.youtube.com/shorts/4I67kdAGvRg', 'Kiev, Ukraine - Summary'), ('http://www.youtube.com/shorts/txNHxdSWkN8', 'Kiev, Ukraine - Best Hotels to Stay'), ('http://www.youtube.com/shorts/DpLeKfDIANo', 'Kiev, Ukraine - Amazing Places to Visit'), ('http://www.youtube.com/shorts/E4tZsMtevsU', 'Kiev, Ukraine - Transportation Tips'), ('http://www.youtube.com/shorts/Z9tPFaV0tOU', 'Kiev, Ukraine - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/LSSthteUbQo', 'Punta Del Este, Uruguay - Transportation Tips'), ('http://www.youtube.com/shorts/DHORKPzWBd4', 'Punta Del Este, Uruguay - Summary'), ('http://www.youtube.com/shorts/k0wbl_Z3uKI', 'Punta Del Este, Uruguay - Best Hotels to Stay'), ('http://www.youtube.com/shorts/z8sv6ciwYkk', 'Punta Del Este, Uruguay - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/C4p65ZbHLvk', 'Granada, Spain - Amazing Places to Visit'), ('http://www.youtube.com/shorts/tQYAkVlzOr8', 'Granada, Spain - Best Hotels to Stay'), ('http://www.youtube.com/shorts/99Pk0MyJlrs', 'Granada, Spain - Summary'), ('http://www.youtube.com/shorts/ztD6nL2S29U', 'Granada, Spain - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/nOH1-juQzWs', 'Petra, Jordan - Transportation Tips'), ('http://www.youtube.com/shorts/RQvp6il4nrI', 'Petra, Jordan - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/dmKh3ZggyoI', 'Geneva, Switzerland - Summary'), ('http://www.youtube.com/shorts/NlPRqeVjPL4', 'Geneva, Switzerland - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/QfwBGkQhJ_4', 'Geneva, Switzerland - Amazing Places to Visit'), ('http://www.youtube.com/shorts/lVhabh-EV8c', 'Geneva, Switzerland - Best Hotels to Stay'), ('http://www.youtube.com/shorts/yUCS60Z8X10', 'Manila, Philippines - Summary'), ('http://www.youtube.com/shorts/fy0O6naVxD8', 'Manila, Philippines - Best Hotels to Stay'), ('http://www.youtube.com/shorts/iNcre9ToxHI', 'Astana, Kazakhstan - Transportation Tips'), ('http://www.youtube.com/shorts/RKuYHOPWy5Y', 'Astana, Kazakhstan - Summary'), ('http://www.youtube.com/shorts/uDKbnUJuJeY', 'Astana, Kazakhstan - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/2qzXOk3ZMD4', 'Cusco, Peru - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/CqeZNmHLmVA', 'Cusco, Peru - Transportation Tips'), ('http://www.youtube.com/shorts/ROtuGUR8M94', 'Cusco, Peru - Amazing Places to Visit'), ('http://www.youtube.com/shorts/2gwe8PKzsMI', 'Bagan, Myanmar - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/URYPYqZfOaU', 'Bagan, Myanmar - Summary'), ('http://www.youtube.com/shorts/kbZt8Mdgcu0', 'Bagan, Myanmar - Transportation Tips'), ('http://www.youtube.com/shorts/mhgUZJXu6DE', 'Bagan, Myanmar - Amazing Places to Visit'), ('http://www.youtube.com/shorts/BybsrtkEBQI', 'Bagan, Myanmar - Best Hotels to Stay'), ('http://www.youtube.com/shorts/ajteYHqWPFc', 'Panama City, Panama - Amazing Places to Visit'), ('http://www.youtube.com/shorts/ccX7AreuzRA', 'Panama City, Panama - Summary'), ('http://www.youtube.com/shorts/ezKlPUYY_0Y', 'Panama City, Panama - Transportation Tips'), ('http://www.youtube.com/shorts/9ZPJN0aRBJg', 'Quito, Ecuador - Summary'), ('http://www.youtube.com/shorts/j4PlUE6NvkE', 'Quito, Ecuador - Best Hotels to Stay'), ('http://www.youtube.com/shorts/1HQGQHSWl64', 'Quito, Ecuador - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Ngxa_lw0AJo', 'Quito, Ecuador - Transportation Tips'), ('http://www.youtube.com/shorts/drKi09ap520', 'Havana, Cuba - Best Hotels to Stay'), ('http://www.youtube.com/shorts/ZR-FYhNrCMw', 'Havana, Cuba - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Z2mi9YbtXU4', 'Havana, Cuba - Transportation Tips'), ('http://www.youtube.com/shorts/9CfYTAFDPyM', 'Havana, Cuba - Summary'), ('http://www.youtube.com/shorts/UEqclxUu8fA', 'Havana, Cuba - Amazing Places to Visit'), ('http://www.youtube.com/shorts/KHfMEh1Uqng', 'Santo Domingo, Dominican Republic - Transportation Tips'), ('http://www.youtube.com/shorts/Lc93k2F0XIw', 'Santo Domingo, Dominican Republic - Best Hotels to Stay'), ('http://www.youtube.com/shorts/lX0RWRrsDTs', 'Santo Domingo, Dominican Republic - Amazing Places to Visit'), ('http://www.youtube.com/shorts/QHmeLXLc0OQ', 'Santo Domingo, Dominican Republic - Summary'), ('http://www.youtube.com/shorts/p3QbEm03Uis', 'Santo Domingo, Dominican Republic - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Dyt-M5RLbiI', 'Lalibela, Ethiopia - Transportation Tips'), ('http://www.youtube.com/shorts/rr7kgMTo4qA', 'Lalibela, Ethiopia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/pwuDDFnJr3Q', 'Lalibela, Ethiopia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/euV_DB6c-rU', 'Lalibela, Ethiopia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/Fs6TphmZYJQ', 'Lalibela, Ethiopia - Summary'), ('http://www.youtube.com/shorts/TVO-zr5Dm3w', 'St'), ('http://www.youtube.com/shorts/rHouHzCyuC8', 'St'), ('http://www.youtube.com/shorts/IzEeZV4XSaA', 'St'), ('http://www.youtube.com/shorts/Cfap_eI9sFE', 'St'), ('http://www.youtube.com/shorts/7TEdReunTrA', 'Tirana, Albania - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/I8AzLAqiGR4', 'Tirana, Albania - Amazing Places to Visit'), ('http://www.youtube.com/shorts/kgsoF7ZfQUA', 'Tirana, Albania - Best Hotels to Stay'), ('http://www.youtube.com/shorts/sNGFY3y2snI', 'Tirana, Albania - Transportation Tips'), ('http://www.youtube.com/shorts/rrbitYLEMnE', 'Tirana, Albania - Summary'), ('http://www.youtube.com/shorts/tBDlpE6dTlE', 'Melbourne, Australia - Summary'), ('http://www.youtube.com/shorts/n7hFyq5FZoM', 'Melbourne, Australia - Transportation Tips'), ('http://www.youtube.com/shorts/F5aNAr2bb_8', 'Udaipur, India - Amazing Places to Visit'), ('http://www.youtube.com/shorts/LgrhI2RWsdQ', 'Udaipur, India - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/p3AqBRN2GYA', 'Udaipur, India - Best Hotels to Stay'), ('http://www.youtube.com/shorts/ti_5t_-mTw4', 'Udaipur, India - Summary'), ('http://www.youtube.com/shorts/g3aII9HpKLQ', 'Valencia, Spain - Summary'), ('http://www.youtube.com/shorts/2YcCEK7vGDg', 'Valencia, Spain - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/zTFHKfHJujw', 'Valencia, Spain - Amazing Places to Visit'), ('http://www.youtube.com/shorts/1Ct5k5FtaFw', 'Ho Chi Minh City, Vietnam - Best Hotels to Stay'), ('http://www.youtube.com/shorts/b-6oqxjeLL8', 'Ho Chi Minh City, Vietnam - Amazing Places to Visit'), ('http://www.youtube.com/shorts/trj4nh22Ld4', 'Ho Chi Minh City, Vietnam - Summary'), ('http://www.youtube.com/shorts/Evtm9gkLvUo', 'Ho Chi Minh City, Vietnam - Transportation Tips'), ('http://www.youtube.com/shorts/GjsLskGN3us', 'Ho Chi Minh City, Vietnam - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/qtVRHLAZJQ0', 'Jeju Island, South Korea - Amazing Places to Visit'), ('http://www.youtube.com/shorts/Kkf4UoEzvKc', 'Jeju Island, South Korea - Summary'), ('http://www.youtube.com/shorts/SSWOVgkisxo', 'Jeju Island, South Korea - Best Hotels to Stay'), ('http://www.youtube.com/shorts/M2-0K-q0sw4', 'Jeju Island, South Korea - Transportation Tips'), ('http://www.youtube.com/shorts/t-O44gXbKmw', 'Oxford, United Kingdom - Amazing Places to Visit'), ('http://www.youtube.com/shorts/yj77QtHpAd0', 'Oxford, United Kingdom - Transportation Tips'), ('http://www.youtube.com/shorts/fTzScs_wIj0', 'Oxford, United Kingdom - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/9k_6wbaFXYM', 'Antalya, Turkey - Summary'), ('http://www.youtube.com/shorts/YQ4ckwzLMgA', 'Antalya, Turkey - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Qs50POqBelI', 'Antalya, Turkey - Amazing Places to Visit'), ('http://www.youtube.com/shorts/5JPlKJotrkY', 'Antalya, Turkey - Best Hotels to Stay'), ('http://www.youtube.com/shorts/wWCpvisXtzo', 'Antalya, Turkey - Transportation Tips'), ('http://www.youtube.com/shorts/OjujJcBeSNg', 'Bled, Slovenia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/wgSemOJTmgA', 'Bled, Slovenia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/YIRClLD52nc', 'Bled, Slovenia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Toy7T5qQGAo', 'Bled, Slovenia - Summary'), ('http://www.youtube.com/shorts/ghW06dA1rIE', 'Bled, Slovenia - Transportation Tips'), ('http://www.youtube.com/shorts/PHH9C3v9GqY', 'Zanzibar, Tanzania - Transportation Tips'), ('http://www.youtube.com/shorts/JU3O9PLT7HA', 'Zanzibar, Tanzania - Best Hotels to Stay'), ('http://www.youtube.com/shorts/HoFbtZxOSN4', 'Zanzibar, Tanzania - Summary'), ('http://www.youtube.com/shorts/g_yNfDn9ERM', 'Zanzibar, Tanzania - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/rAR5vSLmJ4M', 'Zanzibar, Tanzania - Amazing Places to Visit'), ('http://www.youtube.com/shorts/GAgYNzh7WeU', 'Cebu, Philippines - Best Hotels to Stay'), ('http://www.youtube.com/shorts/uqjIK2-d1jM', 'Cebu, Philippines - Amazing Places to Visit'), ('http://www.youtube.com/shorts/1Ws2RORXRK0', 'Cebu, Philippines - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/tO_pNyCaL8E', 'Cebu, Philippines - Transportation Tips'), ('http://www.youtube.com/shorts/ARRMsLyTzn0', 'Cebu, Philippines - Summary'), ('http://www.youtube.com/shorts/IzN5N7j_w1E', 'Doha, Qatar - Transportation Tips'), ('http://www.youtube.com/shorts/Anqq01DhXLQ', 'Doha, Qatar - Best Hotels to Stay'), ('http://www.youtube.com/shorts/4c4IeIEUv1I', 'Doha, Qatar - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/0eCNVLcCDKI', 'Doha, Qatar - Summary'), ('http://www.youtube.com/shorts/BkoT1JLWY4k', 'Doha, Qatar - Amazing Places to Visit'), ('http://www.youtube.com/shorts/U2XM6jxgFNA', 'Cleveland, United States - Summary'), ('http://www.youtube.com/shorts/8qzeTe1q-m8', 'Cleveland, United States - Best Hotels to Stay'), ('http://www.youtube.com/shorts/9Fzz9YQtT5I', 'Cleveland, United States - Amazing Places to Visit'), ('http://www.youtube.com/shorts/iX7dc_vfh4Y', 'Cleveland, United States - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/vmZNxjHBxfk', 'Cleveland, United States - Transportation Tips'), ('http://www.youtube.com/shorts/C79eW2KtKm0', 'Agra, India - Summary'), ('http://www.youtube.com/shorts/ywfnzgMvwHU', 'Agra, India - Transportation Tips'), ('http://www.youtube.com/shorts/OlXK2Eu1IWY', 'Agra, India - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/nfCRxNJtCqQ', 'Dover, United Kingdom - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/egfazAOO9Io', 'Dover, United Kingdom - Transportation Tips'), ('http://www.youtube.com/shorts/7Q-QHLVTty4', 'Dover, United Kingdom - Amazing Places to Visit'), ('http://www.youtube.com/shorts/RnsdMp7cM84', 'Dover, United Kingdom - Summary'), ('http://www.youtube.com/shorts/C8v373iQPrA', 'Dover, United Kingdom - Best Hotels to Stay'), ('http://www.youtube.com/shorts/XPO0-n3QcBM', 'Ljubljana, Slovenia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/OpE8m8qKz1A', 'Ljubljana, Slovenia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/7RUYmM-PqLI', 'Ljubljana, Slovenia - Transportation Tips'), ('http://www.youtube.com/shorts/elUUU9VUXBY', 'Ljubljana, Slovenia - Summary'), ('http://www.youtube.com/shorts/q_9XF718L50', 'Rishikesh, India - Summary'), ('http://www.youtube.com/shorts/UmdrDzbFT74', 'Rishikesh, India - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/vAaYZEdhbzE', 'Rishikesh, India - Amazing Places to Visit'), ('http://www.youtube.com/shorts/Yvb1Bm9Tbu4', 'Rishikesh, India - Best Hotels to Stay'), ('http://www.youtube.com/shorts/lvrc-4FbwWA', 'Rishikesh, India - Transportation Tips'), ('http://www.youtube.com/shorts/uFmH1mMAY5c', 'Liverpool, United Kingdom - Best Hotels to Stay'), ('http://www.youtube.com/shorts/iIl_TnTkP2U', 'Liverpool, United Kingdom - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/wV7QjJkrI5M', 'Liverpool, United Kingdom - Amazing Places to Visit'), ('http://www.youtube.com/shorts/UNOBVf3wozY', 'Liverpool, United Kingdom - Transportation Tips'), ('http://www.youtube.com/shorts/blEfucVFimA', 'Liverpool, United Kingdom - Summary'), ('http://www.youtube.com/shorts/HIYaomF64RE', 'Victoria, Seychelles - Best Hotels to Stay'), ('http://www.youtube.com/shorts/ScKoAC1pF3g', 'Victoria, Seychelles - Amazing Places to Visit'), ('http://www.youtube.com/shorts/6z19QSMP1sw', 'Victoria, Seychelles - Transportation Tips'), ('http://www.youtube.com/shorts/u3hVjQ6Zn54', 'Victoria, Seychelles - Summary'), ('http://www.youtube.com/shorts/2SjtzWWXha4', 'Brisbane, Australia - Transportation Tips'), ('http://www.youtube.com/shorts/jLPKoAv2H7o', 'Brisbane, Australia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/LPLr64yLXJA', 'Brisbane, Australia - Summary'), ('http://www.youtube.com/shorts/98WBhwj7ezY', 'Brisbane, Australia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/11PrPGo37m0', 'Brisbane, Australia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/2PXM9IHEAU4', 'Trinidad, Cuba - Transportation Tips'), ('http://www.youtube.com/shorts/fnh5V4l0PJE', 'Trinidad, Cuba - Best Hotels to Stay'), ('http://www.youtube.com/shorts/NuCNJtHC7rk', 'Trinidad, Cuba - Summary'), ('http://www.youtube.com/shorts/8cQ-WIPHZSE', 'Trinidad, Cuba - Amazing Places to Visit'), ('http://www.youtube.com/shorts/CwSlrF2DTvY', 'Bali, Indonesia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/hafEFJOSw4s', 'Bali, Indonesia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/HL0rT8GFhog', 'Bali, Indonesia - Summary'), ('http://www.youtube.com/shorts/WpaYJGog4uU', 'Seattle, United States - Transportation Tips'), ('http://www.youtube.com/shorts/2jpP5r-30NQ', 'Seattle, United States - Amazing Places to Visit'), ('http://www.youtube.com/shorts/kCCc8uqVs-o', 'Seattle, United States - Summary'), ('http://www.youtube.com/shorts/iYpOwZge7Nc', 'Seattle, United States - Best Hotels to Stay'), ('http://www.youtube.com/shorts/9rxS2MCvgPk', 'Seattle, United States - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/AZ9DnX8fmaU', 'Cartagena, Colombia - Summary'), ('http://www.youtube.com/shorts/cuJAXJwm68k', 'Cartagena, Colombia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/pED86OUSuv4', 'Cartagena, Colombia - Transportation Tips'), ('http://www.youtube.com/shorts/-Hsf4FDNtSs', 'Cartagena, Colombia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/VY64BQbn-lI', 'Port-Au-Prince, Haiti - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/4TrY7EoBzik', 'Port-Au-Prince, Haiti - Summary'), ('http://www.youtube.com/shorts/MMZzhnHl118', 'Port-Au-Prince, Haiti - Transportation Tips'), ('http://www.youtube.com/shorts/dS745FiIn_c', 'Port-Au-Prince, Haiti - Best Hotels to Stay'), ('http://www.youtube.com/shorts/K85kxP3R7qo', 'Port-Au-Prince, Haiti - Amazing Places to Visit'), ('http://www.youtube.com/shorts/UVJRf8CcZoM', 'Brasilia, Brazil - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/i_fZ2ENK8iY', 'Brasilia, Brazil - Summary'), ('http://www.youtube.com/shorts/B5CgaDgLqNk', 'Brasilia, Brazil - Best Hotels to Stay'), ('http://www.youtube.com/shorts/TjyXKgoeJbc', 'Brasilia, Brazil - Transportation Tips'), ('http://www.youtube.com/shorts/5uZEtn4wMzQ', 'Florence, Italy - Summary'), ('http://www.youtube.com/shorts/dObSYXZQ6dU', 'Florence, Italy - Best Hotels to Stay'), ('http://www.youtube.com/shorts/-qDLHTd7O9U', 'Florence, Italy - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/MwUYQut9Dv4', 'Florence, Italy - Amazing Places to Visit'), ('http://www.youtube.com/shorts/kas5lYVl8AE', 'Florence, Italy - Transportation Tips'), ('http://www.youtube.com/shorts/9eKLHXANAOk', 'Sao Paulo, Brazil - Best Hotels to Stay'), ('http://www.youtube.com/shorts/ALl3EJwEcyY', 'Sao Paulo, Brazil - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/XM9FuoOhK7c', 'Sao Paulo, Brazil - Transportation Tips'), ('http://www.youtube.com/shorts/75bI9uosTaY', 'Sao Paulo, Brazil - Summary'), ('http://www.youtube.com/shorts/xklr46rM4qA', 'Asuncion, Paraguay - Best Hotels to Stay'), ('http://www.youtube.com/shorts/-dlqBJ63MpE', 'Asuncion, Paraguay - Amazing Places to Visit'), ('http://www.youtube.com/shorts/hyFrOtLOoJE', 'Asuncion, Paraguay - Transportation Tips'), ('http://www.youtube.com/shorts/DBA-KKv9lPI', 'Asuncion, Paraguay - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/Vpu9HZxN5jw', 'Asuncion, Paraguay - Summary'), ('http://www.youtube.com/shorts/x0jDq_QFbj4', 'Paphos, Cyprus - Best Hotels to Stay'), ('http://www.youtube.com/shorts/Tg_wQGqW20U', 'Paphos, Cyprus - Amazing Places to Visit'), ('http://www.youtube.com/shorts/Pg-8LX9LiUY', 'Paphos, Cyprus - Transportation Tips'), ('http://www.youtube.com/shorts/R52i9AAXLOc', 'Paphos, Cyprus - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/aozQyMMQn0o', 'Kotor, Montenegro - Best Hotels to Stay'), ('http://www.youtube.com/shorts/Ho4W4kaep5I', 'Kotor, Montenegro - Summary'), ('http://www.youtube.com/shorts/sgNEhpcTD8k', 'Kotor, Montenegro - Transportation Tips'), ('http://www.youtube.com/shorts/CP98AghoArU', 'Kotor, Montenegro - Amazing Places to Visit'), ('http://www.youtube.com/shorts/3W25wwSl0Po', 'Limassol, Cyprus - Transportation Tips'), ('http://www.youtube.com/shorts/PPJnHGxSRWg', 'Limassol, Cyprus - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/lB3Dks-1xgg', 'Limassol, Cyprus - Summary'), ('http://www.youtube.com/shorts/sild41sQH3M', 'Limassol, Cyprus - Amazing Places to Visit'), ('http://www.youtube.com/shorts/xcy-zYOFxx0', 'La Paz, Bolivia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/Mv3NNJynuFc', 'La Paz, Bolivia - Summary'), ('http://www.youtube.com/shorts/3vZwBiLP6bs', 'La Paz, Bolivia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/jOOpUNxsm8g', 'Denver, United States - Best Hotels to Stay'), ('http://www.youtube.com/shorts/2MVjdecl4eU', 'Denver, United States - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/eMRSKXdAlN4', 'Denver, United States - Amazing Places to Visit'), ('http://www.youtube.com/shorts/ZoJyxdww5pY', 'Capri, Italy - Summary'), ('http://www.youtube.com/shorts/c_oz-n3NpyU', 'Capri, Italy - Transportation Tips'), ('http://www.youtube.com/shorts/WLkyXvOQjSA', 'Shanghai, China - Amazing Places to Visit'), ('http://www.youtube.com/shorts/sL2kUnRMfsA', 'Shanghai, China - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/08uZKrdZ0vg', 'Shanghai, China - Summary'), ('http://www.youtube.com/shorts/BLuucJaKFK8', 'Shanghai, China - Transportation Tips'), ('http://www.youtube.com/shorts/TtFnYefCnl8', 'Muscat, Oman - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/ThBVo0FnRVk', 'Muscat, Oman - Best Hotels to Stay'), ('http://www.youtube.com/shorts/JDrVA_1P9pQ', 'Muscat, Oman - Amazing Places to Visit'), ('http://www.youtube.com/shorts/qPXgIXCKdwI', 'Muscat, Oman - Summary'), ('http://www.youtube.com/shorts/d3Qm_PVDKPM', 'Limassol, Cyprus - Transportation Tips'), ('http://www.youtube.com/shorts/gd2oP-H3tg4', 'Limassol, Cyprus - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/hRJm-VmONDE', 'Limassol, Cyprus - Summary'), ('http://www.youtube.com/shorts/pIZPi7T21xk', 'Limassol, Cyprus - Amazing Places to Visit'), ('http://www.youtube.com/shorts/78dEEZfHf4U', 'Chiang Mai, Thailand - Summary'), ('http://www.youtube.com/shorts/QljmSITcVxM', 'Chiang Mai, Thailand - Best Hotels to Stay'), ('http://www.youtube.com/shorts/1w5XyLiUZsA', 'Chiang Mai, Thailand - Transportation Tips'), ('http://www.youtube.com/shorts/QGxR2RK4DKQ', 'Chiang Mai, Thailand - Amazing Places to Visit'), ('http://www.youtube.com/shorts/pGS5Q0Dy7a8', 'Almaty, Kazakhstan - Summary'), ('http://www.youtube.com/shorts/xzlJbhy_Sto', 'Almaty, Kazakhstan - Transportation Tips'), ('http://www.youtube.com/shorts/G0kwyu0_w94', 'Almaty, Kazakhstan - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/TF8iptCexgo', 'Lima, Peru - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/VherJJtXiTg', 'Lima, Peru - Amazing Places to Visit'), ('http://www.youtube.com/shorts/1RhxwuK6E6A', 'Lima, Peru - Transportation Tips'), ('http://www.youtube.com/shorts/hF-PaKHAO9Q', 'Lima, Peru - Summary'), ('http://www.youtube.com/shorts/LYa3eptyLY8', 'La Paz, Bolivia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/dwHGs0w7HnA', 'La Paz, Bolivia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/hybxG54USX0', 'La Paz, Bolivia - Summary'), ('http://www.youtube.com/shorts/O5ZF07mEQcA', 'La Paz, Bolivia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/sqR8a87g3pU', 'Gozo, Malta - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/ETw7XahZVLU', 'Gozo, Malta - Summary'), ('http://www.youtube.com/shorts/1n4OIxF4IwE', 'Gozo, Malta - Amazing Places to Visit'), ('http://www.youtube.com/shorts/aNJ2NtULWVM', 'Detroit, United States - Transportation Tips'), ('http://www.youtube.com/shorts/JpNLjmZBK30', 'Detroit, United States - Best Hotels to Stay'), ('http://www.youtube.com/shorts/eW8diZi4eFI', 'Detroit, United States - Summary'), ('http://www.youtube.com/shorts/IyW0Rx1yXR4', 'Detroit, United States - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/nFnUAPhKpoE', 'Adelaide, Australia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/52Zmhya2jOk', 'Adelaide, Australia - Summary'), ('http://www.youtube.com/shorts/MTo7Avbn0Ts', 'Adelaide, Australia - Transportation Tips'), ('http://www.youtube.com/shorts/K_Tah_wVi1E', 'St'), ('http://www.youtube.com/shorts/pX9t8HzoY7g', 'Panama City, Panama   Delicious Foods to Taste'), ('http://www.youtube.com/shorts/oon5O6rBDSA', 'Ljubljana, Slovenia   Best Hotels to Stay'), ('http://www.youtube.com/shorts/R395ucie2zY', 'Agra, India   Best Hotels to Stay'), ('http://www.youtube.com/shorts/i68opZQwQGQ', 'Gozo, Malta   Best Hotels to Stay'), ('http://www.youtube.com/shorts/RU5jCqms37o', 'Bali, Indonesia   Transportation Tips'), ('http://www.youtube.com/shorts/F9QhNVxtNK0', 'Brasilia, Brazil   Amazing Places to Visit'), ('http://www.youtube.com/shorts/2b37Kjh419I', 'Capri, Italy   Best Hotels to Stay'), ('http://www.youtube.com/shorts/zAyX_KWgQ1U', 'Capri, Italy   Amazing Places to Visit'), ('http://www.youtube.com/shorts/lM02qJ14zIM', 'Almaty, Kazakhstan   Best Hotels to Stay'), ('http://www.youtube.com/shorts/WuXvXB0OV3E', 'Denver, United States   Transportation Tips'), ('http://www.youtube.com/shorts/_pcFEndGFYM', 'Adelaide, Australia   Best Hotels to Stay'), ('http://www.youtube.com/shorts/wOyxfRW4B1M', 'Maputo, Mozambique - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/sTPXH0Zdncs', 'Maputo, Mozambique - Transportation Tips'), ('http://www.youtube.com/shorts/3TCksT-GI2Y', 'Maputo, Mozambique - Best Hotels to Stay'), ('http://www.youtube.com/shorts/wuFfNMrfMfc', 'Maputo, Mozambique - Amazing Places to Visit'), ('http://www.youtube.com/shorts/VAuqjjrtZ60', 'Mexico City, Mexico - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/EZB5ohf2_vU', 'Mexico City, Mexico - Amazing Places to Visit'), ('http://www.youtube.com/shorts/jhWiMELltQU', 'Mexico City, Mexico - Transportation Tips'), ('http://www.youtube.com/shorts/Q-U6IfvMSfg', 'Mexico City, Mexico - Best Hotels to Stay'), ('http://www.youtube.com/shorts/OXLul6R-UtI', 'Sossusvlei, Namibia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/XCYWHmojO1g', 'Sossusvlei, Namibia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/hdVMrRZNHEs', 'San Juan, Puerto Rico - Summary'), ('http://www.youtube.com/shorts/sFRlItCEJNs', 'San Juan, Puerto Rico - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/PuXqeFtHKxI', 'San Juan, Puerto Rico - Amazing Places to Visit'), ('http://www.youtube.com/shorts/R9YZ-cah4bk', 'San Juan, Puerto Rico - Transportation Tips'), ('http://www.youtube.com/shorts/qiAVRsfR5fo', 'Kingston, Jamaica - Summary'), ('http://www.youtube.com/shorts/Nr2sJpRQn-c', 'Kingston, Jamaica - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/5ejcpRsX71E', 'Kingston, Jamaica - Best Hotels to Stay'), ('http://www.youtube.com/shorts/XgQAnTEyPZw', 'Kingston, Jamaica - Amazing Places to Visit'), ('http://www.youtube.com/shorts/syzmVWO2WYs', 'San Gimignano, Italy - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/_HoMGA4JM6Y', 'San Gimignano, Italy - Transportation Tips'), ('http://www.youtube.com/shorts/M6c5xJIgDU8', 'San Gimignano, Italy - Best Hotels to Stay'), ('http://www.youtube.com/shorts/7kk-Eqz3sMc', 'San Gimignano, Italy - Amazing Places to Visit'), ('http://www.youtube.com/shorts/tc1pWU69G04', 'Lugano, Switzerland - Amazing Places to Visit'), ('http://www.youtube.com/shorts/KSTb9FbWdcI', 'Lugano, Switzerland - Best Hotels to Stay'), ('http://www.youtube.com/shorts/tntY7Itd5UY', 'Lugano, Switzerland - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/jow7f_S5yus', 'Lugano, Switzerland - Transportation Tips'), ('http://www.youtube.com/shorts/IqzbE0DXRUA', 'Thessaloniki, Greece - Summary'), ('http://www.youtube.com/shorts/48p2M5LQTSw', 'Thessaloniki, Greece - Transportation Tips'), ('http://www.youtube.com/shorts/3I1wn2P1ZWU', 'Thessaloniki, Greece - Best Hotels to Stay'), ('http://www.youtube.com/shorts/gQlbhh1hf1c', 'Thessaloniki, Greece - Amazing Places to Visit'), ('http://www.youtube.com/shorts/b2ffVGOBPYs', 'Cardiff, United Kingdom - Best Hotels to Stay'), ('http://www.youtube.com/shorts/9-dNvx6udyc', 'Cardiff, United Kingdom - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/n1uZ9TUJmIw', 'Cardiff, United Kingdom - Transportation Tips'), ('http://www.youtube.com/shorts/3qaG0oy3u8o', 'Cardiff, United Kingdom - Summary'), ('http://www.youtube.com/shorts/SQDdsTxiJNQ', 'Bissau, Guinea-Bissau - Best Hotels to Stay'), ('http://www.youtube.com/shorts/64Kc3hY5at8', 'Bissau, Guinea-Bissau - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/T5-qIVwg_VM', 'Bissau, Guinea-Bissau - Transportation Tips'), ('http://www.youtube.com/shorts/ls4h38KeZns', 'Bissau, Guinea-Bissau - Summary'), ('http://www.youtube.com/shorts/DLJqVhHcNXA', 'Santorini, Greece - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/1CDSNtmN3R8', 'Santorini, Greece - Amazing Places to Visit'), ('http://www.youtube.com/shorts/jFGJ2jJW2Eo', 'Santorini, Greece - Summary'), ('http://www.youtube.com/shorts/mHo8WapVilY', 'Santorini, Greece - Best Hotels to Stay'), ('http://www.youtube.com/shorts/MC1AJ57-vYw', 'Sintra, Portugal - Best Hotels to Stay'), ('http://www.youtube.com/shorts/8pSN-oJOfX0', 'Sintra, Portugal - Transportation Tips'), ('http://www.youtube.com/shorts/7gGDpY84UA0', 'Sintra, Portugal - Summary'), ('http://www.youtube.com/shorts/Xy5jWp-F7ms', 'Sintra, Portugal - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/SrkiZQZ7DLg', 'Lucca, Italy - Amazing Places to Visit'), ('http://www.youtube.com/shorts/jCXZmF2Hh1E', 'Lucca, Italy - Transportation Tips'), ('http://www.youtube.com/shorts/LLW7_QkgVMA', 'Lucca, Italy - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/IAFFIZbHJVU', 'Lucca, Italy - Best Hotels to Stay'), ('http://www.youtube.com/shorts/K1ib1sjiL_s', 'Taipei, Taiwan - Amazing Places to Visit'), ('http://www.youtube.com/shorts/cm_wKBZNG64', 'Taipei, Taiwan - Best Hotels to Stay'), ('http://www.youtube.com/shorts/UjwQHQ0HKqo', 'Taipei, Taiwan - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/_RkiFZnVt2M', 'Taipei, Taiwan - Summary'), ('http://www.youtube.com/shorts/GcMIjr_Bi6E', 'Vladivostok, Russia - Best Hotels to Stay'), ('http://www.youtube.com/shorts/Jzzksp2RYGg', 'Vladivostok, Russia - Amazing Places to Visit'), ('http://www.youtube.com/shorts/FI7xV5N_58s', 'Vladivostok, Russia - Summary'), ('http://www.youtube.com/shorts/xtIYpQQHzOk', 'Vladivostok, Russia - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/ZOJ6tGt2ptc', 'Interlaken, Switzerland - Transportation Tips'), ('http://www.youtube.com/shorts/UsSPQdA8nIo', 'Interlaken, Switzerland - Amazing Places to Visit'), ('http://www.youtube.com/shorts/TxITQfDZrck', 'Interlaken, Switzerland - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/m-cszR0lzZw', 'Interlaken, Switzerland - Summary'), ('http://www.youtube.com/shorts/1TsgzFUgaxQ', 'Bran, Romania - Transportation Tips'), ('http://www.youtube.com/shorts/JdIKXiYXO9s', 'Bran, Romania - Delicious Foods to Taste'), ('http://www.youtube.com/shorts/C-6wi8yiT6Y', 'Bran, Romania - Amazing Places to Visit'), ('http://www.youtube.com/shorts/AM7Yv7dbNv4', 'Bran, Romania - Summary')]
    uploader.upload_one_short(param)
