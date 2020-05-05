# UT-TOR-DATA-PT-01-2020-U-C Week 12 Homework
# Web Scraping Challenge
# (C) Boris Smirnov

import pandas as pd
from bs4 import BeautifulSoup
from splinter import Browser
import requests
import re
import time


# Global parameters with splinter Browser configuration parameters
# Put them here so the calling app can modify them
browser_args = {
    "executable_path": "chromedriver.exe",
    "headless": True
}


# The class is used to report scraping progress to a progress bar on clinet's side
class Progress():
    # Parameter: a list of all events that signufy advancement of a progress bar
    def __init__(self, events_lst = [""]):
        self.events_lst = events_lst
        self.progress = 0.0
        self.stage = 0
        self.stages = len(events_lst)
        if self.stages:
            self.step = 100.0 / self.stages
        else:
            self.events_lst = [""]
            self.progress = 100

    # Advances a progress bar either by one event, or up to the named event
    def stage_start(self, event_name=""):
        self.stage += 1
        if self.stage > self.stages:
            self.stage = self.stages

        if not event_name:
            try:
                self.stage = self.events_lst.index(event_name) + 1
            except:
                pass

        self.progress = self.stage * self.step
        if self.progress > 100:
            self.progress = 100
        
    # Advances a progress bar by a small step inside of the current stage of progress
    # For example: a stage might have 10 sub stages, to advance to the 3rd step, call progress.substage_start(3, 10)
    # Steps are not accumulated
    def substage_start(self, num, total):
        self.progress = (self.stage + (num-1)/total) * self.step

    # Return a dictionary with the current progress
    # Intended to be returnes as JSON object to a request
    def to_dict(self):
        return {
            'progress': int(self.progress),
            'stage': self.stage,
            'stages': self.stages,
            'name': self.events_lst[self.stage - 1]
        }
    

def make_scraping_progress():
    return Progress([
        "Staring browser",
        "NASA Mars News",
        "JPL Mars Space Images",
        "Mars Weather",
        "Mars Facts",
        "Mars Hemispheres",
        "Finalizing"
    ])


# Function does actual scraping and returns a dictionary with scraped data
# Parameter: Progress object
def scrape(progress: Progress):

    # One browser to rule them all
    progress.stage_start()
    browser = Browser('chrome', **browser_args)

    # NASA Mars News
    # ===============

    progress.stage_start()
    nasa_mars_news_url = 'https://mars.nasa.gov/news/'
    browser.visit(nasa_mars_news_url)

    first_news_node = browser.find_by_css('li.slide').first

    news_title = first_news_node.find_by_css('div.content_title').text
    news_para = first_news_node.find_by_css('div.article_teaser_body').text

    # JPL Mars Space Images - Featured Image
    # =======================================
    # N.B. Featured image changes periodically and it isn't necesserily a Mars image, it may be pretty much anything - Saturn, for example.

    progress.stage_start()
    base_jpl_url = 'https://www.jpl.nasa.gov'
    jpl_mars_images_url = 'https://www.jpl.nasa.gov/spaceimages/?search=&category=Mars'
    browser.visit(jpl_mars_images_url)

    featured_node = browser.find_by_css('article.carousel_item').first
    s = featured_node['style']
    featured_image_url = base_jpl_url + re.search(r'url\("(.+)"\)', s).group(1)
    featured_image_alt = featured_node['alt']

    # Mars Weather
    # =============

    progress.stage_start()
    logout_timeout = 1
    tweets_timeout = 3
    steps_count = 1 + logout_timeout + 1 + tweets_timeout
    current_step = 0

    twitter_logout_url = 'https://twitter.com/logout'
    mars_weather_url = 'https://twitter.com/marswxreport?lang=en'
    
    progress.substage_start(current_step, steps_count)
    browser.visit(twitter_logout_url)
    steps_count += 1

    for i in range(0, logout_timeout):
        progress.substage_start(current_step, steps_count)
        time.sleep(1)
        current_step += 1

    progress.substage_start(current_step, steps_count)
    browser.visit(mars_weather_url)
    steps_count += 1

    # Wait for the page to load!
    # It didn't work without the delay
    for i in range(tweets_timeout):
        progress.substage_start(current_step, steps_count)
        time.sleep(1)
        current_step += 1

    no_weather_msg = "Failed to extract weather information"
    mars_weather = no_weather_msg

    # Elaborate approach: going down the DOM tree...
    soup = BeautifulSoup(browser.html, 'lxml')
    tweet_nodes = soup.select('div[data-testid="tweet"]')

    for tweet_node in tweet_nodes:
        # tweet_node has 2 child nodes: [0] - left sidebar, [1] - right tweet body
        tweet_right_part = tweet_node.contents[1]

        # tweet_right_part has 2 child nodes: [0] - header part, [1] - tweet contents part
        tweet_contents_part = tweet_right_part.contents[1]

        # tweet_contents_part has 3 child nodes: [0] - text, [1] - image, [2] - controls (reply/retweet/like)
        tweet_text = tweet_contents_part.contents[0]

        mars_weather = tweet_text.text
        match = re.search('^InSight', mars_weather)
        if match:
            mars_weather = mars_weather.replace('\n', ' ')
            break

    if mars_weather == no_weather_msg:
        # Try again
        browser.reload()
        time.sleep(3)

        # Very stupid and straightforward (and probably the most effective) approach:
        # Just find the first string that looks like Mars weather
        match = re.search('InSight ([^<]+) hPa', browser.html)
        if match: # Gotcha!
            s = match.group(1)
            mars_weather = 'InSight ' + s.replace('\n', ' ') + ' hPa'

    # Mars Facts
    # ===========

    progress.stage_start()
    mars_facts_url = 'https://space-facts.com/mars/'
    df_list = pd.read_html(mars_facts_url)
    mars_facts_df = df_list[0]
    mars_facts_df.set_index(mars_facts_df.columns[0], inplace=True)
    mars_facts_df

    args_dct = {
        'header': False,
        'index_names': False,
        'border': 0,
        'justify': 'right',
        'classes': 'table table-striped table-sm small'
    }

    mars_facts_table = mars_facts_df.to_html(**args_dct)

    # Mars Hemispheres
    # =================

    progress.stage_start()
    steps_count = 5 # main page and 4 download pages
    current_step = 1
    
    mars_hemispheres_url = 'https://astrogeology.usgs.gov/search/results?q=hemisphere+enhanced&k1=target&v1=Mars'
    astrogeology_base_url = 'https://astrogeology.usgs.gov'

    progress.substage_start(current_step, steps_count)
    response = requests.get(mars_hemispheres_url)
    current_step += 1
    soup = BeautifulSoup(response.text, 'lxml')

    # First, iterate throught the list of hemispheres, read their names and urls to download pages
    hemisphere_image_urls = []
    item_nodes = soup.find_all('div', class_='item')
    for item_node in item_nodes:
        anchor_node = item_node.contents[0]
        download_url = astrogeology_base_url + anchor_node['href']

        header_node = anchor_node.find('h3')
        name = ' '.join(header_node.text.split(' ')[:-1])

        hemisphere_image_urls.append({
            'title': name,
            'download_page_url': download_url
        })

    # Secondly, load every image download page and retrieve image url
    for hemisphere_dct in hemisphere_image_urls:
        progress.substage_start(current_step, steps_count)
        current_step += 1

        time.sleep(1)
        response = requests.get(hemisphere_dct['download_page_url'])
        soup = BeautifulSoup(response.text, 'lxml')
        
        download_node = soup.find('div', class_='downloads')
        first_anchor = download_node.find('a')

        del hemisphere_dct['download_page_url']
        hemisphere_dct['img_url'] = first_anchor['href']

    # Finalize
    # =========

    progress.stage_start()
    browser.quit()

    return {
        'news_title': news_title,
        'news_para': news_para,
        'featured_image_url': featured_image_url,
        'featured_image_alt': featured_image_alt,
        'mars_weather': mars_weather,
        'mars_facts_table': mars_facts_table,
        'hemisphere_image_urls': hemisphere_image_urls
    }


# Function returns dictionary similar to the one from scrape() but without scraping
# The data in the dictionary is from actual scraping session performed with mission_to_mars.ipynb
def test():
    return {
        'news_title': "NASA's Perseverance Rover Will Look at Mars Through These 'Eyes'",
        'news_para': 'A pair of zoomable cameras will help scientists and rover drivers with high-resolution color images.',
        'featured_image_url': 'https://www.jpl.nasa.gov/spaceimages/images/wallpaper/PIA19113-1920x1200.jpg',
        'featured_image_alt': 'Martian Concretions Near Fram Crater',
        'mars_weather': 'InSight sol 508 (2020-05-01) low -92.2ºC (-134.0ºF) high -2.4ºC (27.7ºF) winds from the SW at 5.1 m/s (11.3 mph) gusting to 15.8 m/s (35.3 mph) pressure at 6.80 hPa',
        'mars_facts_table': '<table border="0" class="dataframe table table-striped table-sm small">\n  <tbody>\n    <tr>\n      <th>Equatorial Diameter:</th>\n      <td>6,792 km</td>\n    </tr>\n    <tr>\n      <th>Polar Diameter:</th>\n      <td>6,752 km</td>\n    </tr>\n    <tr>\n      <th>Mass:</th>\n      <td>6.39 × 10^23 kg (0.11 Earths)</td>\n    </tr>\n    <tr>\n      <th>Moons:</th>\n      <td>2 (Phobos &amp; Deimos)</td>\n    </tr>\n    <tr>\n      <th>Orbit Distance:</th>\n      <td>227,943,824 km (1.38 AU)</td>\n    </tr>\n    <tr>\n      <th>Orbit Period:</th>\n      <td>687 days (1.9 years)</td>\n    </tr>\n    <tr>\n      <th>Surface Temperature:</th>\n      <td>-87 to -5 °C</td>\n    </tr>\n    <tr>\n      <th>First Record:</th>\n      <td>2nd millennium BC</td>\n    </tr>\n    <tr>\n      <th>Recorded By:</th>\n      <td>Egyptian astronomers</td>\n    </tr>\n  </tbody>\n</table>',
        'hemisphere_image_urls': [
            {
                'title': 'Cerberus Hemisphere',
                'img_url': 'http://astropedia.astrogeology.usgs.gov/download/Mars/Viking/cerberus_enhanced.tif/full.jpg'
            },
            {
                'title': 'Schiaparelli Hemisphere',
                'img_url': 'http://astropedia.astrogeology.usgs.gov/download/Mars/Viking/schiaparelli_enhanced.tif/full.jpg'
            },
            {
                'title': 'Syrtis Major Hemisphere',
                'img_url': 'http://astropedia.astrogeology.usgs.gov/download/Mars/Viking/syrtis_major_enhanced.tif/full.jpg'
            },
            {
                'title': 'Valles Marineris Hemisphere',
                'img_url': 'http://astropedia.astrogeology.usgs.gov/download/Mars/Viking/valles_marineris_enhanced.tif/full.jpg'
            }
        ]
    }
    