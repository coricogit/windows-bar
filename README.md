# Barra de temas

Barra de tareas para Windows 11 con 7 temas y Claudito. Reemplaza a la de Windows sin cambiar archivos del
sistema ni inyectar código: solo la oculta mientras está abierta.

- **Abrir:** `Iniciar barra.bat`
- **Cerrar:** clic derecho en el reloj → *Salir y volver a la barra de Windows*
- **Emergencia:** `Ctrl+Alt+Mayús+B`, o `Restaurar barra de Windows.bat`

## Uso

| Dónde | Qué hace |
|---|---|
| Reloj, volumen o un hueco | Clic derecho: menú de temas y ajustes |
| Programa | Pasar el ratón: vista previa de todas sus ventanas · Clic: activar o minimizar (con varias, elegir) · Rueda: pasar de una a otra · Clic central: abrir otra · Clic derecho: menú |
| Volumen | Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio |
| Reloj | Clic: notificaciones y calendario |
| Inicio | Clic: menú Inicio · Clic derecho: menú Win+X · Rueda: pasar de tema |

Ajustes en `%LOCALAPPDATA%\barra-temas\ajustes.json`: tema por hora (`auto`, `tema_dia`, `tema_noche`, `dia`,
`noche`), por programa (`"por_programa": {"steam.exe": "tokyo"}`) y `modo_juego`. Errores en `barra.log`, al lado.

## Formatos

En el menú, *Formato* cambia la forma de cada tema por separado: completa, islas, compacta (30 px) o islas compactas (36 px).
Las compactas agrandan el área de trabajo, y las ventanas maximizadas ganan ese espacio; al cerrar vuelve a su sitio.

## Claudito

Pasa el ratón para ver tus sesiones de Claude, los límites del plan y el uso de hoy. Un clic trae al frente la ventana
de la sesión que toca (la que te necesita, si la hay). Late cuando Claude te está esperando.

## Posición de los iconos

Sigue lo elegido en Windows (izquierda o centro) y cambia al momento. Se puede fijar en el menú.

## Liquid Glass

Refracta la capa del fondo de escritorio, también la de Wallpaper Engine; nunca lee las ventanas. Cada pieza mide lo
claro que es su fondo y cambia a texto oscuro si hace falta. El menú tiene cinco niveles de transparencia.

## Ambiente

Píxel y Bosque cambian con la hora (noche, amanecer, día y atardecer, con horas aproximadas del hemisferio norte) y
Bosque, también con la estación. CPU, RAM y GPU tienen un dibujo propio en cada tema (`medidor` en `tema.json`:
`texto`, `onda`, `flor`, `anillo`, `corazones`, `rama`, `linea` o `pildora`). Los colores por momento van en `momentos`.

## Menú y recursos

Clic derecho en el reloj: menú visual con los temas y todos los ajustes, también *Arrancar con Windows*. Las miniaturas
se rehacen con `py barra.pyw --miniaturas`. *Animaciones* regula cuánto se redibuja; a los 90 s sin tocar el equipo, los
fondos se paran solos. Claudito se dibuja desde una copia en `%LOCALAPPDATA%\barra-temas\claudito`, hecha al arrancar.

## Si se cae

El vigilante devuelve la barra de Windows al momento y vuelve a abrir esta, como mucho 3 veces en 5 minutos. No la
reabre si la cierras tú, con el atajo de emergencia o con el .bat, ni al apagar el equipo.

## Crear un tema

Copia una carpeta de `temas`, cámbiale el nombre y edita `tema.json`. `alto + margen` no puede pasar de 48.
`Fondo.qml` es opcional. Para verlos todos sin tocar nada: `py barra.pyw --vista CARPETA`.

Para recuperar un tema quitado, muévelo de `temas-retirados` a `temas`.

El icono de Windows sale de `logo` en `tema.json`: colores, redondez de cada esquina (`fuera`, `dentro`, `lados`) y `hueco`.

## Piezas

- `barra/bandeja.py`: proceso aparte que recibe los iconos de la bandeja y los reenvía a Explorer.
- `barra/vigilante.py`: proceso aparte que devuelve la barra de Windows si esta se cierra o se cuelga.
- `barra/vista.py`: vista previa de las ventanas (miniaturas de DWM).
- `barra/vidrio.py`: el vidrio de Liquid Glass.
- `barra/sesiones.py`, `barra/uso.py`, `barra/panel_claude.py`: Claudito interactivo.
- `barra/programas.py`: nombre real de los programas y agrupación.
- `barra/ajustes.py`: ajustes guardados y programas anclados.
- `barra/claudito.py`: lee el estado y el dibujo de `~/src/claudito`, sin escribir allí.
- `lib/`: paquetes `winrt-*` para la música. Se regenera con
  `py -m pip install --target lib winrt-runtime winrt-Windows.Media.Control winrt-Windows.Foundation winrt-Windows.Foundation.Collections`

Pruebas: `py -m unittest discover -s tests`
