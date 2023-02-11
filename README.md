# Marca Fantasy Scraper
Web scraper del API de LaLiga Fantasy de Marca. Descarga la información existente en la Liga Fantasy Marca sobre los equipos y jugadores de la temporada.
Se ha implementado multithreading (es 4 veces más rapido) y comandos varios para poder modificar la ejecución sin cambiar nada del código en caso de modificaciones.

<!-- MarkdownTOC -->

- [Requisitos](#requisitos)
- [Uso](#uso)
- [Funcionamiento](#funcionamiento)
- [Referencias](#referencias)
- [Implementaciones pendientes](#implementaciones-pendientes)
- [Sugerencias y Errores](#sugerencias-y-errores)

<!-- /MarkdownTOC -->


# Requisitos
- Python v3 o más
- Librería requests en python

# Uso
- Para instalar el paquete requests, podemos hacerlo con `pip install -r requirements.txt`
- El programa se puede ejecutar con `python fantasy_scraper.py` o `python3 fantasy_scraper.py` o `py fantasy_scraper.py` con los ajustes establecidos por defecto
- Acepta algunos comandos al ejecutarlo, para más información `fantasy_scraper.py --help`
<div style="text-align: center;">
<img src="https://github.com/alxgarci/marca-fantasy-api-scraper-updated/raw/master/img/ex01.png"
     alt="Ejemplo comandos"
     height="200" />
</div>

# Funcionamiento
- Se creará un log.txt que registrará cada operación del programa para solución de errores
- Se almacena el .json de cada jugador en `players/IDEQUIPO_NOMBRECORTO/IDJUGADOR_NOMBRECORTO.json`
- Se crea un .json separado por cada equipo con sus jugadores y que guarda lo mismo que el jugadores pero sin estadisticas detalladas (minutos jugados,...), sólo con los puntos de cada jornada en `data/IDEQUIPO_NOMBRECORTO.json`

# Referencias
Este es un proyecto modificado a partir del de [diegoparrilla](https://github.com/diegoparrilla/marca-fantasy-scraper), sin su proyecto no hubiese sabido ni por donde empezar, y simplemente lo modifico ya que he visto que había dejado de darle soporte

# Implementaciones pendientes
- Permitir al usuario elegir entre .json y .csv

# Sugerencias y Errores
- Para errores/sugerencias escribir una nueva entrada en [issues](https://github.com/alxgarci/marca-fantasy-api-scraper-updated/issues/new)
- También revisaré los pull requests