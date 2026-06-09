#!/usr/bin/env python3
"""
Script de limpieza: Correción de timestamps NULL en tabla pedidos

Este script actualiza cualquier pedido con creado_en o actualizado_en = NULL
a CURRENT_TIMESTAMP para garantizar consistencia de datos.

RECOMENDACIÓN: Ejecutar una sola vez después de actualizar app.py
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def fix_null_timestamps():
    """Corrige timestaps NULL en tabla pedidos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si hay pedidos con creado_en = NULL
    cursor.execute("SELECT COUNT(*) as count FROM pedidos WHERE creado_en IS NULL")
    count_creado = cursor.fetchone()['count']
    
    # Verificar si hay pedidos con actualizado_en = NULL
    cursor.execute("SELECT COUNT(*) as count FROM pedidos WHERE actualizado_en IS NULL")
    count_actualizado = cursor.fetchone()['count']
    
    print(f"📊 Diagnóstico:")
    print(f"   - Pedidos con creado_en = NULL: {count_creado}")
    print(f"   - Pedidos con actualizado_en = NULL: {count_actualizado}")
    
    if count_creado == 0 and count_actualizado == 0:
        print("\n✅ Base de datos está limpia. No hay timestamps NULL.")
        conn.close()
        return
    
    print("\n🔄 Aplicando correcciones...")
    
    # Actualizar creado_en NULL a CURRENT_TIMESTAMP
    if count_creado > 0:
        cursor.execute(
            "UPDATE pedidos SET creado_en = CURRENT_TIMESTAMP WHERE creado_en IS NULL"
        )
        print(f"   ✓ Actualizados {count_creado} pedidos con creado_en = NULL")
    
    # Actualizar actualizado_en NULL a CURRENT_TIMESTAMP
    if count_actualizado > 0:
        cursor.execute(
            "UPDATE pedidos SET actualizado_en = CURRENT_TIMESTAMP WHERE actualizado_en IS NULL"
        )
        print(f"   ✓ Actualizados {count_actualizado} pedidos con actualizado_en = NULL")
    
    conn.commit()
    
    # Verificación final
    cursor.execute("SELECT COUNT(*) as count FROM pedidos WHERE creado_en IS NULL")
    final_creado = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM pedidos WHERE actualizado_en IS NULL")
    final_actualizado = cursor.fetchone()['count']
    
    print(f"\n✅ Verificación final:")
    print(f"   - Pedidos con creado_en = NULL: {final_creado}")
    print(f"   - Pedidos con actualizado_en = NULL: {final_actualizado}")
    
    if final_creado == 0 and final_actualizado == 0:
        print("\n✨ Limpieza completada exitosamente!")
    
    conn.close()

if __name__ == '__main__':
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        fix_null_timestamps()
    except Exception as e:
        print(f"❌ Error: {e}")
