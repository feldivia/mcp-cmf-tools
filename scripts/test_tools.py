"""
Testea cada tool del MCP server directamente.
Uso: python scripts/test_tools.py
"""
import asyncio
import os
import json
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_tools.cmf import indicadores_cmf, alertas_fraude
from mcp_tools.mindicador import indicadores_economicos

CMF_API_KEY = os.getenv("CMF_API_KEY", "")


async def test_all():
    print("=" * 60)
    print("Testing MCP CMF Tools")
    print("=" * 60)

    # Test 1: Indicadores economicos (mindicador.cl)
    print("\n1. indicadores_economicos()")
    try:
        result = await indicadores_economicos()
        print(f"   Result: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: Alertas de fraude (consulta en vivo a CMF)
    print("\n2. alertas_fraude('forex')")
    try:
        result = await alertas_fraude("forex")
        print(f"   Result: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Indicadores CMF
    print("\n3. indicadores_cmf()")
    try:
        result = await indicadores_cmf(CMF_API_KEY)
        print(f"   Result: {json.dumps(result, ensure_ascii=False, indent=2)[:300]}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Tests completados")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())
