#!/usr/bin/env python
import base64
import configparser
import subprocess
import sys
import textwrap
from typing import Any
import requests

# Fichero INI que contiene los parámetros del programa (mas editable que JSON)
INI_FILE = "config.ini"

DEFAULT_LOG_FILE = "out.log"

# Esto son los prompts en diferente idiomas.
prompts = {
    "es": """Si la imagen tiene {subject} responde exactamente con una sola palabra.
        Lás únicas respuestas válidas son OK o ERROR.""",
    "en": """If the image clearly contains {subject}, respond with exactly one word.
The only valid responses are OK or ERROR.""",
}

# El idioma de prompt a usar
DEFAULT_LANG = "en"

# Usando ollama en modo local. Usando API Generate. *NO* Chat
API_URL = "http://localhost:11434/api/generate"

# Tamaño mínimo ancho y/o alto para que el modelo pueda examinar
# la imagen de forma más rápida y eficiente
IMG_MIN_SIZE = 384

# Para presentación con colores por terminal (sin librerías externas)
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


class FileProcessingError(RuntimeError):
    """
    Definición de una excepción, esto facilita el código para mostrar el error
    con el nombre del fichero al intentar convertir la imagen con ffmpeg y el
    bucle de procesar los ficheros
    """

    def __init__(self, path: str, message: str):
        super().__init__(message)
        self.path = path


def image_to_base64_ffmpeg(path, size=IMG_MIN_SIZE) -> bytes:
    """
    Redimensiona la imagen con ffmpeg manteniendo la proporción y la devuelve en
    PNG codificado en base64.
    La conversión se hace por stdout para evitar archivos temporales.

    :param path: Ruta original
    :param size: fija el lado mínimo (ancho o alto) tras el reescalado
    :return: Imagen reducida y en formato de bytes
    :rtype: bytes
    """
    cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-i",
        path,
        "-vf",
        f"scale='if(gt(iw,ih),{size},-2)':'if(gt(ih,iw),{size},-2)'",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
        return base64.b64encode(proc.stdout).decode("ascii")
    except subprocess.CalledProcessError as e:
        # Error específico de procesamiento de imagen
        raise FileProcessingError(path, "ffmpeg failed") from e


def load_config(path: str = INI_FILE) -> configparser.ConfigParser:
    """
    Carga la configuración `config` a partir del fichero ini indicado.
    
    :param path: Fichero ini
    :type path: str
    :return: La configuración leída
    :rtype: ConfigParser
    """
    config = configparser.ConfigParser()
    if not config.read(path):
        raise FileNotFoundError(f"Config file not found: {path}".format(path=path))
    return config


def print_info(config: configparser.ConfigParser):
    """
    Tan sólo muestra por pantalla info sobre modelo, lenguaje, etc. usados

    :param config: La configuración del sistema
    :type config: configparser.ConfigParser
    """

    model = config.get("config", "model")
    lang = config.get("config", "lang", fallback="en")
    subject = config.get("config", "subject")
    print(f"Model: {model}. Lang: {lang}. Search: {subject}")

    #prompt = config.get("config", f"prompt {lang}", fallback=prompts[lang])
    #print(prompt)


def create_payload(config: configparser.ConfigParser) -> dict[str, Any]:
    """
    Genera el payload a partir de la configuración del fichero INI indicado

    :param config: El parser que ha leido el fichero ini
    :type config: configparser.ConfigParser
    :return: El payload que se envía a la API
    :rtype: dict[str, Any]
    """
    model = config.get("config", "model")
    prompt = get_prompt(config)

    payload = {
        "model": model,
        "temperature": 0.0,  # Menos invención, más determinista
        "top_p": 1.0,  # Opciones a elegir. Margen 0.8 - 1.0
        "prompt": prompt,
        "images": ["TODO"],  # Cambiará con cada llamada
        "stream": False,
    }
    return payload


def get_prompt(config: configparser.ConfigParser) -> str:
    """
    Extrae el prompt teniendo en cuenta el idioma y si hubiera un prompt definido
    en el config.
    
    :param config: El parser que ha leido el fichero ini
    :type config: configparser.ConfigParser
    :return: El prompt "saneado" y formateado
    :rtype: str
    """
    
    lang = config.get("config", "lang", fallback=DEFAULT_LANG)
    prompt_lang = f"prompt {lang}"

    # Comprobamos que haya un prompt definido para el idioma seleccionado
    # Se añade o modifica en prompts
    if config.has_option("config", prompt_lang):
        # Añadir o sobreescribir prompts.
        # Esto no es necesario ahora, pero está aquí por una posible ampliación
        prompts[lang] = prompt_lang

    # Si hay algún error añadiendo el idioma/prompt, se lecciona el prompt por defecto
    if lang in prompts:
        prompt = prompts[lang]
    else:
        prompt = prompts[DEFAULT_LANG]

    subject = config.get("config", "subject")

    # "Limpiamos" el texto. Necesario?
    prompt = prompt.format(subject=subject)
    prompt = textwrap.dedent(prompt).lstrip()
    return prompt


def classify_image(api_url: str, image_b64: bytes, payload: dict[str, Any]) -> str:
    """
    Devuelve la respuesta de clasifición para la imagen y el payload indicado

    :param image_b64: Imagen reducida en formato b64encode
    :param payload: El payload que se enviará a la API
    :return: La respuesta del servidor Ollama
    :rtype: str (debería ser "OK" o "ERROR")
    """
    # Inyectamos la imagen en el payload
    # FIXME: Para evitar data races, añadir mutex o crear copia. De momento no hay concurrencia
    payload["images"] = [image_b64]

    r = requests.post(api_url, json=payload, timeout=(5, None))
    r.raise_for_status()
    return r.json()["response"]


def main():

    # Primero comprobar que se ha usado argumentos de ficheros y no por stdin.
    files = sys.argv[1:]
    if not files:
        # La lectura se hace con a través de `find -exec` de la shell
        # list comprehension syntax nightmare... ;-)
        # if line.strip() --> Filtra lineas vacías o \n
        files = [line.strip() for line in sys.stdin if line.strip()]

    config = load_config("config.ini")
    api_url = config.get("config", "api url", fallback=API_URL)
    log = config.get("config", "log file", fallback=DEFAULT_LOG_FILE)

    payload = create_payload(config)
    print_info(config)

    with open(log, "w") as f:
        f.seek(0)
        f.truncate()
        for path in files:
            try:
                img_64 = image_to_base64_ffmpeg(path)
                result = classify_image(api_url, img_64, payload).upper().strip()
                match result:
                    case "OK":
                        color = GREEN
                        filename = path
                    case "ERROR":
                        color = RED
                        filename = ""
                    case _:  # Salida inesperada, ignorar o auditar: grep [-v] '^?'
                        color = YELLOW
                        filename = f"?{path}"

                print(f"{color}{path}{RESET}")
                if result != "ERROR":
                    print(filename, file=f)

            except FileProcessingError as e:
                print(f"Error processing {e.path}: {e}", file=sys.stderr)
                continue


if __name__ == "__main__":
    # Manejo elegante de excepciones, evitamos mostrar el traceback
    try:
        main()
    except FileNotFoundError as e:  # Referido a config.ini
        print(e)
        sys.exit(1)
    except KeyboardInterrupt as e:  # CTRL-C
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(2)
