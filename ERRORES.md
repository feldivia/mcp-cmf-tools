# RegulBot — Registro de Errores

> Revisar este documento ANTES de desarrollar para no repetir errores.
> Ultima actualizacion: 2026-04-26

---

## Errores Resueltos

### ERR-001: pyproject.toml sin build-system
- **Fecha**: 2026-04-21
- **Sintoma**: `pip install -e .` fallaba con error de setuptools
- **Causa**: Faltaba la seccion `[build-system]` en pyproject.toml
- **Solucion**: Agregar `[build-system]` con requires = ["setuptools>=68.0"]
- **Leccion**: Siempre incluir `[build-system]` en pyproject.toml para proyectos Python

### ERR-002: setuptools multiple top-level packages
- **Fecha**: 2026-04-21
- **Sintoma**: `pip install -e .` fallaba con "Multiple top-level packages discovered in a flat-layout"
- **Causa**: setuptools detectaba `chat/`, `data/`, `frontend/`, `mcp_tools/` como paquetes Python
- **Solucion**: Agregar `[tool.setuptools.packages.find]` con `include = ["mcp_tools*", "chat*"]`
- **Leccion**: En proyectos flat-layout con carpetas mixtas (frontend, data), declarar packages explicitamente

### ERR-003: venv con permisos bloqueados
- **Fecha**: 2026-04-21
- **Sintoma**: `python -m venv .venv` fallaba con Permission denied en python.exe
- **Causa**: .venv existente con archivos bloqueados (posiblemente por proceso activo)
- **Solucion**: `rm -rf .venv` y recrear
- **Leccion**: Si .venv da problemas de permisos, eliminar y recrear desde cero

---

## Errores Conocidos / Sin Resolver

_(Ninguno por ahora)_

---

## Patrones a Evitar

| Patron | Por que evitarlo | Que hacer |
|---|---|---|
| `pip install -e .` sin build-system | Falla con error de setuptools | Siempre tener `[build-system]` en pyproject.toml |
| Flat-layout sin packages explicitos | setuptools incluye carpetas no-Python | Usar `[tool.setuptools.packages.find]` con include |
| Instalar en venv con `source activate && pip` | En Windows/Git Bash puede fallar | Usar `.venv/Scripts/python.exe -m pip install` |
