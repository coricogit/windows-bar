# Privacidad

Windows Bar no recoge datos, no tiene telemetría y no tiene servidores propios. Lo que sabe de tu equipo se queda en tu
equipo (`%LOCALAPPDATA%\barra-temas`).

Solo se conecta a internet para esto:

| Con quién | Cuándo | Qué recibe | Cómo se quita |
|---|---|---|---|
| GitHub | La copia instalada, cada 6 horas, para buscar una versión nueva y descargarla | Tu dirección IP, como en cualquier descarga ([política](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement)) | Menú > *Actualizar sola* |
| Open-Meteo | Solo si eliges una ciudad: cada 20 minutos, para el tiempo | El nombre que escribes y las coordenadas de esa ciudad, con tu dirección IP ([política](https://open-meteo.com/en/terms)) | Menú > *Ciudad* y dejarla vacía |

- **Sonido:** el visualizador mira lo que sale por los altavoces, nunca el micrófono, y no guarda ni envía nada.
- **Teclado:** los atajos solo se miran con la tecla Windows pulsada o eligiendo con las flechas. No se guarda nada.
- **Claude Code:** la cuenta, los límites y los tokens se leen de archivos de tu equipo. No se envían. Si pulsas *Conectar
  Claude Code*, se añaden avisos locales a su `settings.json`; *Desconectar* los quita.

## Cambios en el equipo

Mientras está abierta oculta la barra de tareas de Windows y, según el formato, cambia el espacio de las ventanas. Al
cerrarla, o si falla, todo vuelve a su sitio. Se instala en tu perfil, sin administrador; puede añadir una entrada de arranque
y accesos en el menú Inicio. Se desinstala desde *Configuración > Aplicaciones*, que quita todo eso. Los ajustes se conservan.
