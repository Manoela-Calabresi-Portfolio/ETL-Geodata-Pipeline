#!/usr/bin/env python3
"""
Exemplo Simples de Como Usar DuckDB
Demonstra o workflow básico: Python → DuckDB → QGIS
"""

import duckdb
import geopandas as gpd
from shapely import wkt

def exemplo_basico():
    """Exemplo básico de como usar DuckDB"""
    print("🚀 Exemplo Básico de Uso do DuckDB")
    print("=" * 50)
    
    # 1. Conectar ao DuckDB
    print("1️⃣ Conectando ao DuckDB...")
    con = duckdb.connect("stuttgart_analysis.duckdb")
    print("   ✅ Conectado!")
    
    # 2. Ver o que tem no banco
    print("\n2️⃣ Verificando tabelas disponíveis...")
    tables = con.execute("SHOW TABLES").fetchall()
    for table in tables:
        print(f"   📋 {table[0]}")
    
    # 3. Ler dados do DuckDB
    print("\n3️⃣ Lendo dados dos distritos...")
    districts_data = con.execute("SELECT * FROM districts LIMIT 3").fetchall()
    print("   📊 Primeiros 3 distritos:")
    for row in districts_data:
        print(f"      - {row[1]} (Pop: {row[2]})")
    
    # 4. Fazer uma análise simples
    print("\n4️⃣ Fazendo análise espacial...")
    
    # Ler todos os distritos
    all_districts = con.execute("SELECT * FROM districts").fetchall()
    
    # Converter para GeoDataFrame para análise
    districts_df = gpd.GeoDataFrame(
        [(row[0], row[1], row[2], row[3]) for row in all_districts],
        columns=['id', 'name', 'pop', 'pop_density'],
        geometry=[wkt.loads(row[4]) for row in all_districts],
        crs='EPSG:4326'
    )
    
    # Análise: encontrar distritos com mais população
    print("   🏆 Top 5 distritos por população:")
    top_districts = districts_df.nlargest(5, 'pop')
    for idx, row in top_districts.iterrows():
        print(f"      {row['name']}: {row['pop']:,} habitantes")
    
    # 5. Salvar resultado no DuckDB
    print("\n5️⃣ Salvando resultado no DuckDB...")
    
    # Criar tabela para resultados
    con.execute("""
        CREATE TABLE IF NOT EXISTS top_districts (
            rank INTEGER,
            name VARCHAR,
            population INTEGER,
            pop_density DOUBLE
        )
    """)
    
    # Inserir resultados
    for rank, (idx, row) in enumerate(top_districts.iterrows(), 1):
        con.execute("""
            INSERT INTO top_districts (rank, name, population, pop_density)
            VALUES (?, ?, ?, ?)
        """, [rank, row['name'], row['pop'], row['pop_density']])
    
    print("   ✅ Resultado salvo! QGIS verá automaticamente!")
    
    # 6. Verificar nova tabela
    print("\n6️⃣ Verificando nova tabela criada...")
    new_tables = con.execute("SHOW TABLES").fetchall()
    for table in new_tables:
        if table[0] == 'top_districts':
            count = con.execute("SELECT COUNT(*) FROM top_districts").fetchone()[0]
            print(f"   📋 {table[0]}: {count} registros")
    
    # Fechar conexão
    con.close()
    print("\n🎉 Exemplo concluído!")

def exemplo_buffer():
    """Exemplo de como criar buffers e salvar no DuckDB"""
    print("\n\n📐 Exemplo de Buffer Analysis")
    print("=" * 50)
    
    # Conectar ao DuckDB
    con = duckdb.connect("stuttgart_analysis.duckdb")
    
    # Ler paradas de PT
    print("1️⃣ Lendo paradas de transporte público...")
    pt_data = con.execute("SELECT * FROM pt_stops LIMIT 100").fetchall()
    
    # Converter para GeoDataFrame
    pt_gdf = gpd.GeoDataFrame(
        [(row[0], row[1]) for row in pt_data],
        columns=['id', 'stop_type'],
        geometry=[wkt.loads(row[2]) for row in pt_data],
        crs='EPSG:4326'
    )
    
    print(f"   ✅ Carregadas {len(pt_gdf)} paradas")
    
    # Criar buffer de 200m
    print("2️⃣ Criando buffer de 200m...")
    
    # Converter para CRS projetado para buffer preciso
    pt_proj = pt_gdf.to_crs('EPSG:25832')
    pt_proj['buffer_200m'] = pt_proj.geometry.buffer(200)
    
    # Converter de volta para WGS84
    pt_proj['buffer_wgs84'] = pt_proj['buffer_200m'].to_crs('EPSG:4326')
    
    # Salvar no DuckDB
    print("3️⃣ Salvando buffers no DuckDB...")
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS pt_buffers_200m (
            id INTEGER,
            stop_type VARCHAR,
            buffer_wkt VARCHAR
        )
    """)
    
    for idx, row in pt_proj.iterrows():
        con.execute("""
            INSERT INTO pt_buffers_200m (id, stop_type, buffer_wkt)
            VALUES (?, ?, ?)
        """, [row['id'], row['stop_type'], wkt.dumps(row['buffer_wgs84'])])
    
    print("   ✅ Buffers salvos! QGIS pode usar agora!")
    
    con.close()

def instrucoes_qgis():
    """Instruções para usar no QGIS"""
    print("\n\n🗺️ Como Usar no QGIS:")
    print("=" * 50)
    
    print("1️⃣ Instalar Plugin DuckDB:")
    print("   - Abrir QGIS")
    print("   - Plugins → Manage and Install Plugins")
    print("   - Buscar por 'DuckDB Provider'")
    print("   - Instalar e reiniciar QGIS")
    
    print("\n2️⃣ Conectar ao DuckDB:")
    print("   - Layer → Add Layer → Add DuckDB Layer")
    print("   - Navegar até: stuttgart_analysis.duckdb")
    print("   - Selecionar tabela (ex: districts, roads)")
    print("   - Clicar 'Add'")
    
    print("\n3️⃣ Aplicar Estilos:")
    print("   - Usar os arquivos .qml que criamos")
    print("   - Right-click na layer → Load Style")
    
    print("\n4️⃣ Ver Atualizações:")
    print("   - Python modifica DuckDB")
    print("   - QGIS atualiza automaticamente!")
    print("   - Não precisa mais exportar/importar! 🎉")

def main():
    """Função principal"""
    print("🎯 GUIA COMPLETO: Como Usar DuckDB")
    print("=" * 60)
    
    # Executar exemplos
    exemplo_basico()
    exemplo_buffer()
    
    # Mostrar instruções QGIS
    instrucoes_qgis()
    
    print("\n\n🎉 RESUMO DO WORKFLOW:")
    print("=" * 40)
    print("1. Python faz análises espaciais")
    print("2. Salva resultados no DuckDB")
    print("3. QGIS vê automaticamente!")
    print("4. Sem mais export/import! ✨")
    
    print("\n💡 DICA: Execute este script sempre que quiser")
    print("   fazer análises e ver no QGIS!")

if __name__ == "__main__":
    main()

