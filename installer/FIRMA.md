# Firmar el instalador

El `.exe` no está firmado y Smart App Control lo bloquea. [SignPath Foundation](https://signpath.org) firma gratis proyectos
de código abierto. Está todo preparado en `.github/workflows/compilar.yml`; falta que la persona dueña del repositorio lo
solicite, porque el certificado se concede a quien lo mantiene.

## 1. Solicitarlo

1. Activa la verificación en dos pasos en GitHub (es obligatoria para todo el equipo).
2. Lee las [condiciones](https://signpath.org/terms) y pídelo en <https://signpath.org/apply>. Datos del proyecto:
   - Repositorio: `https://github.com/coricogit/windows-bar` · Licencia: MIT
   - Descargas: `https://github.com/coricogit/windows-bar/releases`
   - Compilación: GitHub Actions, `.github/workflows/compilar.yml`
   - Privacidad: `PRIVACIDAD.md`, que el instalador enseña antes de empezar
3. La decisión es suya y miran también la reputación del proyecto: con pocos usuarios pueden decir que no.

## 2. Al aprobarlo

1. En SignPath: añade el sistema de compilación *GitHub.com* y enlázalo con el proyecto. La configuración del artefacto es un
   `zip-file` con `Windows-Bar-Setup-*.exe` dentro; nombre de producto `Windows Bar`.
2. En GitHub, *Settings > Secrets and variables > Actions*:
   - Secreto `SIGNPATH_API_TOKEN`
   - Variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG` y `SIGNPATH_POLICY_SLUG`
3. Añade al README, tal cual (solo cuando esté aprobado):

```markdown
## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org)

- Committers and reviewers: [coricogit](https://github.com/coricogit)
- Approvers: [coricogit](https://github.com/coricogit)
- Privacy policy: [PRIVACIDAD.md](PRIVACIDAD.md)
```

Desde entonces, cada etiqueta `v*` pide la firma, que hay que aprobar a mano en SignPath, y el borrador del release sale con
el `.exe` firmado.

## Lo que queda

- `unins000.exe`, el desinstalador que crea Inno Setup, va dentro del `.exe` y no se firma con él. Para firmarlo hay que
  compilar en dos pasos (`SignedUninstaller` de Inno). La instalación con `instalar.ps1` no lo usa.
- Aun firmado, un programa nuevo puede tardar en ganar reputación.
