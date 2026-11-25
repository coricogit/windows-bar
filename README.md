# Barra de temas

Barra de tareas para Windows 11 con 10 temas y Claudito. Reemplaza a la de Windows sin cambiar archivos del
sistema ni inyectar código: solo la oculta mientras está abierta.

- **Abrir:** `Iniciar barra.bat`
- **Cerrar:** botón derecho en un hueco de la barra, o clic en el pincel → *Salir y volver a la barra de Windows*
- **Emergencia:** `Ctrl+Alt+Mayús+B`, o `Restaurar barra de Windows.bat`

## Uso

| Dónde | Qué hace |
|---|---|
| Pincel | Clic: menú de temas · Rueda: pasar de tema |
| Ventana | Clic: activar o minimizar · Clic central: abrir otra |
| Volumen | Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio |
| Reloj | Notificaciones y calendario |
| Inicio | Clic: menú Inicio · Clic derecho: menú Win+X |

Ajustes en `%LOCALAPPDATA%\barra-temas\ajustes.json`: tema por hora (`auto`, `tema_dia`, `tema_noche`, `dia`,
`noche`), por programa (`"por_programa": {"steam.exe": "tokyo"}`) y `modo_juego`. Errores en `barra.log`, al lado.

## Formatos

En el menú, *Formato* cambia la forma de cualquier tema: completa, islas, compacta (30 px) o islas compactas (36 px).
Las compactas agrandan el área de trabajo, y las ventanas maximizadas ganan ese espacio; al cerrar vuelve a su sitio.

## Crear un tema

Copia una carpeta de `temas`, cámbiale el nombre y edita `tema.json`. `alto + margen` no puede pasar de 48.
`Fondo.qml` es opcional. Para verlos todos sin tocar nada: `py barra.pyw --vista CARPETA`.

Para recuperar un tema quitado, muévelo de `temas-retirados` a `temas`.

## Piezas

- `barra/bandeja.py`: proceso aparte que recibe los iconos de la bandeja y los reenvía a Explorer.
- `barra/vigilante.py`: proceso aparte que devuelve la barra de Windows si esta se cierra o se cuelga.
- `barra/claudito.py`: lee el estado y el dibujo de `~/src/claudito`, sin escribir allí.
- `lib/`: paquetes `winrt-*` para la música. Se regenera con
  `py -m pip install --target lib winrt-runtime winrt-Windows.Media.Control winrt-Windows.Foundation winrt-Windows.Foundation.Collections`

Pruebas: `py -m unittest discover -s tests`
