import argparse
import datetime
import json
import os.path
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
import logging

import requests

RUTA_DATA = "data/"
RUTA_PLAYERS = "players/"
PLAYERS_ENDPOINT = "https://api.laligafantasymarca.com/api/v3/player"
LOG_FILE = "log.txt"
PROGRESS_BAR = False
TOTAL_JUGADORES = 1595

if os.path.isfile(LOG_FILE):
    os.remove(LOG_FILE)


# Configuracion de argumentos por consola para mostrar INFO o PROGRESSBAR
def check_totaljugadores_provided(value):
    ivalue = int(value)
    if not TOTAL_JUGADORES <= ivalue <= TOTAL_JUGADORES + 1000:
        raise argparse.ArgumentTypeError("%s no es un numero valido de jugadores" % value)
    return ivalue


parser = argparse.ArgumentParser(description=" Este programa usa multithread al llamar a la API y"
                                             " guardar los jugadores,"
                                             " puede consumir recursos pero lo convierte en mucho más eficiente."
                                             " Se guardara siempre un log en " + LOG_FILE,
                                 epilog="MarcaFantasy API Scraper de https://github.com/alxgarci")
parser.add_argument("--no-consolelog", action="store_false", dest="consolelog",
                    help="Mostrar progressBar en lugar de log en consola (default)")
parser.add_argument("--consolelog", action="store_true",
                    help="Mostrar log en consola en vez de progressBar")
parser.add_argument("--totaljugadores", type=check_totaljugadores_provided,
                    help=f"Seleccionar maximo de jugadores registrados en la API "
                         f"(entre {TOTAL_JUGADORES} (default) y {TOTAL_JUGADORES + 1000})")
parser.set_defaults(consolelog=False, totaljugadores=TOTAL_JUGADORES)
args = parser.parse_args()

# Configuracion del logging para guardar en log.txt o mostrar por consola en base a args
logging.basicConfig(filename=LOG_FILE, format="[%(asctime)s.%(msecs)03d] %(levelname)s - %(message)s",
                    datefmt="%H:%M:%S", level=logging.INFO)
TOTAL_JUGADORES = args.totaljugadores
if args.consolelog:
    console = logging.StreamHandler()
    formatter = logging.Formatter(fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logging.getLogger("").addHandler(console)
    logger = logging.getLogger(__name__)
else:
    PROGRESS_BAR = True
    logger = logging.getLogger(__name__)

teams_to_write = dict()


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


def get_formatted_time():
    return "[" + datetime.datetime.now().strftime("%H:%M:%S") + "]"


def append_to_team_object(team_filename, content):
    global teams_to_write
    filename = RUTA_DATA + team_filename + ".json"
    if filename not in teams_to_write.keys():
        teams_to_write[filename] = [content]
    else:
        teams_to_write[filename].append(content)


def write_player_json(filename_player, content):
    # sub_folder = f"{content['team']['id']}_{content['team']['shortName']}/"
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
    # print(f"[+] {get_formatted_time()} Jugador {player_id} guardado en {player_filename}")


def format_player_stats(payload):
    player_stats = [0 for _ in range(0, 38)]
    for jornada in payload["playerStats"]:
        player_stats[jornada["weekNumber"] - 1] = jornada["totalPoints"]
    return player_stats


def to_team_simple_json(player_id, payload):
    team_filename = f"{payload['team']['id']}_{payload['team']['shortName']}"
    # player_stats = dict()
    if payload["playerStatus"] != "out_of_league":
        # for jornada in payload["playerStats"]:
        #     week_numbers.append(jornada["weekNumber"])
        #     total_week_points.append(jornada["totalPoints"])
        #     player_stats.update({
        #         "weekNumber": week_numbers,
        #         "totalPoints": total_week_points
        #     })
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
    # if os.path.isfile(LOG_FILE):
    #     os.remove(LOG_FILE)


def multithread_scrape_player_aux(player_index):
    # for player_index in range(52, 1400):
    response = requests.get(f"{PLAYERS_ENDPOINT}/{player_index}")
    if response.status_code == 200:
        payload = response.json()
        try:
            check_if_team = payload["team"]["id"]
            to_player_json(player_index, payload)
            to_team_simple_json(player_index, payload)
            logger.info(f"Jugador {player_index} obtenido correctamente")
        except KeyError:
            # Es un jugador que no esta en 1 DIV, de equipo que ha descendido pero no se ha borrado
            logger.error(f"Jugador {player_index} [SIN EQUIPO]")
    elif response.status_code == 404:
        logger.error(f"Jugador {player_index} [NO ENCONTRADO]")


def main():
    remove_files()
    if not os.path.exists(RUTA_DATA):
        os.mkdir(RUTA_DATA)
    if not os.path.exists(RUTA_PLAYERS):
        os.mkdir(RUTA_PLAYERS)

    logging.info(f"API endpoint {PLAYERS_ENDPOINT}")

    if PROGRESS_BAR:
        print_progress_bar(0, TOTAL_JUGADORES, prefix='Progreso:', suffix='Jugadores obtenidos', length=70)
        counter = 52
        with ThreadPoolExecutor() as executor:
            for _ in executor.map(multithread_scrape_player_aux, range(52, TOTAL_JUGADORES)):
                counter = counter + 1
                print_progress_bar(counter, TOTAL_JUGADORES, prefix='Progreso:', suffix='Jugadores obtenidos',
                                   length=70)
    else:
        with ThreadPoolExecutor() as executor:
            executor.map(multithread_scrape_player_aux, range(52, TOTAL_JUGADORES))

    for x in teams_to_write.keys():
        logging.info(f"Escribiendo jugadores en {x}")
        with open(x, "w", encoding="utf-8") as f:
            json.dump(teams_to_write[x], f, indent=4)
    sys.exit()


if __name__ == '__main__':
    main()
