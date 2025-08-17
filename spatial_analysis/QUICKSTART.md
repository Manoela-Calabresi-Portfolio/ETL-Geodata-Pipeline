# Stuttgart Spatial Analysis - Quick Start

## 🚀 Instalação Rápida

### 1. Instalar Dependências
```bash
# Instalar dependências específicas da análise espacial
pip install -r spatial_analysis/requirements.txt
```

### 2. Verificar Pipeline Principal
Certifique-se que o pipeline principal já foi executado:
```bash
# Verificar se existem dados processados
ls data_final/stuttgart/processed/
```

Deve mostrar:
- `amenities_categorized.parquet`
- `pt_stops_categorized.parquet` 
- `roads_categorized.parquet`
- `landuse_categorized.parquet`

## 📋 Execução Passo a Passo

### PASSO 1: Coleta de Dados
```bash
# Coleta completa (recomendado na primeira execução)
python spatial_analysis/scripts/1_data_collection.py

# OU coleta seletiva
python spatial_analysis/scripts/1_data_collection.py --gtfs-only
python spatial_analysis/scripts/1_data_collection.py --osm-only
```

### PASSO 2: Cálculo de KPIs
```bash
# Em desenvolvimento - próximo script
python spatial_analysis/scripts/2_kpi_calculation.py
```

### PASSO 3: Visualização
```bash
# Em desenvolvimento - próximo script  
python spatial_analysis/scripts/3_visualization.py
```

## 📊 Dados Coletados

Após executar o PASSO 1, você terá em `spatial_analysis/data/processed/`:

### Dados Reutilizados do Pipeline Principal:
- `amenities.parquet` - 62k+ amenidades categorizadas
- `pt_stops.parquet` - 8k+ paradas de transporte  
- `roads.parquet` - 76k+ segmentos de ruas
- `landuse.parquet` - 12k+ áreas de uso do solo

### Dados Específicos da Análise:
- `stadtbezirke.parquet` - 23 distritos de Stuttgart com população
- `gtfs_stops_with_frequency.parquet` - Paradas GTFS com frequência
- `osm_road_edges.parquet` - Rede viária para análise de cruzamentos

## 🎯 Indicadores Calculados

### Transporte Público:
1. **% população ≤ 300m parada alta frequência** (headway ≤ 15min)
2. **Nº médio de linhas acessíveis** por distrito

### Caminhabilidade:
3. **Densidade de cruzamentos** (n/km²)
4. **% população ≤ 500m de POIs** (mercado, escola, parque)

### Áreas Verdes:
5. **% população ≤ 500m área verde** pública

## ⚙️ Configuração

### Pesos dos Indicadores (`spatial_analysis/config/kpi_weights.yaml`):
```yaml
main_categories:
  public_transport: 0.4    # 40%
  walkability: 0.35        # 35%  
  green_access: 0.25       # 25%
```

### Parâmetros de Análise (`spatial_analysis/config/analysis_config.yaml`):
```yaml
analysis_parameters:
  public_transport:
    high_frequency_threshold: 15  # minutos
    access_distance: 300         # metros
  walkability:
    poi_access_distance: 500     # metros
  green_spaces:
    access_distance: 500         # metros
```

## 📁 Estrutura de Saída

```
spatial_analysis/
├── data/
│   ├── processed/          # Dados processados
│   └── results/           # KPIs calculados por distrito
└── outputs/
    ├── maps/              # Mapas de mobilidade
    ├── rankings/          # Rankings dos distritos  
    └── reports/           # Relatórios detalhados
```

## 🔧 Solução de Problemas

### Erro de Dependências OSMnx:
```bash
# Se osmnx falhar, instalar dependências do sistema
# Ubuntu/Debian:
sudo apt-get install libspatialindex-dev

# Windows: usar conda
conda install -c conda-forge osmnx
```

### Erro GTFS Download:
```bash
# Se download do GTFS falhar, baixar manualmente:
wget https://download.mobidata-bw.de/soll-fahrplandaten-vvs.zip \
  -O spatial_analysis/data/raw/gtfs_vvs.zip
```

### Dados Mock:
- O script cria distritos mock se não encontrar dados oficiais
- Para dados reais, baixar de: https://www.stuttgart.de/open-data/

## 🎯 Próximos Passos

1. **Completar coleta de dados** (PASSO 1)
2. **Aguardar PASSO 2** - Cálculo de KPIs  
3. **Aguardar PASSO 3** - Visualização

O pipeline está sendo desenvolvido de forma modular - cada passo pode ser executado independentemente!
