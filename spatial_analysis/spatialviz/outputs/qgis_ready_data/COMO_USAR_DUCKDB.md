# 🦆 Como Usar DuckDB - Guia Visual Simples

## 🎯 **O que é o DuckDB?**
É um **banco de dados** que conecta Python e QGIS automaticamente!

## 🚀 **Workflow Simples (3 Passos):**

```
1️⃣ Python (Análises) → 2️⃣ DuckDB (Armazenamento) → 3️⃣ QGIS (Visualização)
```

## 💻 **Como Usar no Python:**

### **Passo 1: Conectar**
```python
import duckdb
con = duckdb.connect("stuttgart_analysis.duckdb")
```

### **Passo 2: Ler Dados**
```python
# Ler distritos
districts = con.execute("SELECT * FROM districts").fetchall()
```

### **Passo 3: Fazer Análise**
```python
# Exemplo: criar buffer
import geopandas as gpd
gdf = gpd.GeoDataFrame(...)
gdf['buffer'] = gdf.geometry.buffer(500)  # 500m
```

### **Passo 4: Salvar no DuckDB**
```python
# Criar tabela
con.execute("CREATE TABLE minha_analise (...)")

# Inserir dados
con.execute("INSERT INTO minha_analise VALUES (...)")
```

### **Passo 5: QGIS Vê Automaticamente! 🎉**

## 🗺️ **Como Usar no QGIS:**

### **1. Instalar Plugin**
- Plugins → Manage and Install Plugins
- Buscar: **"DuckDB Provider"**
- Instalar e reiniciar

### **2. Conectar ao DuckDB**
- Layer → Add Layer → **Add DuckDB Layer**
- Navegar até: `stuttgart_analysis.duckdb`
- Selecionar tabela (ex: `districts`, `roads`)
- Clicar **"Add"**

### **3. Aplicar Estilos**
- Usar arquivos `.qml` que criamos
- Right-click na layer → **Load Style**

## 📊 **Exemplos Práticos:**

### **Exemplo 1: Análise de População**
```python
# Encontrar top 5 distritos
top_districts = districts_df.nlargest(5, 'pop')
# Salvar no DuckDB
# QGIS vê automaticamente!
```

### **Exemplo 2: Buffers de Acessibilidade**
```python
# Criar buffer de 300m ao redor de paradas
pt_buffers = pt_stops.geometry.buffer(300)
# Salvar no DuckDB
# QGIS mostra áreas de serviço!
```

### **Exemplo 3: Análise de Interseção**
```python
# Calcular áreas verdes por distrito
green_percentage = green_areas.intersection(district).area
# Salvar no DuckDB
# QGIS mostra mapa de densidade verde!
```

## 🔄 **Vantagens do Workflow:**

✅ **Sem Export/Import** - QGIS vê mudanças automaticamente  
✅ **Análises Complexas** - Python faz o trabalho pesado  
✅ **Visualização Profissional** - QGIS para mapas bonitos  
✅ **Tempo Real** - Resultados aparecem instantaneamente  

## 🎯 **Quando Usar:**

- **Python**: Para análises espaciais complexas
- **DuckDB**: Para armazenar e compartilhar dados
- **QGIS**: Para visualização e cartografia profissional

## 💡 **Dica Importante:**

Execute o script `exemplo_simples.py` sempre que quiser ver como funciona!

---

## 🚀 **Próximos Passos:**

1. **Teste no Python**: Execute `exemplo_simples.py`
2. **Instale QGIS**: Se ainda não tiver
3. **Instale Plugin DuckDB**: No QGIS
4. **Conecte**: Ao arquivo `stuttgart_analysis.duckdb`
5. **Explore**: As tabelas e dados disponíveis!

**🎉 Agora você tem o poder de fazer análises espaciais avançadas e ver os resultados instantaneamente no QGIS!**

