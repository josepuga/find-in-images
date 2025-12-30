# find-in-images

Un script en python que permite buscar imágenes con un determinado contenido.

El script no indexa ni busca por metadatos; cada imagen se evalúa individualmente mediante un modelo visual.

## Requisitos

- Tener acceso a un `servidor ollama`, ya sea localhost o remoto.
- Tener disponible un `modelo visual` en ollama capaz de procesar imágenes.
- `ffmpeg` instalado, se encarga de reducir las imágenes antes de procesarlas.

## Cómo usar (vía rápida)

Antes de ejecutarlo, debemos editar el fichero `config.ini` y modificar sobre todo estos 2 valores:

```ini
model = qwen3-vl:8b
subject = un chihuahua
lang = es
```

En `model`, debes poner un modelo visual que tengas instalado en ollama.

En `subject` pon lo que quieras buscar, asegúrate de que coincida el idioma `lang` con la búsqueda

Lanzamos el programa con `python find-in-images.py <fichero1> <...> <ficheroN>` ó usando máscara `test-chihuahua-muffin/*` como en el ejemplo.

![Chihuaha-Muffin test](doc/test-chihuahua.png "Chihuahua-Muffin test")

Las imágenes que cumplan la condición se mostrarán en el fichero `out.log` (nombre por defecto). Si el modelo hubiera tenido una respuesta ambigua, los ficheros contendrán una `?` al principio.

Por pantalla las que cumplan la condición aparecerán en verde, las que no, en rojo y las que el modelo devuelva una respuesta ambigua, en amarillo.

## Cómo usar (vía avanzada)

### Cambio de prompt

Si el prompt que hay por defecto no te funcionara, o quisieras usar otro idioma, puedes añadir el tuyo propio en la key `prompt XX =` del `config.ini` donde `XX` es el código de idioma. Tienes un ejemplo en dicho fichero.

### Procesar una lista de ficheros

Si ya tienes una lista de ficheros, puedes usarla para que `find-in-images` las procese.

```bash
cat your-file-list.txt | python find-in-images.py
```

### Usando linux find

La herramienta más poderosa es usar find para localizar todas la imágenes de un determinado directorio y subdirectorios.

```bash
find /your/path -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \) | python find-in-images.py
```

## Limitaciones conocidas

- No es determinista al 100 %
- Modelos grandes pueden ser lentos
- El tiempo de ejecución depende del modelo y de si se usa CPU o GPU.
- El resultado depende fuertemente del prompt

## Licencia

Este código está bajo GPL3.
