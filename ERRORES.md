# RegulBot — Registro de Errores

> Revisar este documento ANTES de desarrollar para no repetir errores.
> Última actualización: 2026-04-21

---

## Errores Resueltos

### ERR-001: pyproject.toml sin build-system
- **Fecha**: 2026-04-21
- **Síntoma**: `pip install -e .` fallaba con error de setuptools
- **Causa**: Faltaba la sección `[build-system]` en pyproject.toml
- **Solución**: Agregar `[build-system]` con requires = ["setuptools>=68.0"]
- **Lección**: Siempre incluir `[build-system]` en pyproject.toml para proyectos Python

### ERR-002: setuptools multiple top-level packages
- **Fecha**: 2026-04-21
- **Síntoma**: `pip install -e .` fallaba con "Multiple top-level packages discovered in a flat-layout"
- **Causa**: setuptools detectaba `chat/`, `data/`, `frontend/`, `mcp_tools/` como paquetes Python
- **Solución**: Agregar `[tool.setuptools.packages.find]` con `include = ["mcp_tools*", "chat*"]`
- **Lección**: En proyectos flat-layout con carpetas mixtas (frontend, data), declarar packages explícitamente

### ERR-003: venv con permisos bloqueados
- **Fecha**: 2026-04-21
- **Síntoma**: `python -m venv .venv` fallaba con Permission denied en python.exe
- **Causa**: .venv existente con archivos bloqueados (posiblemente por proceso activo)
- **Solución**: `rm -rf .venv` y recrear
- **Lección**: Si .venv da problemas de permisos, eliminar y recrear desde cero

---

## Errores Conocidos / Sin Resolver

_(Ninguno por ahora — se agregarán conforme se pruebe la aplicación)_

---

## Patrones a Evitar

| Patrón | Por qué evitarlo | Qué hacer en su lugar |
|---|---|---|
| `pip install -e .` sin build-system | Falla silenciosamente o con error críptico | Siempre tener `[build-system]` en pyproject.toml |
| Flat-layout sin packages explícitos | setuptools incluye carpetas no-Python | Usar `[tool.setuptools.packages.find]` con include |
| Instalar en venv con `source activate && pip` | En Windows/Git Bash puede fallar | Usar `.venv/Scripts/python.exe -m pip install` directamente |

---

## Formato para Nuevos Errores

```markdown
### ERR-XXX: Título descriptivo
- **Fecha**: YYYY-MM-DD
- **Síntoma**: Qué se observó (mensaje de error, comportamiento)
- **Causa**: Por qué ocurrió
- **Solución**: Qué se hizo para resolverlo
- **Lección**: Qué recordar para el futuro
```
