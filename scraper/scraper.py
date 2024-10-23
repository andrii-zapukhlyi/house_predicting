import asyncio, aiohttp, re, pandas as pd, numpy as np
from bs4 import BeautifulSoup

## Take all cities and villages in the Poland from the file
df = pd.read_csv('PL_locations.txt', sep='\t', usecols=[1,3,7], header=None, names = ['name', 'alternatenames', 'feature code'])
feature_codes = ['ADM1', 'ADM2', 'ADM3', 'PPLC', 'PPLA', 'PPLA2', 'PPLA3']
filtered_df = df[df['feature code'].isin(feature_codes)]
city_names = filtered_df['name'].tolist()
alternate_names = filtered_df['alternatenames'].str.split(',', expand=True).stack().tolist()
cities_villages = city_names + alternate_names
voivodships = [
    'dolnośląskie',
    'kujawsko-pomorskie',
    'lubelskie',
    'lubuskie',
    'łódzkie',
    'małopolskie',
    'mazowieckie',
    'opolskie',
    'podkarpackie',
    'podlaskie',
    'pomorskie',
    'śląskie',
    'świętokrzyskie',
    'warmińsko-mazurskie',
    'wielkopolskie',
    'zachodniopomorskie'
]


## Links for scraping
base_url = "https://www.otodom.pl"
url_template = "https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie%2Crynek-wtorny/cala-polska?limit=72&page={}"

## You need to switch between proxy servers to scrape data

#proxies = ["https://ip:port",
#           "https://ip:port"]

async def fetch(session, url):
    headers = {
        'authority': 'www.google.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-full-version': '"115.0.5790.110"',
        'sec-ch-ua-full-version-list': '"Not/A)Brand";v="99.0.0.0", "Google Chrome";v="115.0.5790.110", "Chromium";v="115.0.5790.110"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': 'Windows',
        'sec-ch-ua-platform-version': '15.0.0',
        'sec-ch-ua-wow64': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'x-client-data': '#..',
    }
    async with session.get(url, headers=headers) as response:
        return await response.text()

## Find page count at the moment to parse all offers from the platform
async def get_page_count(session):
    page_content = await fetch(session, url_template.format(1))
    soup = BeautifulSoup(page_content, 'html.parser')
    jump_forward = soup.find('li', attrs={'type': 'JUMP_FORWARD'})
    next_sibling = jump_forward.find_next_sibling()
    return int(next_sibling.text)

## Scrape all links including 'ofers' in href 
async def scrape_links(session, page):
    page_content = await fetch(session, url_template.format(page))
    soup = BeautifulSoup(page_content, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True) if '/oferta/' in a['href']]
    return links

## Parse the data from a specific offer
async def scrape_data(session, link):
    full_url = base_url + link
    page_content = await fetch(session, full_url)
    soup = BeautifulSoup(page_content, 'html.parser')
    
    try:
        # Check is advertisement expired
        expired = soup.find(attrs={"data-cy": "expired-ad-alert"})
        if expired:
            return
        
        # Initialize variables
        location = voivodship = area = ownership = rooms = floor = outdoor_space = rent = parking = heating = advertiser = construction_year = building = elevator = price = np.nan

        # Take the whole address string and extract city and voivodship from it 
        address = soup.find(attrs={"aria-label": "Adres"})
        if address:
            address = address.get_text(strip=True)
            words = address.split(', ')
            location = None
            for word in words:
                if word in cities_villages:
                    location = word
                if word in voivodships:
                    voivodship = word

        # Parse area
        area_children = soup.find(attrs={"aria-label": "Powierzchnia"})
        if area_children:
            area_children = area_children.findChildren()
            area = area_children[len(area_children)-1].get_text(strip = True)
            if area == "Zapytaj":
                area = np.nan
            else:
                area = float("".join(re.findall(r'\d+[\.,]?\d*', area)).replace(",", ".").replace(" ", ""))

        # Parse ownership form
        ownership_children = soup.find(attrs={"aria-label": "Forma własności"})
        if ownership_children:
            ownership_children = ownership_children.findChildren()
            ownership = ownership_children[len(ownership_children)-1].get_text(strip = True)
            if ownership == "Zapytaj":
                ownership = np.nan

        # Parse number of rooms 
        rooms_children = soup.find(attrs={"aria-label": "Liczba pokoi"})
        if rooms_children:
            rooms_children = rooms_children.findChildren()
            rooms = rooms_children[len(rooms_children)-1].get_text(strip = True)
            if rooms == "Zapytaj":
                rooms = np.nan
            elif rooms == "więcej niż 10":
                rooms = 11
            else:
                rooms = int(rooms)

        # Parse floor
        floor_children = soup.find(attrs={"aria-label": "Piętro"})
        if floor_children:
            floor_children = floor_children.findChildren()
            floor = floor_children[len(floor_children)-1].get_text(strip = True)
            if floor == "Zapytaj":
                floor = np.nan
            elif "parter" in floor:
                floor = 0
            elif "suterena" in floor:
                floor = -1
            elif "poddasze" in floor:
                if "/" in floor:
                    floor = int(floor.split('/')[1])
                else:
                    floor = np.nan
            else: 
                if "/" in floor:
                    floor = int(floor.split('/')[0].replace(">", "").replace("<", ""))
                else:
                    floor = int(floor.replace(">", "").replace("<", ""))
        
        # Parse outdoor space
        outdoor_space_children = soup.find(attrs={"aria-label": "Balkon / ogród / taras"})
        if outdoor_space_children:
            outdoor_space_children = outdoor_space_children.findChildren()
            outdoor_space = outdoor_space_children[len(outdoor_space_children)-1].get_text(strip = True)
            if outdoor_space == "Zapytaj":
                outdoor_space = "none"

        # Parse rent
        rent_children = soup.find(attrs={"aria-label": "Czynsz"})
        if rent_children:
            rent_children = rent_children.findChildren()
            rent = rent_children[len(rent_children)-1].get_text(strip = True)
            if rent == "Zapytaj":
                rent = 0
            elif "EUR" in rent:
                rent = 4.3*float(rent.replace("EUR", "").replace(" ", "").replace(",", "."))      
            else:
                rent = float(rent.replace("zł", "").replace(" ", "").replace(",", "."))

        # Parse parking
        parking_children = soup.find(attrs={"aria-label": "Miejsce parkingowe"})
        if parking_children:
            parking_children = parking_children.findChildren()
            parking = parking_children[len(parking_children)-1].get_text(strip = True)
            if parking == "Zapytaj":
                parking = 0
            else:
                parking = 1

        # Parse heating type
        heating_children = soup.find(attrs={"aria-label": "Ogrzewanie"})
        if heating_children:
            heating_children = heating_children.findChildren()
            heating = heating_children[len(heating_children)-1].get_text(strip = True)
            if heating == "Zapytaj":
                heating = np.nan

        # Parse advertiser
        advertiser_chlidren = soup.find(attrs={"aria-label": "Typ ogłoszeniodawcy"})
        if advertiser_chlidren:
            advertiser_chlidren = advertiser_chlidren.findChildren()
            advertiser = advertiser_chlidren[len(advertiser_chlidren)-1].get_text(strip = True)
            if advertiser == "brak informacji":
                advertiser = np.nan

        # Parse construction year
        construction_year_chlidren = soup.find(attrs={"aria-label": "Rok budowy"})
        if construction_year_chlidren:
            construction_year_chlidren = construction_year_chlidren.findChildren()
            construction_year = construction_year_chlidren[len(construction_year_chlidren)-1].get_text(strip = True)
            if construction_year == "brak informacji":
                construction_year = np.nan
            else:
                construction_year = int(construction_year)

        # Parse building type
        building_children = soup.find(attrs={"aria-label": "Rodzaj zabudowy"})
        if building_children:
            building_children = building_children.findChildren()
            building = building_children[len(building_children)-1].get_text(strip = True)
            if building == "brak informacji":
                building = np.nan
        
        #Parse elevator
        elevator_children = soup.find(attrs={"aria-label": "Winda"})
        if elevator_children:
            elevator_children = elevator_children.findChildren()
            elevator = elevator_children[len(elevator_children)-1].get_text(strip = True)
            if elevator == "brak informacji":
                elevator = np.nan
            else:
                if elevator == "tak":
                    elevator = 1
                else: 
                    elevator = 0

        # Parse price
        price = soup.find(attrs={"aria-label": "Cena"})
        if price:
            price = price.get_text(strip=True)
            if price == "Zapytaj o cenę":
                price = np.nan
            elif "EUR" in price:
                price = 4.3*float(price.replace("EUR", "").replace(" ", "").replace(",", "."))
            else:
                price = float(price.replace("zł", "").replace(" ", "").replace(",", "."))
    
    ## Offer link with error
    except Exception as e:
        print("Link:", full_url)
        print("Error:", e)
        return None
    
    return {
        'location': location,
        'voivodship': voivodship,
        'area': area,
        'ownership': ownership,
        'rooms': rooms,
        'floor': floor,
        'outdoor_space': outdoor_space,
        'rent': rent,
        'parking': parking,
        'heating': heating,
        'advertiser': advertiser,
        'construction_year': construction_year,
        'building': building,
        'elevator': elevator,
        'price': price
    }

async def main(): 
    async with aiohttp.ClientSession() as session:
        all_data = pd.DataFrame()
        page_count = await get_page_count(session)
        tasks = [scrape_links(session, page) for page in range(1, page_count)] 
        results = await asyncio.gather(*tasks)
        all_links = list(set(link for sublist in results for link in sublist))
        tasks = [scrape_data(session, link) for link in all_links]
        data_results = await asyncio.gather(*tasks)
        page_df = pd.DataFrame(data_results)
        all_data = pd.concat([all_data, page_df], ignore_index=True)
        all_data.to_csv("data1.csv", index=False)

asyncio.run(main())