# Python script to automatically generate a route map for flea markets within a specified radius

## Context

Sabradou is a website listing flea markets in the north of France but it offers very limited functionality. You can’t filter or export a custom route for the flea markets you would like to visit.\
This script solves that by allowing you to input a starting town and a maximum search radius then generates a driving route to all nearby flea markets.

The generated map includes:
   * A route with markers at each flea market.
   * Clickable popups showing the town name and distance from your starting point.
   * A side panel detailing:
      * Each step in the order of visit.
      * Turn-by-turn driving instructions.
      * Key metrics such as total distance, estimated travel time and number of towns visited.

It uses OpenRouteService and Geopy for everything related to the route.

## Prerequisites
1. You will need to install the dependencies listed in requirements.txt
   ```
   pip3 install -r requirements.txt
   ```
3. You will need to create a .env file with your OpenRouteService API key.
   ```
   API_KEY =
   ```

## Usage

1. Git clone this repository.

2. You will need to specify your desired starting town and the maximum radius around it.\
   The following command will find all flea markets happening on Sunday, August 10, 2025 within a 40kms radius.\
   By default, Sabradou displays the next upcoming flea market. If you want to select a specific date, update the "url" at the beginning of the script with the URL corresponding to your desired date.
    ```bash
   $ python3 ./flea_markets_route.py "La Madeleine" 40
    
    Dimanche 10 Aout 2025 (mise à jour le 9/08/2025)
    => Data about the nearby flea markets has been successfully retrieved.
    => Route generated for 9 flea markets, total distance: 205.8 km, estimated time: 3.73 hours.
    Map saved to route.html
   ```
3. Open route.html
<table>
    <tr>
    <td valign="middle"><img width="900" alt="Capture d’écran du 2025-08-10 23-19-08" src="https://github.com/user-attachments/assets/a4b13525-3531-417c-8487-9c7cae7ad3b4" /></td>
    </tr>
</table>

## To do
* Finish optimization function









