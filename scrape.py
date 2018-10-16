from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import pandas as pd

import time, re, csv, sys
import settings

RE_REMOVE_HTML = re.compile('<.+?>')

SLEEP_SECONDS = 3
WEEK = settings.week
# END_WEEK = 1
YAHOO_RESULTS_PER_PAGE = 25 # Static but used to calculate offsets for loading new pages
STATS_TYPE = settings.stats_type
PAGES_PER_WEEK = 10
teams = range(1,13)
all_teams = 'ALL'

#Projected versus actual
if STATS_TYPE == 'projected':
    base_url = 'https://football.fantasysports.yahoo.com/f1/%s/players?status=%s&pos=O&cut_type=9&stat1=S_PW_%d&myteam=0&sort=PR&sdir=1&count=%d'
else:
    base_url = 'https://football.fantasysports.yahoo.com/f1/%s/players?status=%s&pos=O&cut_type=9&stat1=S_W_%d&myteam=0&sort=AR&sdir=1&count=%d'

# Modify these as necessary based on league settings
fields = ['week', 'name', 'position', 'team', 'opp', 'bye_week',
    '{}_passing_yds'.format(STATS_TYPE),
    '{}_passing_tds'.format(STATS_TYPE),
    '{}_passing_int'.format(STATS_TYPE),
    '{}_rushing_att'.format(STATS_TYPE),
    '{}_rushing_yds'.format(STATS_TYPE),
    '{}_rushing_tds'.format(STATS_TYPE),
    '{}_receiving_tgt'.format(STATS_TYPE),
    '{}_receiving_rec'.format(STATS_TYPE),
    '{}_receiving_yds'.format(STATS_TYPE),
    '{}_receiving_tds'.format(STATS_TYPE),
    '{}_return_tds'.format(STATS_TYPE),
    '{}_twopt'.format(STATS_TYPE),
    '{}_fumbles'.format(STATS_TYPE),
    '{}_points'.format(STATS_TYPE),]

# TODO: Try to get these automatically
XPATH_MAP = {
    'name': 'td[contains(@class,"player")]/div/div/div[contains(@class,"ysf-player-name")]/a',
    'position': 'td[contains(@class,"player")]/div/div/div[contains(@class,"ysf-player-name")]/span',
    'opp': 'td//div[contains(@class,"ysf-player-detail")]/span',

    '{}_passing_yds'.format(STATS_TYPE): 'td[12]',
    '{}_passing_tds'.format(STATS_TYPE): 'td[13]',
    '{}_passing_int'.format(STATS_TYPE): 'td[14]',

    '{}_rushing_att'.format(STATS_TYPE): 'td[15]',
    '{}_rushing_yds'.format(STATS_TYPE): 'td[16]',
    '{}_rushing_tds'.format(STATS_TYPE): 'td[17]',

    '{}_receiving_tgt'.format(STATS_TYPE): 'td[18]',
    '{}_receiving_rec'.format(STATS_TYPE): 'td[19]',
    '{}_receiving_yds'.format(STATS_TYPE): 'td[20]',
    '{}_receiving_tds'.format(STATS_TYPE): 'td[21]',

    '{}_return_tds'.format(STATS_TYPE): 'td[22]',
    '{}_twopt'.format(STATS_TYPE): 'td[23]',
    '{}_fumbles'.format(STATS_TYPE): 'td[24]',
    '{}_points'.format(STATS_TYPE): 'td[8]',
    'bye_week': 'td[7]',
}

stats = []

def process_stats_row(stat_row, week):
    stats_item = {}
    stats_item['week'] = week
    for col_name, xpath in XPATH_MAP.items():
        stats_item[col_name] = RE_REMOVE_HTML.sub('', stat_row.find_element_by_xpath(xpath).get_attribute('innerHTML'))
    # Custom logic for team, position, and opponent
    stats_item['opp'] = stats_item['opp'].split(' ')[-1]
    team, position = stats_item['position'].split(' - ')
    stats_item['position'] = position
    stats_item['team'] = team
    return stats_item

def process_page(driver, week, cnt, team):
    print('Getting stats for week', week, 'count', cnt)

    url = base_url % (str(settings.YAHOO_LEAGUEID), team, week, cnt)
    driver.get(url)

    base_xpath = "//div[contains(concat(' ',normalize-space(@class),' '),' players ')]/table/tbody/tr"

    rows = driver.find_elements_by_xpath(base_xpath)

    stats = []
    for row in rows:
        stats_item = process_stats_row(row, week)
        stats.append(stats_item)

    print('Sleeping for', SLEEP_SECONDS)
    time.sleep(SLEEP_SECONDS)
    return stats

def login(driver):
    driver.get("https://login.yahoo.com/")

    username = driver.find_element_by_name('username')
    username.send_keys(settings.YAHOO_USERNAME)
    driver.find_element_by_id("login-signin").click()

    time.sleep(SLEEP_SECONDS)

    password = driver.find_element_by_name('password')
    password.send_keys(settings.YAHOO_PASSWORD)
    driver.find_element_by_id("login-signin").click()

def write_stats(stats, out):
    print('Writing to file', out)
    with open(out, 'w') as f:
        w = csv.DictWriter(f, delimiter=',', fieldnames=fields)
        w.writeheader()
        for row in stats:
            w.writerow(row)

def clean_csv(file_name):
    df = pd.read_csv(file_name)
    df.drop_duplicates(subset = None, inplace = True)
    df.to_csv(file_name)

def get_stats(outfile):
    driver = webdriver.Chrome('/Applications/Python 3.6/chromedriver')
    driver.set_page_load_timeout(30)

    print("Logging in")
    login(driver)

    time.sleep(SLEEP_SECONDS)

    stats = []

    for team in teams:
        for cnt in range(0, YAHOO_RESULTS_PER_PAGE, YAHOO_RESULTS_PER_PAGE):
            try:
                page_stats = process_page(driver, WEEK, cnt, team)
            except Exception as e:
                print('Failed to process page, sleeping and retrying', e)
                time.sleep(SLEEP_SECONDS * 5)
                page_stats = process_page(driver, WEEK, cnt)
            stats.extend(page_stats)

    for cnt in range(0, PAGES_PER_WEEK*YAHOO_RESULTS_PER_PAGE, YAHOO_RESULTS_PER_PAGE):
        try:
            page_stats = process_page(driver, WEEK, cnt, all_teams)
        except Exception as e:
            print('Failed to process page, sleeping and retrying', e)
            time.sleep(SLEEP_SECONDS * 5)
            page_stats = process_page(driver, WEEK, cnt)
        stats.extend(page_stats)

    write_stats(stats, outfile)
    clean_csv(outfile)
    driver.close()

if __name__ == '__main__':
    outfile = 'player_stats_2018_{}_week{}.csv'.format(STATS_TYPE ,WEEK)
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    get_stats(outfile)
