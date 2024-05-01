import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
import asyncio

service = Service()
options = webdriver.ChromeOptions()
# options.add_experimental_option("detach", True)

words = pd.read_csv('./words.csv', converters={"IPA": str })
formatted_words = words.copy(deep=True)


async def get_definition_from_vocab(word):
    try:
        url = "https://www.vocabulary.com/dictionary/{}".format(word)
        browser = webdriver.Chrome(service=service, options=options)
        browser.get(url)
        
        # First Definition
        WebDriverWait(browser, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.word-definitions > ol > li:first-child > .definition')))
        
        html = browser.page_source
        soup = BeautifulSoup(html, 'html.parser')
        definition = soup.select_one('.word-area > p.short').text
        short_definition = re.sub('\s+', ' ', soup.select_one('.word-definitions > ol > li:first-child > .definition').text)
        words = short_definition.split()

        type = words[0]
        words.pop(0)

        browser.close()
        return [definition if len(definition) > 0 else ' '.join(words), type]
    except Exception as ex:
        print(ex)
        return [None, None]


async def main():
    for index, row in words.iterrows():
        if index == 1: break
        try:
            word = re.sub(r'[^A-Za-z0-9 ]+', '', row['ID'])
            word.replace(' ', '-')
            word_info = requests.get('https://cambridge-dictionary-api.vercel.app/api/dictionary/english/{}'.format(word), auth=('user', 'pass'))
            word_info = word_info.json()

            if word_info.get('error'): pass

            pronounces = word_info.get('pronunciation', None)

            pronounce = None
            if pronounces: 
                pronounce = next(x for x in pronounces if x["lang"] == "us" )
            if not pronounce and len(pronounces) > 0:
                pronounce = pronounces[0]

            first_definition = next((x for x in (word_info.get('definition', None) or []) if len(x['text']) > 10), None)
            definition, type = await get_definition_from_vocab(word)
            
            formatted_words.at[index, 'IPA'] = pronounce.get('url', '-')
            formatted_words.at[index, 'Class'] = type if definition != None else next(iter(pronounce.get('pos', '-') or []), None)
            formatted_words.at[index, 'ID'] = formatted_words.at[index, 'Word'] = word
            formatted_words.at[index, 'Definition'] = first_definition['text'] if definition == None else definition
            formatted_words.to_csv('./new_words.csv')

        except: pass
        
loop =  asyncio.new_event_loop()
loop.run_until_complete(main())
loop.close()