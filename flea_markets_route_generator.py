import requests
import lxml
import json
import openrouteservice
import os
import folium
import sys
import re

from dotenv import load_dotenv
from lxml import html
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from jinja2 import Environment, FileSystemLoader

load_dotenv()
URL = "http://www.sabradou.com"

def get_flea_markets():
    """
    Parses the request data from sabradou website and returns a list of dicts of each flea market.

    Returns:
        results_flea_markets: town, type_flea_market, url
    """
  
    response = requests.get(URL)
    if response.status_code == 200:
        parsed_content = html.fromstring(response.text)
        results_flea_markets = []

        all_flea_markets = parsed_content.xpath('//div[@class="deptardt"]') + parsed_content.xpath('//div[@class="dept"]')
        date = parsed_content.xpath('//h2[@id="datejour"]')
        date = date[0].text_content().strip()

        for flea_market in all_flea_markets:
            towns = flea_market.xpath('.//ul/li/a')
            type_flea_markets = flea_market.xpath('.//ul/li/a/@title')
            urls = flea_market.xpath('.//ul/li/a/@href')

            for town, type_flea_market, url in zip(towns, type_flea_markets, urls):
                if not url.startswith("http://www.sabradou.com"):
                    print("Suspect URL detected, moving to the next flea market")
                    continue

                results_flea_markets.append({
                    "town": town.text_content(),
                    "type_flea_market": type_flea_market,
                    "URL": url
                })
        return results_flea_markets, date
    else:
        logging.error("An error occured while loading the page, the scripts stops.")
        sys.exit(1)

def get_location_flea_markets(flea_markets, date):
    """
    Parses data from each flea market URL recovered and returns a list of dicts of the town and location of each flea market.
    Returns:
        results_locations: town, location_flea_market
    """
  
    results_locations = []
    type_location = ["centre","rue","quartier","place","digue","plage","parking","route","pature","salle","avenue","hameau","boulevard","chemin","stade"]
    location_already_seen = set()
    for flea_market in flea_markets:
        url_flea_market = flea_market["URL"]
        response = requests.get(url_flea_market)
        
        if response.status_code == 200:
            response = response.text
            parsed_content = html.fromstring(response)
            chineur_column = parsed_content.xpath('//div/ul[@class="ville-colonne"][2]')
            for description in chineur_column:
                all_li = description.xpath('.//li')

                for element_li in all_li:
                    text = list(element_li.itertext())
                    location_found = False
                    for line in text:
                        for word in type_location:
                            if word in line.lower():
                                location_found = True
                                break  
                        if location_found:
                            key = (flea_market["town"])
                            if key not in location_already_seen:
                                results_locations.append({"town": flea_market["town"], "location_flea_market": line })
                                location_already_seen.add(key)
    print(date)                            
    print("=> Data about the nearby flea markets has been successfully retrieved")
    return results_locations
                    
def distance_towns(flea_markets, start_town, radius):
    """
    Caculates the distance between the flea markets and the desired town specified by the user within a certain radius.
    Returns:
        coords_start_town, flea_markets_within_radius
    """
  
    geolocator = Nominatim(user_agent="geopy", timeout=5)
    try:
        coords_start_town = geolocator.geocode(start_town + ', France')
        coords_start_town = [coords_start_town.longitude, coords_start_town.latitude]
    except Exception as e:
        print("Could not use geocode for ", start_town)
        sys.exit(1)

    flea_markets_within_radius = []

    for flea_market in flea_markets:
        coords_flea_market = geolocator.geocode(flea_market['location_flea_market'] + ", " + flea_market['town'] + ", France")
        if coords_flea_market == None:
            coords_flea_market = geolocator.geocode(flea_market['town'] + ", France")

        if coords_flea_market:
            distance_km = geodesic((coords_start_town[1], coords_start_town[0]), (coords_flea_market.latitude, coords_flea_market.longitude)).km
            if distance_km < radius:
                flea_market["coords"] = [coords_flea_market.longitude, coords_flea_market.latitude]
                print("Distance between", start_town, "and", flea_market["town"], ":", round(distance_km, 2), "kms")
                flea_markets_within_radius.append(flea_market)        
    return coords_start_town, flea_markets_within_radius

def get_trajet(flea_markets, coords_start_town, start_town, date):
    """
    Generates a .html route page to visit the various flea markets by car.
    The route contains markers and an information panel including instructions.
    """
  
    API_KEY = os.getenv("API_KEY")
    client = openrouteservice.Client(key=API_KEY)

    steps = [coords_start_town]
    for flea_market in flea_markets:
        steps.append(flea_market["coords"])
    steps.append(coords_start_town)

    try:
        route = client.directions(steps, profile='driving-car', format='geojson', instructions=True, language='fr')
    except openrouteservice.exceptions.ApiError as e:
        print("Could not generate directions")
        sys.exit(1)

    total_distance_km = round(route['features'][0]['properties']['summary']['distance'] / 1000, 2)
    total_time_hr = round(route['features'][0]['properties']['summary']['duration'] / 3600, 2)
    segments = route['features'][0]['properties']['segments']
    nb_flea_markets = len(flea_markets)

    distance_step = []
    time_step = []
    total = 0
    total_time_seconds = 0

    for i in range(nb_flea_markets):
        distance_segment = segments[i]['distance']
        duration_segment = segments[i]['duration']
        total += distance_segment
        total_time_seconds += duration_segment
        distance_step.append(round(total / 1000, 1))
        time_step.append(int(total_time_seconds))

    route_map = folium.Map(location=[coords_start_town[1], coords_start_town[0]], zoom_start=12)
    print("=> Route generated for " + str(nb_flea_markets) + " flea markets, total distance: " + str(total_distance_km) + " km, estimated time: " + str(total_time_hr) + " hours")

    add_markers_and_route(route_map, flea_markets, coords_start_town, steps, distance_step, start_town, route, total_distance_km)

    render_template(route_map, flea_markets, distance_step, time_step, total_distance_km, total_time_hr, nb_flea_markets, route, start_town, date)

def add_markers_and_route(route_map, flea_markets, coords_start_town, steps, distance_step, start_town, route, total_distance_km):
    """
    Add the steps markers using CSS and HTML.
    """
  
    folium.GeoJson(route, name="Itinéraire").add_to(route_map)

    #Start town label
    folium.map.Marker(
        [coords_start_town[1], coords_start_town[0]], icon=folium.DivIcon(
            html=f"""<div style="
                font-weight: bold;
                font-size: 12px;
                color: black;
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid D6D6D6;
                border-radius: 4px;
                padding: 2px;
                text-align: center;
                white-space: nowrap;
                transform: translateY(-240%);
                display: inline-block;
                ">Départ – {start_town}</div>"""
        )
    ).add_to(route_map)

    #Start/Destination town marker
    folium.Marker(
        [coords_start_town[1], coords_start_town[0]], icon=folium.Icon(color="green", icon="flag-checkered"), popup=start_town + " – " + str(total_distance_km) + " km"
    ).add_to(route_map)

    #Steps label
    step_index = 1
    for flea_market in flea_markets:
        coords = steps[step_index]
        town = flea_market['town']
        distance_km = distance_step[step_index - 1]

        label = "Étape " + str(step_index) + " – " + town
        popup_text = town + " – " + str(distance_km) + " km"

        folium.map.Marker(
            [coords[1], coords[0]], icon=folium.DivIcon(
                html=f"""<div style="
                    font-weight: bold;
                    font-size: 12px;
                    color: black;
                    background-color: rgba(255, 255, 255, 0.8);
                    border: 1px solid D6D6D6;
                    border-radius: 2px;
                    padding: 2px;
                    text-align: center;
                    white-space: nowrap;
                    transform: translateY(-240%);
                    text-shadow: 
                        -0.5px -0.5px 0 white,
                        0.5px -0.5px 0 white,
                        -0.5px 0.5px 0 white,
                        0.5px 0.5px 0 white;
                    display: inline-block;
                    ">{label}</div>"""
            )
        ).add_to(route_map)

        #Steps marker
        folium.Marker(
            [coords[1], coords[0]], icon=folium.Icon(color="blue", icon="map-marker"), popup=popup_text
        ).add_to(route_map)
        step_index += 1

def render_template(route_map, flea_markets, distance_step, time_step, total_distance_km, total_time_hr, nb_flea_markets, route, start_town, date):
    """
    Renders the HTML map using the markers and route map.
    """

    #HTML route render
    html_map = route_map._repr_html_()

    html_instructions = ""
    for segment in route['features'][0]['properties']['segments']:
        for step in segment['steps']:
            html_instructions += "• " + step['instruction'] + " – " + str(round(step['distance'] / 1000, 2)) + " km<br>"

    formatted_durations = []
    for total_sec in time_step:
        heures = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        formatted_durations.append(str(heures) + "h" + "{:02d}".format(minutes))

    #Jinja2 template
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("template.html")
    jinja_rendered = template.render(
        html_map=html_map,
        flea_markets=flea_markets,
        total_distance_km=total_distance_km,
        formatted_durations=formatted_durations,
        total_time_hr=total_time_hr,
        html_instructions=html_instructions,
        start_town=start_town,
        nb_flea_markets = nb_flea_markets,
        date = date,
        distance_step = distance_step
    )

    with open("route.html", "w", encoding="utf-8") as f:
        f.write(jinja_rendered)

    print("Map saved to route.html")

def main():
    if len(sys.argv) != 3:
        print("Expected 2 arguments:")
        print("Usage: python flea_markets_route.py string:<start_town> int:<radius_in_km>")
        sys.exit(1)
    elif not re.match(r'^[a-zA-Z\s-]+$', sys.argv[1]):
        print("Invalid town name")
        sys.exit(1)
    elif int(sys.argv[2]) <= 0:
        print("The radius must be a positive integer")

    start_town = sys.argv[1].strip()
    radius = int(sys.argv[2].strip())

    data_flea_markets, date = get_flea_markets()
    location_flea_markets = get_location_flea_markets(data_flea_markets, date)
    coords_start_town, filtered_flea_markets = distance_towns(location_flea_markets, start_town, radius)
    get_trajet(filtered_flea_markets, coords_start_town, start_town, date)

if __name__ == '__main__':
    main()
