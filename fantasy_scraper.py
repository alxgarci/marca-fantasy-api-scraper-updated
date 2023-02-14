import argparse
import datetime
import json
import os.path
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
import logging
import numpy as np

import requests

RUTA_DATA = "data/"
RUTA_PLAYERS = "players/"
RUTA_MARKET_VALUES = "market_values/"
RUTA_MARKET_VALUES_JSON = RUTA_MARKET_VALUES + "values.json"
PLAYERS_ENDPOINT = "https://api.laligafantasymarca.com/api/v3/player"
LOG_FILE = "log.txt"
TOTAL_JUGADORES = 1595
INDEX_INICIO_API = 52
TEAMS_TO_WRITE = dict()
MARKET_VALUES_DICT = dict()


# Configuracion de argumentos por consola para mostrar INFO o PROGRESSBAR
def check_totaljugadores_provided(value):
    ivalue = int(value)
    if not TOTAL_JUGADORES <= ivalue <= TOTAL_JUGADORES + 1000:
        raise argparse.ArgumentTypeError(f"{value} no es un numero valido de jugadores, --help para mas info")
    return ivalue


# Definir parser y argumentos para los argumentos introducidos por consola
def set_parser(p):
    p.add_argument("--no-consolelog", action="store_false", dest="consolelog",
                   help="Mostrar progressBar en lugar de log en consola (default)")
    p.add_argument("--consolelog", action="store_true",
                   help="Mostrar log en consola en vez de progressBar")
    p.add_argument("--totaljugadores", type=check_totaljugadores_provided,
                   help=f"Seleccionar maximo de jugadores registrados en la API "
                        f"(entre {TOTAL_JUGADORES} (default) y {TOTAL_JUGADORES + 1000})")
    p.set_defaults(consolelog=False, totaljugadores=TOTAL_JUGADORES)
    # args = p.parse_args()
    return p.parse_args()


# Metodo muy util obtenido de:
# https://stackoverflow.com/a/34325723
def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        print_end    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


def append_to_team_object(team_filename, content):
    global TEAMS_TO_WRITE
    filename = RUTA_DATA + team_filename + ".json"
    if filename not in TEAMS_TO_WRITE.keys():
        TEAMS_TO_WRITE[filename] = [content]
    else:
        TEAMS_TO_WRITE[filename].append(content)


def write_player_json(filename_player, content):
    directory = f"{RUTA_PLAYERS}{content['team']['id']}_{content['team']['shortName']}/"
    if not os.path.exists(directory):
        try:
            # Solucionar errores multithreading cuando dos hilos intentan crear un archivo simultaneamente
            os.mkdir(directory)
        except FileExistsError:
            pass

    filename = f"{directory}{filename_player}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4)


def to_player_json(player_id, payload):
    player_filename = f"{player_id}_{payload['slug']}"
    write_player_json(player_filename, payload)


def format_player_stats(payload):
    # Jornada no disputada = NaN
    player_stats = [np.nan for _ in range(0, 38)]
    for jornada in payload["playerStats"]:
        player_stats[jornada["weekNumber"] - 1] = jornada["totalPoints"]
    return player_stats


def to_team_simple_json(player_id, payload):
    team_filename = f"{payload['team']['id']}_{payload['team']['shortName']}"
    if payload["playerStatus"] != "out_of_league":
        player_stats = format_player_stats(payload)
        player_simple_json = {
            "id": player_id,
            "status": payload["playerStatus"],
            "slug": payload["slug"],
            "position": payload['position'],
            "marketValue": payload["marketValue"],
            "playerStats": player_stats,
            "points": payload["points"],
            "averagePoints": payload["averagePoints"]
        }
        append_to_team_object(team_filename, player_simple_json)

    else:
        logger.error(f"Jugador {player_id} [out_of_league]")


def remove_files():
    logging.info(f"Eliminando anteriores archivos ({RUTA_DATA}, {RUTA_PLAYERS})")
    if os.path.exists(RUTA_DATA):
        shutil.rmtree(RUTA_DATA)
    if os.path.exists(RUTA_PLAYERS):
        shutil.rmtree(RUTA_PLAYERS)


def read_market_values_historial_json():
    global MARKET_VALUES_DICT
    if os.path.exists(RUTA_MARKET_VALUES_JSON):
        with open(RUTA_MARKET_VALUES_JSON, encoding="utf-8") as f:
            MARKET_VALUES_DICT = json.loads(f.read())
        logging.info(MARKET_VALUES_DICT)


def to_market_values_historial_json(player_index, mkt_value):
    global MARKET_VALUES_DICT
    p_index = str(player_index)
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    logging.info(f"p_index {p_index} - fecha: {date} = marketValue: {mkt_value}")

    # Escribir valor por primera vez
    if p_index not in MARKET_VALUES_DICT.keys():
        MARKET_VALUES_DICT[p_index] = {
            date: mkt_value
        }
    else:
        # Escribir si no se ha guardado ya un valor de marketValue en el dia actual
        if date not in MARKET_VALUES_DICT[p_index].keys():
            MARKET_VALUES_DICT[p_index].update({
                date: mkt_value
            })
            logging.info(MARKET_VALUES_DICT[p_index])


def multithread_scrape_player_aux(player_index):
    response = requests.get(f"{PLAYERS_ENDPOINT}/{player_index}")
    if response.status_code == 200:
        payload = response.json()
        try:
            _ = payload["team"]["id"]
            to_player_json(player_index, payload)
            to_market_values_historial_json(player_index, payload["marketValue"])
            to_team_simple_json(player_index, payload)
            logger.info(f"Jugador {player_index} obtenido correctamente")
        except KeyError:
            # Es un jugador que no esta en 1 DIV, de equipo que ha descendido pero no se ha borrado
            logger.error(f"Jugador {player_index} [SIN EQUIPO]")
    elif response.status_code == 404:
        logger.error(f"Jugador {player_index} [NO ENCONTRADO]")


def main(p_bar, total_jugadores):
    remove_files()
    if not os.path.exists(RUTA_DATA):
        os.mkdir(RUTA_DATA)
    if not os.path.exists(RUTA_PLAYERS):
        os.mkdir(RUTA_PLAYERS)
    if not os.path.exists(RUTA_MARKET_VALUES):
        os.mkdir(RUTA_MARKET_VALUES)

    logging.info(f"Leyendo MARKET_VALUES a dict() desde {RUTA_MARKET_VALUES_JSON}")
    read_market_values_historial_json()

    logging.info(f"API endpoint {PLAYERS_ENDPOINT}")

    if p_bar:
        print_progress_bar(0, total_jugadores, prefix='Progreso:', suffix='Jugadores obtenidos', length=70)
        counter = INDEX_INICIO_API
        with ThreadPoolExecutor() as executor:
            for _ in executor.map(multithread_scrape_player_aux, range(INDEX_INICIO_API, total_jugadores)):
                counter = counter + 1
                print_progress_bar(counter, total_jugadores, prefix='Progreso:', suffix='Jugadores obtenidos',
                                   length=70)
    else:
        with ThreadPoolExecutor() as executor:
            executor.map(multithread_scrape_player_aux, range(INDEX_INICIO_API, total_jugadores))

    for x in TEAMS_TO_WRITE.keys():
        logging.info(f"Escribiendo jugadores en {x}")
        with open(x, "w", encoding="utf-8") as f:
            json.dump(TEAMS_TO_WRITE[x], f, indent=4)

    with open(RUTA_MARKET_VALUES_JSON, "w", encoding="utf-8") as f:
        logging.info(f"Escribiendo MARKET_VALUES_DICT en {RUTA_MARKET_VALUES_JSON}")
        json.dump(MARKET_VALUES_DICT, f, indent=4)

    sys.exit()


if __name__ == '__main__':
    # # Eliminar anterior log
    # if os.path.isfile(LOG_FILE):
    #     os.remove(LOG_FILE)

    # Configuracion del logging para guardar en log.txt o mostrar por consola en base a args
    logging.basicConfig(filename=LOG_FILE, format="[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s",
                        datefmt="%H:%M:%S", level=logging.INFO, filemode="w")

    description = "Este programa usa multithread al llamar a la API y guardar los jugadores en .JSON, " \
                  "lo convierte en más eficiente. Se guardara siempre un log en " + LOG_FILE
    epilog = "MarcaFantasy API Scraper de https://github.com/alxgarci"
    parser = argparse.ArgumentParser(description=description, epilog=epilog)

    # Obteniendo args pasados por consola y estableciendo variables
    args = set_parser(parser)
    tot_jugadores = args.totaljugadores
    progress_bar = False
    if args.consolelog:
        console = logging.StreamHandler()
        formatter = logging.Formatter(fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)
        logging.getLogger("").addHandler(console)
        logger = logging.getLogger(__name__)
    else:
        progress_bar = True
        logger = logging.getLogger(__name__)

    main(progress_bar, tot_jugadores)
