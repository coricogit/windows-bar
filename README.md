# Barra de temas

Barra de tareas para Windows 11 con 6 temas y Claudito. Reemplaza a la de Windows sin cambiar archivos del
sistema ni inyectar código: solo la oculta mientras está abierta.

## Instalar

Necesita Windows 11 de 64 bits; no pide administrador y trae Python y Qt. Se desinstala desde *Configuración > Aplicaciones*.

**Con Smart App Control activado**, o si lo prefieres, en PowerShell:

```powershell
irm https://raw.githubusercontent.com/coricogit/windows-bar/main/instalar.ps1 | iex
```

**Con el instalador**: `Windows-Bar-Setup-<versión>.exe` de
[Releases](https://github.com/coricogit/windows-bar/releases/latest). No está firmado: Smart App Control lo bloquea, y sin él
Windows puede avisar (*Más información > Ejecutar de todas formas*).

Las dos dejan lo mismo. Lo que se ejecuta después va firmado por sus autores (Python y Qt). La copia instalada se actualiza
sola: mira este repositorio cada pocas horas, comprueba la descarga y la instala cuando llevas un par de minutos sin tocar el
equipo. Si falla, vuelve la versión anterior. Se quita en el menú (*Actualizar sola*).

Claudito sale en los equipos con Claude Code. Usa el [instalado](https://github.com/coricogit/claudito) o el de
`~/src/claudito`; si no hay, el que trae la barra: para que vea tus sesiones y límites, *Conectar Claude Code* en el menú.

Desde el código: `py -m pip install PySide6_Essentials`, y después

- **Abrir:** `Iniciar barra.bat` (o *Windows Bar* en el menú Inicio)
- **Cerrar:** clic derecho en el reloj → *Salir y volver a la barra de Windows*
- **Emergencia:** `Ctrl+Alt+Mayús+B`, o `Restaurar barra de Windows.bat`

## Uso

| Dónde | Qué hace |
|---|---|
| Reloj, volumen o un hueco | Clic derecho: menú de temas y ajustes |
| Programa | Pasar el ratón: vista previa de todas sus ventanas · Clic: activar o minimizar (con varias, elegir) · Rueda: su volumen (si tiene sonido abierto; si no, o con Mayús, pasar de una ventana a otra) · Clic central: abrir otra · Clic derecho: menú con su lista de saltos (tareas y recientes) · Arrastrar: cambiar de sitio · Soltar archivos encima: se abren con él (un momento encima: su ventana pasa delante) |
| Volumen | Con la red y la batería al lado · Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio |
| Reloj | Clic: calendario del tema · Clic central: notificaciones · A su lado, el temporizador en marcha (clic: quitarlo) |
| Bandeja | Micrófono naranja: algún programa lo está usando (pasar el ratón: cuál; clic: privacidad) · Clic central en un icono: guardarlo tras la flecha o sacarlo (también en el menú) · Clic en la flecha: ver los ocultos |
| Inicio | Clic: menú Inicio · Clic derecho: menú Win+X · Clic central: buscador · Rueda: pasar de tema |

Ajustes en `%LOCALAPPDATA%\barra-temas\ajustes.json`: tema por hora (`auto`, `tema_dia`, `tema_noche`, `dia`,
`noche`), por programa (`"por_programa": {"steam.exe": "tokyo"}`) y `modo_juego`. Errores en `barra.log`, al lado
(ver [Si se cae](#si-se-cae)).

## Atajos de teclado

| Atajo | Qué hace |
|---|---|
| Win+1…0 | Abrir, traer al frente o minimizar ese botón; con varias ventanas, pasar de una a otra |
| Win+Mayús+1…0 | Abrir otra ventana (con Ctrl, como administrador) |
| Win+Ctrl+1…0 | Ir a su última ventana |
| Win+Alt+1…0 | Su menú |
| Win+T · Win+B | Elegir un botón · un icono de la bandeja. Flechas para moverse, Intro, Esc, tecla Menú |
| Alt+Espacio | El buscador (ver abajo) |

Los demás (Win+A, N, S, X, W, E…) son de Windows y siguen igual. El proceso que los atiende solo intercepta teclas con
Windows pulsada o eligiendo con las flechas, y descansa en modo juego. Con una ventana de administrador delante no llegan.

## Buscador

El campo «Buscar» junto a Inicio, Alt+Espacio o clic central en Inicio: escribe y pulsa Intro. En las barras estrechas
(compacta, vertical, dock, burbujas) el campo es solo una lupa; se quita en *Funciones → Barra de búsqueda junto a Inicio*. Busca en las aplicaciones del menú Inicio (también las de
la Tienda y los juegos de Steam), en las páginas de Configuración (también por palabras: «volumen» da Sonido) y hace
cuentas (`2*(3+4)`, `15% de 80`, `sqrt(2)`; Intro copia el resultado). La última fila busca el texto en tus archivos con
el Explorador. También lleva a las ventanas abiertas (por programa o por título: «disc» → tu Discord, antes que
abrir otro) y pone temporizadores: «5 min», «temporizador 10», «1h 30m», «pomodoro» (25 min y 5 de descanso; con otros minutos:
«pomodoro 50» o «pomodoro 50/10», y se quedan para la próxima vez; también en *Funciones → Pomodoro*). El que
está en marcha sale junto al reloj y al acabar avisa con un sonido y en la isla. Sin texto enseña las que más abres. Todo es local. Flechas o Tab para moverse, Esc para cerrar.
El atajo es `RegisterHotKey` (sin gancho de teclado), se suelta en modo juego y se quita en *Funciones → Buscador*.

## Programas que piden atención

Cuando un programa pide atención (Discord con un mensaje, un juego que termina de cargar…), su botón se pone naranja y
late, como en la barra de Windows, hasta que lo abres; con la isla dinámica, además, sale un aviso con su nombre y un
clic lo trae delante. Lo cuenta Windows con `RegisterShellHookWindow`, sin inyectar nada.

## Ventanas encajadas

Windows reparte las ventanas al encajarlas (mitades, tercios, cuartos) con el hueco de su propia barra, no con el de
esta: la barra las recoloca al momento en el área de verdad, con las mismas proporciones (solo las que encajan
exactamente en ese reparto; las puestas a mano no se tocan). En una pantalla vertical, soltar una ventana sobre la
barra la encaja en la mitad de abajo, con una vista previa mientras se arrastra (`barra/encaje.py`).

## Micrófono y volumen por programa

Mientras un programa graba del micrófono sale un micrófono naranja en la bandeja (y un aviso en la isla al empezar).
La rueda sobre el botón de un programa cambia su volumen de 5 en 5, como su barra del Mezclador. Las dos cosas salen
de las sesiones de sonido de Windows (`barra/audio.py`), por el programa y sus procesos auxiliares. La cámara no:
Windows ya no deja saber quién la usa sin permisos especiales.

## Widgets y tiempo

El botón abre los widgets de Windows (Win+W). Windows no enseña el tiempo con su barra oculta: si eliges una ciudad en el
menú, se pide a [Open-Meteo](https://open-meteo.com) (CC BY 4.0) cada 20 minutos. Sin ciudad no se consulta nada.

## Música y visualizador

Mientras hay algo reproduciéndose salen barras de frecuencias al estilo de [cava](https://github.com/karlstav/cava), hechas aquí: capturan lo
que sale por los altavoces (nunca el micrófono, y sin guardar nada) solo mientras suena algo. Clic: pausar o seguir; rueda: anterior o siguiente. Se quitan con *Visualizador*;
*Animaciones* regula su ritmo.

## Formatos

En el menú (pestaña *Forma*), el formato cambia la forma de cada tema por separado: completa, flotante (píldora separada
del borde), compacta (30 px), islas, islas compactas (36 px), una isla (todo junto en el centro), una isla compacta,
pestaña (una isla pegada al borde), dock (iconos grandes que crecen bajo el ratón; 60 px), dock pegado (56 px), dock
pequeño (cabe en los 48 px de Windows), esquinas (tres piezas pegadas al borde, las de los lados en las esquinas) o
burbujas (cada programa en su círculo y el resto en píldoras).
*Esconderse → Se esconde sola* deja una rayita en el borde: la barra sale al llevar el ratón allí, y las ventanas
maximizadas ocupan toda la pantalla.
Las compactas agrandan el área de trabajo, y las ventanas maximizadas ganan ese espacio; al cerrar vuelve a su sitio.

## Mínimo

Monocromo y sin dibujos: sigue el modo claro u oscuro de Windows pero no su color de acento (`"acentoWindows": false`),
marca la ventana activa solo con un punto (`"fondoActiva": false`) y enseña solo inicio, programas, bandeja, volumen y
hora. Con los iconos adaptados, la bandeja va sin pastilla detrás (`"pastillaSoloOriginales": true`).

## Original y opacidad

El tema Original imita la barra de Windows 11 y sigue su modo claro u oscuro y su color de acento. En el menú, *Opacidad* va de opaca a transparente. Por debajo del 60 % el
texto lleva contorno, y si la imagen de fondo es clara tras la barra pasa a oscuro. Cualquier tema puede tener esa fila
con `"translucida": true` (y `coloresClaros` para el texto oscuro).

## Claudito

Pasa el ratón para ver tus sesiones de Claude, los límites del plan, la cuenta y los tokens de hoy y de la
semana. Todo sale de archivos de tu equipo. Los límites los da la línea de estado de Claude Code, que solo hay en la terminal. Un clic trae al frente la ventana
de la sesión que toca (la que te necesita, si la hay). Late cuando Claude te está esperando.

## Posición de la barra

Abajo, arriba, a la izquierda o a la derecha: en el menú o arrastrando un hueco vacío de la barra hacia ese borde. En
vertical los temas no llevan paisaje.

## Posición de los iconos

Sigue lo elegido en Windows (izquierda o centro) y cambia al momento. Se puede fijar en el menú. Los iconos van en el centro
exacto o al principio; lo demás se reparte a los lados y, si no cabe, se esconde: título, música, widgets, medidores y Claudito.

## Iconos

En el menú, *Iconos*: los originales o adaptados al tema, que los pinta con sus colores (en Píxel, como pixel art). Vale
para los programas y la bandeja; no cambia ningún archivo.

## Ambiente

Píxel, Bosque y Sakura cambian con la hora (noche, amanecer, día y atardecer, con horas aproximadas del hemisferio norte) y
Bosque, también con la estación. CPU, RAM y GPU tienen un dibujo propio en cada tema (`medidor` en `tema.json`:
`texto`, `onda`, `flor`, `anillo`, `corazones`, `rama`, `linea` o `pildora`). Los colores por momento van en `momentos`. También son de cada
tema la forma del visualizador (`cava`: `barras`, `neon`, `petalos`, `hojas` o `bloques`) y el dibujo del tiempo (`clima`:
`emoji`, `neon`, `flor`, `hoja` o `pixel`). En Tokyo Night, las ventanas de la ciudad laten con el sonido.

## Menú y recursos

Clic derecho en el reloj: menú visual en pestañas (Temas, Forma, Iconos, Funciones, General), también *Arrancar con Windows*.
La *isla dinámica* (pestaña Funciones) avisa junto a la barra de la canción nueva, de Claude esperando, de la red y de la
batería. Las miniaturas
se rehacen con `py barra.pyw --miniaturas`. *Animaciones* regula cuánto se redibuja; a los 90 s sin tocar el equipo, los
fondos se paran solos. Claudito se dibuja desde una copia en `%LOCALAPPDATA%\barra-temas\claudito`, hecha al arrancar.

## Si se cae

El vigilante devuelve la barra de Windows al momento y vuelve a abrir esta, como mucho 3 veces en 5 minutos. No la
reabre si la cierras tú, con el atajo de emergencia o con el .bat, ni al apagar el equipo.

En `barra.log` queda cada cierre con su motivo: el código de salida y qué suele querer decir (fallo de memoria, la
cerró otro programa, no respondía…). Si cayó de golpe, debajo va dónde estaba cada hilo (lo deja `faulthandler` en
`barra-fallo.log`). Los errores de Python que no la tiran también se anotan, cada uno como mucho una vez por minuto.

Para probar código nuevo sin que cuente como caída: `py barraigilante.py --recargar` la cierra y la vuelve a abrir.

## Crear un tema

Copia una carpeta de `temas` en `%LOCALAPPDATA%\barra-temas\temas`, cámbiale el nombre y edita `tema.json`. `alto + margen` no puede pasar de 48.
`Fondo.qml` es opcional y debe tener `radio`, `desde` y `total`: en los formatos de islas se dibuja dentro de
cada pieza (`barra.tema.dentro`), con esas esquinas y desde ese punto de la barra. Para verlos todos sin tocar nada: `py barra.pyw --vista CARPETA`.

Para recuperar un tema quitado, muévelo de `temas-retirados` a `temas`.

El icono de Windows sale de `logo` en `tema.json`: colores, redondez de cada esquina (`fuera`, `dentro`, `lados`) y `hueco`.

## Piezas

- `barra/cava.py`: proceso aparte con el visualizador.
- `barra/atajos.py`: proceso aparte con los atajos de teclado. `barra/tiempo.py`: el tiempo.
- `barra/actualizar.py`, `barra/instalado.py`, `installer/`: instalador y actualización (`py installer\build.py`).
- `.github/workflows/compilar.yml`: pruebas y compilación en GitHub; con una etiqueta `v*`, borrador del release. La firma, en
  [installer/FIRMA.md](installer/FIRMA.md).
- `barra/bandeja.py`: proceso aparte que recibe los iconos de la bandeja y los reenvía a Explorer.
- `barra/vigilante.py`: proceso aparte que devuelve la barra de Windows si esta se cierra o se cuelga.
- `barra/vista.py`: vista previa de las ventanas (miniaturas de DWM).
- `barra/vidrio.py`: lectura del fondo de escritorio para los temas con `vidrio` o `adapta` (Liquid Glass y Camaleón
  están en `temas-retirados`).
- `barra/sesiones.py`, `barra/uso.py`, `barra/conectar.py`, `barra/panel_claude.py`: Claudito interactivo.
- `claudito/`: copia exacta de lo que hace falta de Claudito (`py installer\copiar_claudito.py`).
- `barra/iconos.py`: iconos adaptados al tema.
- `barra/saltos.py`: listas de saltos (IApplicationResolver, IApplicationDocumentLists y CustomDestinations).
- `barra/red.py`: Wi-Fi, conexión y batería. `barra/calendario.py`: el calendario. `barra/isla.py`: la isla dinámica.
- `barra/programas.py`: nombre real de los programas y agrupación.
- `barra/buscador.py`, `barra/apps.py`: el buscador (y el temporizador) y la lista de aplicaciones de `shell:AppsFolder`.
- `barra/audio.py`: las sesiones de sonido de cada programa: quién usa el micrófono y el volumen por programa.
- `barra/atencion.py`: programas que piden atención.
- `barra/ajustes.py`: ajustes guardados y programas anclados.
- `barra/claudito.py`: lee el estado y el dibujo de `~/src/claudito`, sin escribir allí.

Pruebas: `py -m unittest discover -s tests`

## Privacidad

Sin telemetría. Con quién se conecta, cuándo y cómo quitarlo: [PRIVACIDAD.md](PRIVACIDAD.md).

## Licencia

[MIT](LICENSE). El instalador incluye Python y Qt/PySide6, con sus licencias en `licenses`.
