import json
import logging
import os
import shutil

import requests
from concurrent.futures import ThreadPoolExecutor

LOG_FILE = "log.txt"
HEADER_BEARER = ""
RUTA_LIGAS = "mis_ligas/"
REQUEST_TIMEOUT = 30

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Origin': 'https://fantasy.laliga.com',
    'Referer': 'https://fantasy.laliga.com/',
    'X-App': 'Fantasy-web',
    'X-Lang': 'es'
}


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


def ask_league_id_bearer():
    global HEADER_BEARER
    print("Introduce tu token (Para mas info visitar \n"
          "https://github.com/alxgarci/marca-fantasy-api-scraper-updated )")
    HEADER_BEARER = str(input("Bearer Header: ")).replace("'", "")
    logging.info(f"Guardado Header '{HEADER_BEARER[0:12]}...'")


def read_leagues():
    url = "https://api-fantasy.llt-services.com/api/v4/leagues"
    league_ids_response = requests.get(url,
                                       auth=BearerAuth(HEADER_BEARER), headers=HEADERS, timeout=REQUEST_TIMEOUT)
    league_ids_payload = league_ids_response.json()
    logging.info(f"Request {url} OK")
    league_ids = []
    for x in league_ids_payload:
        league_ids.append(x["id"])

    return league_ids


def main():
    remove_files()
    create_base_dirs()
    ask_league_id_bearer()
    league_ids = read_leagues()
    for league_id in league_ids:
        read_market(league_id)
        read_players(league_id)


def read_market(league_id):
    url = f"https://api-fantasy.llt-services.com/api/v3/league/{league_id}/market"
    league_market_response = requests.get(url,
                                          auth=BearerAuth(HEADER_BEARER), timeout=REQUEST_TIMEOUT)
    league_market_payload = league_market_response.json()
    logging.info(f"Request {url} OK")
    write_json_ligas(league_market_payload, league_id)


def write_json_ligas(content, league_id):
    directory = f"{RUTA_LIGAS}{league_id}/"
    if not os.path.exists(directory):
        try:
            # Solucionar errores multithreading cuando dos hilos intentan crear un directorio simultaneamente
            os.mkdir(directory)
        except FileExistsError:
            logging.error(f"Error creando {directory} (Ya se ha creado)")
            pass

    filename = "market.json"
    with open(directory + filename, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4)

    logging.info(f"{directory}{filename} escrito correctamente")


def write_json_player_team(player_team_payload, league_id):
    directory = f"{RUTA_LIGAS}{league_id}/"
    if not os.path.exists(directory):
        try:
            # Solucionar errores multithreading cuando dos hilos intentan crear un directorio simultaneamente
            os.mkdir(directory)
        except FileExistsError:
            logging.error(f"Error creando {directory} (Ya se ha creado)")
            pass

    filename = f"{player_team_payload['manager']['id']}_{player_team_payload['manager']['managerName']}.json"
    with open(directory + filename, "w", encoding="utf-8") as f:
        json.dump(player_team_payload, f, indent=4)
    logging.info(f"{directory}{filename} escrito correctamente")


def get_player_team(player_id, league_id):
    url = f"https://api-fantasy.llt-services.com/api/v3/leagues/{league_id}/teams/{player_id}"
    player_team_response = requests.get(
        url,
        auth=BearerAuth(HEADER_BEARER), timeout=REQUEST_TIMEOUT)
    player_team_payload = player_team_response.json()
    logging.info(f"Request {url} OK")
    write_json_player_team(player_team_payload, league_id)


def read_players(league_id):
    url = f"https://api-fantasy.llt-services.com/api/v4/leagues/{league_id}/ranking?x-lang=es"
    league_players_response = requests.get(
        url,
        auth=BearerAuth(HEADER_BEARER), timeout=REQUEST_TIMEOUT)
    league_players_payload = league_players_response.json()
    logging.info(f"Request {url} OK")
    player_ids = []
    for player in league_players_payload:
        player_ids.append(player["team"]["id"])
    args = ((p, league_id) for p in player_ids)
    logging.info(f"Iniciando multithread para liga {league_id}")
    with ThreadPoolExecutor() as executor:
        for _ in executor.map(lambda p: get_player_team(*p), args):
            pass


def create_base_dirs():
    if not os.path.exists(RUTA_LIGAS):
        try:
            # Solucionar errores multithreading cuando dos hilos intentan crear un directorio simultaneamente
            os.mkdir(RUTA_LIGAS)
        except FileExistsError:
            logging.error(f"Error creando {RUTA_LIGAS} (Ya se ha creado)")
            pass


def remove_files():
    logging.info(f"Eliminando anteriores archivos ({RUTA_LIGAS})")
    if os.path.exists(RUTA_LIGAS):
        shutil.rmtree(RUTA_LIGAS)


if __name__ == '__main__':
    logging.basicConfig(filename=LOG_FILE, format="[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S", level=logging.INFO, filemode="w")
    console = logging.StreamHandler()
    formatter = logging.Formatter(fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logging.getLogger("").addHandler(console)
    logger = logging.getLogger(__name__)
    main()

else:
    logger = logging.getLogger(__name__)
